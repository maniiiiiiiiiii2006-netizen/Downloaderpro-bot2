import os
import uuid
import asyncio
import yt_dlp
import aiosqlite

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, CallbackQueryHandler, ContextTypes, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")

os.makedirs("downloads", exist_ok=True)

queue = asyncio.Queue()
active_users = set()
cancel_flags = {}
pause_flags = {}

# ---------------- DB ----------------

async def init_db():
    async with aiosqlite.connect("bot.db") as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS downloads (
            id TEXT,
            user_id INTEGER,
            title TEXT,
            status TEXT
        )
        """)
        await db.commit()

# ---------------- INFO ----------------

def get_info(url):
    with yt_dlp.YoutubeDL({"quiet": True}) as ydl:
        return ydl.extract_info(url, download=False)

# ---------------- PROGRESS ----------------

async def edit(msg, text):
    try:
        await msg.edit_text(text)
    except:
        pass


def progress_hook(msg, job_id):
    def hook(d):
        if cancel_flags.get(job_id):
            raise Exception("Cancelled")

        while pause_flags.get(job_id):
            asyncio.sleep(1)

        if d["status"] == "downloading":
            percent = d.get("_percent_str", "0%").strip()
            speed = d.get("_speed_str", "")
            eta = d.get("_eta_str", "")

            text = f"""⬇️ Downloading
📊 {percent}
⚡ {speed}
⏳ {eta}"""

            asyncio.run_coroutine_threadsafe(edit(msg, text), asyncio.get_event_loop())

        elif d["status"] == "finished":
            asyncio.run_coroutine_threadsafe(edit(msg, "⚙️ Processing..."), asyncio.get_event_loop())

    return hook

# ---------------- WORKER ----------------

async def worker(app):
    loop = asyncio.get_running_loop()

    while True:
        job = await queue.get()

        uid = job["user_id"]
        jid = job["id"]

        if uid in active_users:
            await queue.put(job)
            await asyncio.sleep(1)
            continue

        active_users.add(uid)

        try:
            def run():
                with yt_dlp.YoutubeDL(job["opts"]) as ydl:
                    ydl.download([job["url"]])

            await loop.run_in_executor(None, run)

            if cancel_flags.get(jid):
                await edit(job["msg"], "❌ Cancelled")
                continue

            for file in os.listdir(job["path"]):
                full = os.path.join(job["path"], file)

                with open(full, "rb") as f:
                    if file.endswith(".mp3"):
                        asyncio.run_coroutine_threadsafe(
                            app.bot.send_audio(job["chat_id"], f, title=job["title"]),
                            loop
                        )
                    else:
                        asyncio.run_coroutine_threadsafe(
                            app.bot.send_video(job["chat_id"], f, caption=job["title"]),
                            loop
                        )

                os.remove(full)

            os.rmdir(job["path"])

            async with aiosqlite.connect("bot.db") as db:
                await db.execute(
                    "INSERT INTO downloads VALUES (?, ?, ?, ?)",
                    (jid, uid, job["title"], "done")
                )
                await db.commit()

        except:
            await edit(job["msg"], "❌ Failed")

        active_users.remove(uid)

# ---------------- HANDLERS ----------------

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    info = get_info(url)

    context.user_data["url"] = url
    context.user_data["title"] = info.get("title", "video")

    keyboard = [
        [InlineKeyboardButton("🎬 720p", callback_data="video")],
        [InlineKeyboardButton("🎧 MP3", callback_data="audio")]
    ]

    await update.message.reply_text(
        f"🎬 {context.user_data['title']}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    url = context.user_data["url"]
    title = context.user_data["title"]

    jid = str(uuid.uuid4())[:8]
    folder = f"downloads/{jid}"
    os.makedirs(folder, exist_ok=True)

    msg = await q.message.reply_text("⏳ Queued...")

    cancel_flags[jid] = False
    pause_flags[jid] = False

    choice = q.data

    if choice == "video":
        opts = {
            "format": "best[height<=720]+bestaudio/best",
            "outtmpl": f"{folder}/{title}.%(ext)s",
            "progress_hooks": [progress_hook(msg, jid)]
        }
    else:
        opts = {
            "format": "bestaudio/best",
            "outtmpl": f"{folder}/{title}.%(ext)s",
            "progress_hooks": [progress_hook(msg, jid)],
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192"
            }]
        }

    job = {
        "id": jid,
        "user_id": q.from_user.id,
        "chat_id": q.message.chat_id,
        "url": url,
        "title": title,
        "path": folder,
        "opts": opts,
        "msg": msg
    }

    await queue.put(job)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⏸ Pause", callback_data=f"pause|{jid}")],
        [InlineKeyboardButton("▶ Resume", callback_data=f"resume|{jid}")],
        [InlineKeyboardButton("❌ Cancel", callback_data=f"cancel|{jid}")]
    ])

    await msg.edit_reply_markup(keyboard)

# ---------------- CONTROL ----------------

async def control(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    action, jid = q.data.split("|")

    if action == "cancel":
        cancel_flags[jid] = True
        await q.message.reply_text("❌ Cancelled")

    elif action == "pause":
        pause_flags[jid] = True
        await q.message.reply_text("⏸ Paused")

    elif action == "resume":
        pause_flags[jid] = False
        await q.message.reply_text("▶ Resumed")

# ---------------- START ----------------

async def post_init(app):
    await init_db()
    asyncio.create_task(worker(app))

app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(CallbackQueryHandler(handle_button))
app.add_handler(CallbackQueryHandler(control, pattern="^(pause|resume|cancel)\\|"))

app.run_polling()
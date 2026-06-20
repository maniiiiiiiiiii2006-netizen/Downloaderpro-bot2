import os
import re
import uuid
import asyncio
import yt_dlp

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    filters
)

BOT_TOKEN = os.getenv("BOT_TOKEN")

# ---------------- QUEUE ----------------
queue = asyncio.Queue()

# ---------------- UTIL ----------------
def extract_url(text):
    urls = re.findall(r'https?://\S+', text)
    return urls[0] if urls else None

def platform(url):
    if "youtube.com" in url or "youtu.be" in url:
        return "youtube"
    if "instagram.com" in url:
        return "instagram"
    return "unknown"

# ---------------- START ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 خوش اومدی!\n\n"
        "📥 لینک یوتیوب یا اینستا بفرست\n"
        "من برات دانلود می‌کنم 😎"
    )

# ---------------- MESSAGE ----------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = extract_url(update.message.text)

    if not url:
        await update.message.reply_text("❌ لینک پیدا نشد")
        return

    p = platform(url)

    if p == "unknown":
        await update.message.reply_text("❌ لینک پشتیبانی نمی‌شود")
        return

    context.user_data["url"] = url
    context.user_data["platform"] = p

    if p == "youtube":
        keyboard = [
            [
                InlineKeyboardButton("🎥 720p", callback_data="yt720"),
                InlineKeyboardButton("🎥 480p", callback_data="yt480"),
            ],
            [InlineKeyboardButton("🎧 MP3", callback_data="ytmp3")]
        ]
    else:
        keyboard = [
            [InlineKeyboardButton("⬇️ Download", callback_data="ig")]
        ]

    await update.message.reply_text(
        f"📥 شناسایی شد: {p}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ---------------- DOWNLOAD ----------------
async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    url = context.user_data.get("url")
    p = context.user_data.get("platform")

    job_id = str(uuid.uuid4())[:8]
    file_base = f"dl_{job_id}"

    await q.message.reply_text("⏳ در حال دانلود...")

    try:
        # ---------------- OPTIONS ----------------
        if p == "youtube":
            if q.data == "yt720":
                opts = {"format": "best[height<=720]", "outtmpl": f"{file_base}.%(ext)s"}

            elif q.data == "yt480":
                opts = {"format": "best[height<=480]", "outtmpl": f"{file_base}.%(ext)s"}

            else:
                opts = {
                    "format": "bestaudio/best",
                    "outtmpl": f"{file_base}.%(ext)s",
                    "postprocessors": [{
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192"
                    }]
                }

        else:
            opts = {
                "format": "best",
                "outtmpl": f"{file_base}.%(ext)s"
            }

        # ---------------- DOWNLOAD ----------------
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])

        # ---------------- SEND ----------------
        for f in os.listdir():
            if f.startswith(file_base):
                with open(f, "rb") as file:
                    if f.endswith(".mp3"):
                        await q.message.reply_audio(file)
                    else:
                        await q.message.reply_video(file)

                os.remove(f)
                break

    except Exception as e:
        await q.message.reply_text(f"❌ خطا:\n{e}")

# ---------------- MAIN ----------------
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(CallbackQueryHandler(handle_button))

app.run_polling()
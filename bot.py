import os
import re
import logging
import yt_dlp
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, ContextTypes, filters

# ---------------- LOG ----------------
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    print("[ERROR] BOT_TOKEN missing")
    exit()

print("[LOG] Bot started...")

# ---------------- URL ----------------
def extract_url(text):
    match = re.findall(r'https?://\S+', text)
    return match[0] if match else None


# ---------------- PLATFORM ----------------
def detect(url):
    if "youtube.com" in url or "youtu.be" in url:
        return "youtube"
    if "instagram.com" in url:
        return "instagram"
    return "unknown"


# ---------------- DOWNLOAD CORE (SMART + RETRY) ----------------
def download(url):
    platform = detect(url)
    print(f"[LOG] Platform: {platform}")

    os.makedirs("downloads", exist_ok=True)

    base_opts = {
        "outtmpl": "downloads/%(title).50s.%(ext)s",
        "noplaylist": True,
        "quiet": False,
        "no_warnings": True,
    }

    # 🔥 METHOD 1 (best mp4 no ffmpeg)
    try:
        print("[LOG] Try method 1: best mp4")
        opts = base_opts.copy()
        opts["format"] = "best[ext=mp4]/best"

        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)

        return file_path

    except Exception as e:
        print(f"[WARN] Method 1 failed: {e}")

    # 🔥 METHOD 2 (more aggressive)
    try:
        print("[LOG] Try method 2: best available")
        opts = base_opts.copy()
        opts["format"] = "best"

        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)

        return file_path

    except Exception as e:
        print(f"[ERROR] Method 2 failed: {e}")

    return None


# ---------------- SEND ----------------
async def send(update: Update, file_path: str):
    try:
        size = os.path.getsize(file_path) / (1024 * 1024)
        print(f"[LOG] Size: {size:.2f}MB")

        if size > 45:
            await update.message.reply_text("❌ فایل خیلی بزرگه برای تلگرام")
            return

        with open(file_path, "rb") as f:
            await update.message.reply_video(video=f)

        print("[LOG] Sent OK")

    except Exception as e:
        print(f"[ERROR] Send failed: {e}")
        await update.message.reply_text(f"❌ ارسال ناموفق: {e}")


# ---------------- HANDLER ----------------
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    print(f"[LOG] MSG: {text}")

    url = extract_url(text)

    if not url:
        await update.message.reply_text("❌ لینک پیدا نشد")
        return

    platform = detect(url)

    await update.message.reply_text(f"⏳ دانلود از {platform} ...")

    file = download(url)

    if not file:
        await update.message.reply_text("❌ دانلود شکست خورد (این لینک محدود شده)")
        return

    await update.message.reply_text("📤 در حال ارسال...")

    await send(update, file)


# ---------------- START ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔥 Bot PRO MAX فعال شد\n"
        "لینک YouTube / Instagram (Reels / Post) بفرست 🚀"
    )


# ---------------- MAIN ----------------
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

    print("[LOG] Running...")
    app.run_polling()


if __name__ == "__main__":
    main()

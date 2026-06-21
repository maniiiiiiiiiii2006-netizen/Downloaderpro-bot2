import os
import logging
import re
import yt_dlp
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

# ---------------- LOGGING ----------------
logging.basicConfig(
    format='[%(levelname)s] %(message)s',
    level=logging.INFO
)

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    print("[ERROR] BOT_TOKEN is missing!")
    exit()

print("[LOG] Bot starting...")

# ---------------- URL DETECTOR ----------------
def extract_url(text: str):
    urls = re.findall(r'https?://\S+', text)
    return urls[0] if urls else None


# ---------------- DOWNLOAD (NO FFMPEG) ----------------
def download_video(url: str):
    print(f"[LOG] Downloading: {url}")

    ydl_opts = {
        'format': 'best[ext=mp4]/best',   # 👈 بدون merge => بدون ffmpeg
        'outtmpl': 'downloads/%(title).50s.%(ext)s',
        'noplaylist': True,
        'quiet': False,
        'no_warnings': False,
    }

    os.makedirs("downloads", exist_ok=True)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)

        print(f"[LOG] Downloaded file: {file_path}")
        return file_path

    except Exception as e:
        print(f"[ERROR] Download failed: {e}")
        return None


# ---------------- SEND TO TELEGRAM ----------------
async def send_video(update: Update, file_path: str):
    try:
        print("[LOG] Sending video to Telegram...")

        with open(file_path, "rb") as f:
            await update.message.reply_video(video=f)

        print("[LOG] Sent successfully!")

    except Exception as e:
        print(f"[ERROR] Send failed: {e}")
        await update.message.reply_text(f"❌ Send failed: {e}")


# ---------------- HANDLER ----------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    print(f"[LOG] Message received: {text}")

    url = extract_url(text)

    if not url:
        await update.message.reply_text("❌ لینک پیدا نشد")
        return

    await update.message.reply_text("⏳ در حال دانلود...")

    file_path = download_video(url)

    if not file_path:
        await update.message.reply_text("❌ دانلود ناموفق بود")
        return

    await update.message.reply_text("📤 در حال ارسال...")

    await send_video(update, file_path)


# ---------------- START COMMAND ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 سلام!\n"
        "لینک یوتیوب یا اینستا بفرست تا دانلود کنم 🚀"
    )


# ---------------- MAIN ----------------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("[LOG] Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()

import os
import re
import logging
import requests
import yt_dlp
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
API = f"https://api.telegram.org/bot{BOT_TOKEN}"

logging.basicConfig(level=logging.INFO)

# -----------------------------
# LOG MESSAGE
# -----------------------------
def log(msg):
    print(f"[LOG] {msg}")


# -----------------------------
# DOWNLOAD PROGRESS
# -----------------------------
def progress_hook(d):
    if d['status'] == 'downloading':
        print(f"⬇️ {d['_percent_str']} | {d['_eta_str']} | {d['_speed_str']}")
    elif d['status'] == 'finished':
        print("✅ Download finished:", d['filename'])


# -----------------------------
# DOWNLOAD FUNCTION
# -----------------------------
def download_video(url):
    log(f"Starting download: {url}")

    ydl_opts = {
        'format': 'best',
        'outtmpl': '%(title)s.%(ext)s',
        'progress_hooks': [progress_hook],
        'quiet': False,
        'no_warnings': False,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        log(f"Download complete file: {filename}")
        return filename

    except Exception as e:
        log(f"DOWNLOAD ERROR: {e}")
        return None


# -----------------------------
# SEND VIDEO
# -----------------------------
def send_video(chat_id, file_path):
    log(f"Sending file: {file_path}")

    if not file_path or not os.path.exists(file_path):
        log("FILE NOT FOUND!")
        requests.post(API + "/sendMessage", data={
            "chat_id": chat_id,
            "text": "❌ فایل پیدا نشد یا دانلود انجام نشد"
        })
        return

    try:
        with open(file_path, "rb") as f:
            r = requests.post(
                API + "/sendVideo",
                data={"chat_id": chat_id},
                files={"video": f}
            )

        log(f"Telegram response: {r.text}")

    except Exception as e:
        log(f"SEND ERROR: {e}")


# -----------------------------
# URL DETECTOR
# -----------------------------
def extract_url(text):
    urls = re.findall(r'(https?://\S+)', text)
    return urls[0] if urls else None


# -----------------------------
# MESSAGE HANDLER
# -----------------------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    chat_id = update.message.chat_id

    log(f"Message received: {text}")

    await update.message.reply_text("⏳ در حال پردازش...")

    url = extract_url(text)

    if not url:
        await update.message.reply_text("❌ لینک معتبر پیدا نشد")
        return

    log(f"URL extracted: {url}")

    file_path = download_video(url)

    if not file_path:
        await update.message.reply_text("❌ دانلود ناموفق بود")
        return

    send_video(chat_id, file_path)

    await update.message.reply_text("✅ کار انجام شد")


# -----------------------------
# MAIN
# -----------------------------
def main():
    log("Bot starting...")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    log("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()

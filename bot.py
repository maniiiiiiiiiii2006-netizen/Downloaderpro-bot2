import logging
import re
import yt_dlp
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = "YOUR_TOKEN"

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

def is_youtube(url):
    return "youtube.com" in url or "youtu.be" in url

def is_instagram(url):
    return "instagram.com" in url

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "سلام 👋\nلینک YouTube یا Instagram بفرست تا دانلود کنم"
    )

def download_video(url):
    try:
        ydl_opts = {
            "outtmpl": "video.%(ext)s",
            "format": "best[ext=mp4]/best",
            "quiet": False
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return ydl.prepare_filename(info)

    except Exception as e:
        print("DOWNLOAD ERROR:", e)
        return None

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    logging.info(f"Got message: {text}")

    if not text.startswith("http"):
        await update.message.reply_text("لطفاً فقط لینک بفرست")
        return

    await update.message.reply_text("در حال دانلود... ⏳")

    try:
        file_path = download_video(text)

        if not file_path:
            await update.message.reply_text("❌ دانلود ناموفق بود")
            return

        await update.message.reply_video(video=open(file_path, "rb"))
        await update.message.reply_text("✅ انجام شد")

    except Exception as e:
        logging.error(e)
        await update.message.reply_text(f"❌ خطا:\n{e}")

def main():
    print("Bot started...")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()

if __name__ == "__main__":
    main()

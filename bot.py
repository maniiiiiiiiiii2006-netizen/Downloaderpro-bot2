import os
import re
import uuid
import asyncio
import yt_dlp

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

BOT_TOKEN = os.getenv("BOT_TOKEN")

# ---------------- UTIL ----------------

def extract_url(text):
    urls = re.findall(r'https?://\S+', text)
    return urls[0] if urls else None


def get_platform(url):
    if "youtube.com" in url or "youtu.be" in url:
        return "youtube"
    if "instagram.com" in url:
        return "instagram"
    return "unknown"


# ---------------- START ----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 سلام!\n\nلینک یوتیوب یا اینستا بفرست 😎"
    )


# ---------------- MESSAGE ----------------

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = extract_url(update.message.text)

    if not url:
        await update.message.reply_text("❌ لینک پیدا نشد")
        return

    platform = get_platform(url)

    if platform == "unknown":
        await update.message.reply_text("❌ لینک پشتیبانی نمی‌شود")
        return

    context.user_data["url"] = url

    if platform == "youtube":
        keyboard = [
            [
                InlineKeyboardButton("720p", callback_data="yt_720"),
                InlineKeyboardButton("480p", callback_data="yt_480"),
            ],
            [InlineKeyboardButton("MP3", callback_data="yt_mp3")]
        ]
    else:
        keyboard = [[InlineKeyboardButton("Download", callback_data="ig")]]

    await update.message.reply_text(
        f"📥 {platform} detected",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ---------------- DOWNLOAD ----------------

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    url = context.user_data.get("url")

    job_id = str(uuid.uuid4())[:8]
    base = f"dl_{job_id}"

    await q.message.reply_text("⏳ در حال دانلود...")

    try:
        if q.data == "yt_720":
            opts = {"format": "best[height<=720]", "outtmpl": f"{base}.%(ext)s"}

        elif q.data == "yt_480":
            opts = {"format": "best[height<=480]", "outtmpl": f"{base}.%(ext)s"}

        elif q.data == "yt_mp3":
            opts = {
                "format": "bestaudio/best",
                "outtmpl": f"{base}.%(ext)s",
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }]
            }

        else:
            opts = {"format": "best", "outtmpl": f"{base}.%(ext)s"}

        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])

        for f in os.listdir():
            if f.startswith(base):
                with open(f, "rb") as file:
                    if f.endswith(".mp3"):
                        await q.message.reply_audio(file)
                    else:
                        await q.message.reply_video(file)
                os.remove(f)
                break

    except Exception as e:
        await q.message.reply_text(f"❌ Error:\n{e}")


# ---------------- MAIN ----------------

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_button))

    app.run_polling()


if __name__ == "__main__":
    main()
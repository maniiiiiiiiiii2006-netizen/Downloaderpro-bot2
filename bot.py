import os
import re
import uuid
import requests
import yt_dlp

TOKEN = os.getenv("BOT_TOKEN")
API = f"https://api.telegram.org/bot{TOKEN}"

user_data = {}

# ---------------- Telegram API ----------------

def send_message(chat_id, text, reply_markup=None):
    data = {"chat_id": chat_id, "text": text}
    if reply_markup:
        data["reply_markup"] = reply_markup
    requests.post(API + "/sendMessage", json=data)


def send_video(chat_id, path):
    with open(path, "rb") as f:
        requests.post(API + "/sendVideo", files={"video": f}, data={"chat_id": chat_id})


def send_audio(chat_id, path):
    with open(path, "rb") as f:
        requests.post(API + "/sendAudio", files={"audio": f}, data={"chat_id": chat_id})


# ---------------- Helpers ----------------

def extract_url(text):
    match = re.search(r"https?://\S+", text)
    return match.group() if match else None


# ---------------- Download ----------------

def download(url, mode):
    name = f"file_{uuid.uuid4().hex[:8]}"

    if mode == "720":
        opts = {"format": "best[height<=720]", "outtmpl": f"{name}.%(ext)s"}
    elif mode == "480":
        opts = {"format": "best[height<=480]", "outtmpl": f"{name}.%(ext)s"}
    else:
        opts = {
            "format": "bestaudio/best",
            "outtmpl": f"{name}.%(ext)s",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }]
        }

    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])

    for f in os.listdir():
        if f.startswith(name):
            return f

    return None


# ---------------- Bot Loop ----------------

def get_updates(offset=None):
    url = API + "/getUpdates"
    params = {"timeout": 30, "offset": offset}
    return requests.get(url, params=params).json()


def main():
    offset = None

    print("Bot started...")

    while True:
        updates = get_updates(offset)

        for update in updates["result"]:
            offset = update["update_id"] + 1

            msg = update.get("message")
            if not msg:
                continue

            chat_id = msg["chat"]["id"]
            text = msg.get("text", "")

            # start
            if text == "/start":
                send_message(chat_id, "👋 سلام!\nلینک یوتیوب یا اینستا بفرست")
                continue

            url = extract_url(text)

            if url:
                user_data[chat_id] = url

                keyboard = {
                    "inline_keyboard": [
                        [
                            {"text": "720p", "callback_data": "720"},
                            {"text": "480p", "callback_data": "480"}
                        ],
                        [
                            {"text": "MP3", "callback_data": "mp3"}
                        ]
                    ]
                }

                send_message(chat_id, "📥 چی میخوای؟", keyboard)

            # callback handling
            if "callback_query" in update:
                cq = update["callback_query"]
                chat_id = cq["message"]["chat"]["id"]
                data = cq["data"]

                url = user_data.get(chat_id)
                if not url:
                    send_message(chat_id, "❌ لینک پیدا نشد")
                    continue

                send_message(chat_id, "⏳ در حال دانلود...")

                if data == "720":
                    file = download(url, "720")
                    send_video(chat_id, file)

                elif data == "480":
                    file = download(url, "480")
                    send_video(chat_id, file)

                else:
                    file = download(url, "mp3")
                    send_audio(chat_id, file)

                if file:
                    os.remove(file)


if __name__ == "__main__":
    main()

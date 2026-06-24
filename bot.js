const TelegramBot = require("node-telegram-bot-api");
const fs = require("fs-extra");
const path = require("path");
const { exec } = require("child_process");

const TOKEN = process.env.BOT_TOKEN;
const bot = new TelegramBot(TOKEN, { polling: true });

console.log("🤖 Bot started...");

const DOWNLOAD_DIR = path.join(__dirname, "downloads");
fs.ensureDirSync(DOWNLOAD_DIR);

let queue = [];
let processing = false;

function isUrl(text) {
  return text && text.startsWith("http");
}

// اجرای yt-dlp مستقیم از سیستم
function download(url, output) {
  return new Promise((resolve, reject) => {
    const cmd = `yt-dlp -f best -o "${output}" "${url}"`;

    exec(cmd, (err, stdout, stderr) => {
      if (err) return reject(stderr || err.message);
      resolve(stdout);
    });
  });
}

async function processQueue() {
  if (processing) return;
  processing = true;

  while (queue.length > 0) {
    const job = queue.shift();
    const { chatId, url } = job;

    const fileName = `video_${Date.now()}.mp4`;
    const filePath = path.join(DOWNLOAD_DIR, fileName);

    try {
      await bot.sendMessage(chatId, "⏳ در حال دانلود...");

      await download(url, filePath);

      await bot.sendMessage(chatId, "📤 در حال ارسال...");

      await bot.sendVideo(chatId, fs.createReadStream(filePath));

      await bot.sendMessage(chatId, "✅ انجام شد!");

      // حذف فایل بعد از ارسال
      fs.remove(filePath);

    } catch (err) {
      console.log(err);
      bot.sendMessage(chatId, "❌ خطا در دانلود لینک");
    }
  }

  processing = false;
}

// دریافت پیام
bot.on("message", (msg) => {
  const chatId = msg.chat.id;
  const text = msg.text;

  if (!isUrl(text)) return;

  queue.push({ chatId, url: text });

  bot.sendMessage(chatId, "📥 اضافه شد به صف");

  processQueue();
});

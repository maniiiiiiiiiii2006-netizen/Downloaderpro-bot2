const TelegramBot = require("node-telegram-bot-api");
const ytdlp = require("yt-dlp-exec");
const fs = require("fs-extra");
const path = require("path");

const TOKEN = process.env.BOT_TOKEN;
const bot = new TelegramBot(TOKEN, { polling: true });

console.log("🚀 Advanced Bot Started");

const DOWNLOAD_DIR = path.join(__dirname, "downloads");
fs.ensureDirSync(DOWNLOAD_DIR);

// ---------------- STATE ----------------
const userState = {};
let queue = [];
let active = 0;
const MAX_CONCURRENT = 2;
const CLEANUP_TIME = 24 * 60 * 60 * 1000;

// ---------------- HELPERS ----------------
const isUrl = (t) => t && t.startsWith("http");

// ---------------- CLEANUP ----------------
function cleanup() {
  const now = Date.now();

  const files = fs.readdirSync(DOWNLOAD_DIR)
    .map(f => ({
      name: f,
      time: fs.statSync(path.join(DOWNLOAD_DIR, f)).mtimeMs
    }))
    .sort((a, b) => b.time - a.time);

  // فقط 2 فایل آخر نگه دار
  files.slice(2).forEach(f => {
    fs.removeSync(path.join(DOWNLOAD_DIR, f.name));
  });

  // پاکسازی 24 ساعته
  files.forEach(f => {
    if (now - f.time > CLEANUP_TIME) {
      fs.removeSync(path.join(DOWNLOAD_DIR, f.name));
    }
  });
}

// ---------------- INFO ----------------
async function getInfo(url) {
  return await ytdlp(url, { dumpSingleJson: true });
}

// ---------------- DOWNLOAD ----------------
async function download(url, format, filePath, chatId, progressMsgId) {
  return new Promise((resolve, reject) => {
    const proc = ytdlp.exec(url, {
      format,
      output: filePath,
      mergeOutputFormat: "mp4"
    });

    proc.stdout.on("data", async (d) => {
      const txt = d.toString();
      const match = txt.match(/(\d+\.\d+)%/);

      if (match) {
        try {
          await bot.editMessageText(
            `📥 دانلود: ${match[1]}%`,
            { chat_id: chatId, message_id: progressMsgId }
          );
        } catch {}
      }
    });

    proc.on("close", resolve);
    proc.on("error", reject);
  });
}

// ---------------- QUEUE ----------------
async function processQueue() {
  if (active >= MAX_CONCURRENT || queue.length === 0) return;

  const job = queue.shift();
  active++;

  const { chatId, url } = job;

  try {
    const format = userState[chatId]?.format || "best";

    const fileName = `dl_${Date.now()}.mp4`;
    const filePath = path.join(DOWNLOAD_DIR, fileName);

    const progressMsg = await bot.sendMessage(chatId, "⏳ شروع دانلود...");

    await download(url, format, filePath, chatId, progressMsg.message_id);

    await bot.editMessageText("📤 در حال ارسال...", {
      chat_id: chatId,
      message_id: progressMsg.message_id
    });

    await bot.sendVideo(chatId, fs.createReadStream(filePath));

    await bot.sendMessage(chatId, "✅ Done");

    cleanup();

  } catch (e) {
    console.log(e);
    bot.sendMessage(chatId, "❌ خطا");
  }

  active--;
  processQueue();
}

// ---------------- QUALITY BUTTONS ----------------
function sendFormats(chatId, formats) {
  const buttons = formats.slice(0, 6).map(f => ([
    {
      text: `${f.height || "audio"}p`,
      callback_data: f.format_id
    }
  ]));

  bot.sendMessage(chatId, "🎛 انتخاب کیفیت:", {
    reply_markup: { inline_keyboard: buttons }
  });
}

// ---------------- EVENTS ----------------

// start
bot.onText(/\/start/, (msg) => {
  bot.sendMessage(msg.chat.id, "👋 لینک بده تا کیفیت‌ها رو بدم");
});

// message
bot.on("message", async (msg) => {
  const chatId = msg.chat.id;
  const text = msg.text;

  if (!isUrl(text)) return;

  // anti spam
  const last = userState[chatId]?.last || 0;
  if (Date.now() - last < 4000) {
    bot.sendMessage(chatId, "🚫 صبر کن یه کم 😅");
    return;
  }

  userState[chatId] = { ...userState[chatId], last: Date.now(), url: text };

  try {
    const info = await getInfo(text);

    // thumbnail + title
    await bot.sendPhoto(chatId, info.thumbnail, {
      caption: `🎬 ${info.title}`
    });

    // فیلتر کیفیت‌ها
    const formats = info.formats.filter(f => f.height);

    sendFormats(chatId, formats);

  } catch (e) {
    console.log(e);
    bot.sendMessage(chatId, "❌ نتونستم اطلاعات بگیرم");
  }
});

// انتخاب کیفیت
bot.on("callback_query", (q) => {
  const chatId = q.message.chat.id;
  const formatId = q.data;

  const url = userState[chatId]?.url;

  if (!url) {
    bot.sendMessage(chatId, "❌ لینک پیدا نشد");
    return;
  }

  userState[chatId].format = formatId;

  queue.push({ chatId, url });

  bot.sendMessage(chatId, "📥 رفت تو صف");

  processQueue();
});
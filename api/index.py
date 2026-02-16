import os
import re
import logging
import glob
import asyncio
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler
import yt_dlp

# Flask ilovasi
app = Flask(__name__)

# Loglarni sozlash
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = "8260660936:AAEfpLwpL9EcOhzNrbzq3bmWZKzftNElKac"

# Botni webhook rejimida sozlash
application = Application.builder().token(BOT_TOKEN).build()
user_searches = {}

# -------------------- YORDAMCHI FUNKSIYALAR --------------------

def is_url(text):
    return re.match(r'https?://[^\s]+', text) is not None

def get_platform(url):
    if 'instagram.com' in url:
        return 'instagram'
    return None

# -------------------- HANDLERLAR --------------------

async def start(update: Update, context):
    await update.message.reply_text(
        "🎵 Salom! Bot Vercel serverless rejimida ishlamoqda.\n\n"
        "1️⃣ **Qo'shiq nomi** yozing\n"
        "2️⃣ **Instagram link** yuboring"
    )

async def handle_message(update: Update, context):
    text = update.message.text.strip()
    if is_url(text):
        if get_platform(text) == 'instagram':
            await download_media(update, context, text)
        else:
            await update.message.reply_text("❌ Faqat Instagram linklarini yuboring!")
    else:
        await update.message.reply_text(f"🔍 '{text}' bo'yicha qidiruv (Vercel vaqt cheklovi tufayli qidiruv cheklangan bo'lishi mumkin)")

async def download_media(update: Update, context, url):
    msg = await update.message.reply_text("⚡ Instagramdan yuklanmoqda...")
    try:
        os.makedirs('/tmp/downloads', exist_ok=True) # Vercel faqat /tmp papkasiga yozishga ruxsat beradi
        ydl_opts = {
            'format': 'best',
            'outtmpl': '/tmp/downloads/%(id)s.%(ext)s',
            'quiet': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_file = ydl.prepare_filename(info)

        if os.path.exists(video_file):
            with open(video_file, 'rb') as video:
                await update.message.reply_video(video=video, caption="✅ Instagramdan yuklandi!")
            os.remove(video_file)
        await msg.delete()
    except Exception as e:
        logger.error(e)
        await msg.edit_text("❌ Yuklab bo'lmadi. Vercel vaqt limiti (10s) tugagan bo'lishi mumkin.")

# -------------------- WEBHOOK VA FLASK --------------------

@app.route('/', methods=['GET'])
def home():
    return "Bot is active!"

@app.route('/', methods=['POST'])
async def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    await application.initialize()
    await application.process_update(update)
    return "ok", 200

# Handlerlarni ro'yxatga olish
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
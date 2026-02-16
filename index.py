import os
import re
import logging
import glob
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import yt_dlp

# Loglarni sozlash
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot tokeningiz
BOT_TOKEN = "8260660936:AAEfpLwpL9EcOhzNrbzq3bmWZKzftNElKac"

user_searches = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎵 Salom!\n\n"
        "1️⃣ **Qo'shiq nomi** yozing (Musiqa qidirish)\n"
        "2️⃣ **Instagram link** yuboring (Video yuklash)"
    )

def is_url(text):
    return re.match(r'https?://[^\s]+', text) is not None

def get_platform(url):
    if 'instagram.com' in url:
        return 'instagram'
    return None

# -------------------- MUSIQA QIDIRUV --------------------

async def search_music(query):
    try:
        search_query = f"ytsearch15:{query} soundcloud"
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'skip_download': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(search_query, download=False)
            if result and 'entries' in result:
                return [e for e in result['entries'] if e]
    except Exception as e:
        logger.error(f"Qidiruv xatosi: {e}")
    return []

def create_music_keyboard(results, page=0, user_id=None):
    keyboard = []
    start_idx = page * 10
    end_idx = min(start_idx + 10, len(results))

    for i in range(start_idx, end_idx):
        item = results[i]
        title = item.get('title', 'Nomsiz')[:50]
        callback_data = f"dl_{i}_{user_id}"
        keyboard.append([InlineKeyboardButton(f"🎵 {title}", callback_data=callback_data)])

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️", callback_data=f"page_{page-1}_{user_id}"))
    if end_idx < len(results):
        nav_buttons.append(InlineKeyboardButton("➡️", callback_data=f"page_{page+1}_{user_id}"))

    if nav_buttons:
        keyboard.append(nav_buttons)

    return InlineKeyboardMarkup(keyboard)

# -------------------- XABARLARNI QABUL QILISH --------------------

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.effective_user.id

    if is_url(text):
        platform = get_platform(text)
        if platform == 'instagram':
            await download_media(update, context, text)
        else:
            await update.message.reply_text("❌ Hozircha faqat Instagram havolalari qo'llab-quvvatlanadi!")
    else:
        msg = await update.message.reply_text("🔍 Qidirilmoqda...")
        results = await search_music(text)

        if not results:
            await msg.edit_text("❌ Musiqa topilmadi.")
            return

        user_searches[user_id] = results
        keyboard = create_music_keyboard(results, 0, user_id)
        await msg.edit_text("🎵 Tanlang:", reply_markup=keyboard)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id

    if data.startswith('page_'):
        _, page, uid = data.split('_')
        if int(uid) != user_id: return
        results = user_searches.get(user_id, [])
        keyboard = create_music_keyboard(results, int(page), user_id)
        await query.edit_message_reply_markup(reply_markup=keyboard)

    elif data.startswith('dl_'):
        _, index, uid = data.split('_')
        if int(uid) != user_id: return
        results = user_searches.get(user_id, [])
        result = results[int(index)]
        url = result.get('url') or result.get('webpage_url')
        title = result.get('title', 'Qo‘shiq')
        await query.edit_message_text("⏳ Musiqa yuklanmoqda...")
        await download_music(query, context, url, title)

# -------------------- YUKLAB BERUVCHILAR --------------------

async def download_music(query, context, url, title):
    try:
        os.makedirs('downloads', exist_ok=True)
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': 'downloads/%(id)s.%(ext)s',
            'quiet': True,
            'noplaylist': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            audio_file = ydl.prepare_filename(info)

        with open(audio_file, 'rb') as audio:
            await context.bot.send_audio(
                chat_id=query.message.chat_id,
                audio=audio,
                title=title[:100]
            )
        if os.path.exists(audio_file):
            os.remove(audio_file)
        await query.edit_message_text("✅ Tayyor!")
    except Exception as e:
        logger.error(f"Musiqa xatosi: {e}")
        await query.edit_message_text("❌ Yuklashda xatolik yuz berdi.")

async def download_media(update: Update, context: ContextTypes.DEFAULT_TYPE, url):
    msg = await update.message.reply_text("⚡ Instagramdan yuklanmoqda...")
    try:
        os.makedirs('downloads', exist_ok=True)
        ydl_opts = {
            'format': 'best',
            'outtmpl': 'downloads/%(id)s.%(ext)s',
            'quiet': True,
            'no_warnings': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'referer': 'https://www.instagram.com/',
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_file = ydl.prepare_filename(info)
            
            # Fayl nomini qayta tekshirish
            if not os.path.exists(video_file):
                base_name = os.path.splitext(video_file)[0]
                found_files = glob.glob(f"{base_name}.*")
                if found_files:
                    video_file = found_files[0]

        await msg.edit_text("📤 Yuborilmoqda...")

        if os.path.exists(video_file):
            with open(video_file, 'rb') as video:
                await update.message.reply_video(
                    video=video, 
                    caption="✅ Instagramdan yuklandi!",
                    supports_streaming=True
                )
            os.remove(video_file)
            await msg.delete()
        else:
            await msg.edit_text("❌ Video fayli topilmadi.")

    except Exception as e:
        logger.error(f"Instagram xatosi: {e}")
        await msg.edit_text("❌ Instagram videosini yuklab bo'lmadi. (Profil yopiq yoki link xato)")

# -------------------- ASOSIY QISM --------------------

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    print("✅ Bot ishga tushdi! (Instagram & Musiqa)")
    application.run_polling()

if __name__ == '__main__':
    main()
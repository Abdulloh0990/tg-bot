import os
import asyncio
import yt_dlp
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from aiogram import Bot, Dispatcher, types, F
from aiogram.utils.keyboard import InlineKeyboardBuilder

# --- Render учун Dummy Server ---
def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), BaseHTTPRequestHandler)
    server.serve_forever()

threading.Thread(target=run_dummy_server, daemon=True).start()

# --- Созламалар ---
TOKEN = "8260660936:AAH52t9eFso4wNpSOb3Pss9BeJnAL3Pdz1I"
bot = Bot(token=TOKEN)
dp = Dispatcher()

# YouTube блокировкаларини олдини олиш ва созламаларни соддалаштириш
COMMON_OPTS = {
    'quiet': True,
    'no_warnings': True,
    'nocheckcertificate': True,
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
}

# --- Функциялар ---
async def search_music(query):
    # Фақат SoundCloud-дан қидириш
    opts = {
        **COMMON_OPTS,
        'format': 'bestaudio/best',
        'default_search': 'scsearch10', 
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = await asyncio.to_thread(ydl.extract_info, f"scsearch10:{query}", download=False)
            if not info or 'entries' not in info:
                return []
            return [{'title': e.get('title', 'Unknown')[:50], 'url': e.get('webpage_url')} for e in info['entries']]
    except Exception:
        return []

async def download_media(url, mode="video"):
    file_id = f"dl_{abs(hash(url))}"
    opts = {**COMMON_OPTS}
    
    if mode == "video":
        opts.update({
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best', 
            'outtmpl': f"{file_id}.mp4"
        })
    else:
        opts.update({
            'format': 'bestaudio/best', 
            'outtmpl': f"{file_id}.%(ext)s", 
            'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}]
        })
    
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = await asyncio.to_thread(ydl.extract_info, url, download=True)
            filename = ydl.prepare_filename(info)
            return filename if mode == "video" else filename.rsplit('.', 1)[0] + ".mp3"
    except Exception:
        return None

# --- Handlerлар ---

@dp.message(F.text == "/start")
async def send_welcome(message: types.Message):
    await message.answer("👋 Бу бот Instagram-дан видео юклайди ва исталган қўшиғингиз номини киритсангиз топиб беради.")

@dp.callback_query(F.data.startswith("music_"))
async def download_chosen_music(callback: types.CallbackQuery):
    url = callback.data.replace("music_", "")
    await callback.message.edit_text("⏳ Мусиқа юкланмоқда, озгина кутинг...")
    
    path = await download_media(url, mode="audio")
    if path and os.path.exists(path):
        await callback.message.answer_audio(types.FSInputFile(path))
        await callback.message.delete()
        os.remove(path)
    else:
        await callback.message.edit_text("❌ Мусиқани юклашда хатолик бўлди.")

@dp.message(F.text)
async def handle_msg(message: types.Message):
    text = message.text
    if text.startswith("/"): return

    if "instagram.com" in text:
        status = await message.answer("⚡️ Инстаграм юкланмоқда...")
        path = await download_media(text, mode="video")
        if path and os.path.exists(path):
            await message.answer_video(types.FSInputFile(path), caption="🎬 Видео юкланди")
            os.remove(path)
        else:
            await message.answer("❌ Инстаграм ҳозирча бу видеони юклашга рухсат бермади.")
        await status.delete()
    
    else:
        status = await message.answer("🔍 Қидирилмоқда...")
        results = await search_music(text)
        if not results:
            await message.answer("❌ Мусиқа топилмади.")
            await status.delete()
            return

        kb = InlineKeyboardBuilder()
        for i, r in enumerate(results, 1):
            kb.button(text=str(i), callback_data=f"music_{r['url']}")
        kb.adjust(5)
        
        msg_text = "🎶 Натижалар:\n" + "\n".join([f"{i}. {r['title']}" for i, r in enumerate(results, 1)])
        msg_text += "\n\n⬇️ Юклаб олиш учун рақамни босинг:"
        await message.answer(msg_text, reply_markup=kb.as_markup())
        await status.delete()

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
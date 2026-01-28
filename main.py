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

COMMON_OPTS = {
    'quiet': True,
    'no_warnings': True,
    'nocheckcertificate': True,
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
}

# --- Функциялар ---
async def search_music(query):
    # YouTube ўрнига SoundCloud қидируви ишлатилади
    opts = {
        **COMMON_OPTS,
        'format': 'bestaudio/best',
        'default_search': 'scsearch10', 
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            # scsearch қидируви YouTube каби блокланмайди
            info = await asyncio.to_thread(ydl.extract_info, f"scsearch10:{query}", download=False)
            if not info or 'entries' not in info:
                return []
            return [{'title': e.get('title', 'Unknown')[:50], 'url': e.get('webpage_url')} for e in info['entries']]
    except Exception as e:
        print(f"Search error: {e}")
        return []

async def download_media(url, mode="video"):
    file_id = f"file_{abs(hash(url))}_{mode}"
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
    
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = await asyncio.to_thread(ydl.extract_info, url, download=True)
        filename = ydl.prepare_filename(info)
        return filename if mode == "video" else filename.rsplit('.', 1)[0] + ".mp3"

# --- Handlerлар ---
@dp.message(F.text)
async def handle_msg(message: types.Message):
    text = message.text
    if "instagram.com" in text:
        status = await message.answer("⚡️ Инстаграм юкланмоқда...")
        try:
            video_path = await download_media(text, mode="video")
            audio_path = await download_media(text, mode="audio")
            await message.answer_video(types.FSInputFile(video_path), caption="🎬 Видео")
            await message.answer_audio(types.FSInputFile(audio_path), caption="🎵 Мусиқа")
            os.remove(video_path)
            os.remove(audio_path)
        except Exception as e:
            await message.answer(f"❌ Хатолик: {str(e)}")
        finally:
            await status.delete()
    else:
        status = await message.answer("🔍 SoundCloud-дан қидирилмоқда...")
        try:
            results = await search_music(text)
            if not results:
                await message.answer("❌ Мусиқа топилмади.")
                return

            kb = InlineKeyboardBuilder()
            for i, r in enumerate(results, 1):
                kb.button(text=str(i), url=r['url'])
            kb.adjust(5)
            
            msg_text = "🎶 Натижалар (SoundCloud):\n" + "\n".join([f"{i}. {r['title']}" for i, r in enumerate(results, 1)])
            await message.answer(msg_text, reply_markup=kb.as_markup())
        except:
            await message.answer("❌ Қидирувда хатолик.")
        finally:
            await status.delete()

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
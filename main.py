import os
import asyncio
import yt_dlp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Токен ва созламалар
TOKEN = "8260660936:AAH52t9eFso4wNpSOb3Pss9BeJnAL3Pdz1I"
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Мусиқа қидириш
async def search_music(query):
    opts = {'format': 'bestaudio/best', 'quiet': True, 'default_search': 'ytsearch10'}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = await asyncio.to_thread(ydl.extract_info, f"ytsearch10:{query}", download=False)
        return [{'title': e['title'][:50], 'url': e['webpage_url'], 'dur': e.get('duration_string', '0:00')} for e in info['entries']]

# Юклаш функцияси
async def download_task(url, is_video=False):
    file_id = f"file_{abs(hash(url))}"
    opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best' if is_video else 'bestaudio/best',
        'outtmpl': f"{file_id}.%(ext)s",
        'quiet': True,
        'cachedir': False,
    }
    if not is_video:
        opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '128'}]

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = await asyncio.to_thread(ydl.extract_info, url, download=True)
        return ydl.prepare_filename(info).rsplit('.', 1)[0] + (".mp4" if is_video else ".mp3")

@dp.message(F.text)
async def handle_msg(message: types.Message):
    if "instagram.com" in message.text:
        status = await message.answer("⚡️ Инстаграм юкланмоқда...")
        path = await download_task(message.text, True)
        await message.answer_video(types.FSInputFile(path))
        os.remove(path)
        await status.delete()
    else:
        # Қидирув натижалари тугмачалар билан
        status = await message.answer("🔍 Қидирилмоқда...")
        results = await search_music(message.text)
        kb = InlineKeyboardBuilder()
        for i, r in enumerate(results, 1):
            kb.button(text=str(i), callback_data=f"dl_{i}")
        kb.adjust(5)
        await message.answer("🎶 Натижалар:\n" + "\n".join([f"{i}. {r['title']}" for i, r in enumerate(results, 1)]), reply_markup=kb.as_markup())
        await status.delete()

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
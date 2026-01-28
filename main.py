import os
import asyncio
import yt_dlp
import threading
import random
from http.server import HTTPServer, BaseHTTPRequestHandler
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

# --- Render Dummy Server ---
def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), BaseHTTPRequestHandler)
    server.serve_forever()

threading.Thread(target=run_dummy_server, daemon=True).start()

TOKEN = "8260660936:AAH52t9eFso4wNpSOb3Pss9BeJnAL3Pdz1I"
bot = Bot(token=TOKEN)
dp = Dispatcher()

temp_urls = {}

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
]

def get_yt_opts(url, mode="audio"):
    file_id = f"dl_{random.randint(1000, 9999)}"
    opts = {
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'user_agent': random.choice(USER_AGENTS),
        'geo_bypass': True,
    }
    
    # Instagram учун алоҳида созламалар
    if "instagram.com" in url:
        opts['extractor_args'] = {'instagram': {'check_headers': True}}
        # Агар куки файли бор бўлсагина уни ишлатамиз
        if os.path.exists('instagram_cookies.txt'):
            opts['cookiefile'] = 'instagram_cookies.txt'
    
    if mode == "video":
        opts.update({
            'format': 'best',
            'outtmpl': f"{file_id}.mp4",
        })
    else:
        opts.update({
            'format': 'bestaudio/best',
            'outtmpl': f"{file_id}.%(ext)s",
            'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}]
        })
    return opts, file_id

async def search_music(query, offset=1):
    opts = {'quiet': True, 'extract_flat': True, 'user_agent': random.choice(USER_AGENTS)}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = await asyncio.to_thread(ydl.extract_info, f"ytsearch30:{query}", download=False)
            entries = [e for e in info.get('entries', []) if e]
            start = (offset - 1) * 10
            res = [{'title': e.get('title', 'Unknown')[:45], 'url': e.get('url')} for e in entries[start:start+10]]
            return res, len(entries) > (start + 10)
    except Exception as e:
        print(f"Search error: {e}")
        return [], False

async def download_task(url, mode="audio"):
    if "instagram.com" in url:
        url = url.split("?")[0]
        
    opts, file_id = get_yt_opts(url, mode)
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            await asyncio.to_thread(ydl.download, [url])
            ext = "mp4" if mode == "video" else "mp3"
            filename = f"{file_id}.{ext}"
            return filename if os.path.exists(filename) else None
    except Exception as e:
        print(f"Download error: {e}")
        return None

def build_music_kb(results, query, page, has_next):
    kb = InlineKeyboardBuilder()
    for i, r in enumerate(results, 1):
        key = f"dl_{abs(hash(r['url']))}"
        temp_urls[key] = r['url']
        kb.button(text=str(i), callback_data=key)
    kb.adjust(5)
    nav = []
    if page > 1: nav.append(types.InlineKeyboardButton(text="⬅️ Ортга", callback_data=f"page_{query}_{page-1}"))
    if has_next: nav.append(types.InlineKeyboardButton(text="Кейинги ➡️", callback_data=f"page_{query}_{page+1}"))
    if nav: kb.row(*nav)
    return kb.as_markup()

@dp.message(Command("start"))
async def cmd_start(m: types.Message):
    await m.answer("👋 Салом! Instagram ҳаволасини юборинг ёки мусиқа номини ёзинг:")

@dp.message(F.text)
async def handle_msg(m: types.Message):
    if "instagram.com" in m.text:
        st = await m.answer("⚡️ Инстаграм юкланмоқда...")
        path = await download_task(m.text, "video")
        if path:
            await m.answer_video(types.FSInputFile(path))
            os.remove(path)
        else:
            await m.answer("❌ Юклаб бўлмади. Бот блокланган бўлиши мумкин.")
        await st.delete()
    else:
        st = await m.answer("🔍 Қидирилмоқда...")
        results, has_next = await search_music(m.text, 1)
        if not results:
            await m.answer("❌ Топилмади.")
        else:
            text = f"🎶 **Натижалар (1-бет):**\n\n" + "\n".join([f"{i}. {r['title']}" for i, r in enumerate(results, 1)])
            await m.answer(text, reply_markup=build_music_kb(results, m.text, 1, has_next))
        await st.delete()

@dp.callback_query(F.data.startswith("page_"))
async def change_page(call: types.CallbackQuery):
    _, query, page = call.data.split("_")
    page = int(page)
    results, has_next = await search_music(query, page)
    if results:
        text = f"🎶 **Натижалар ({page}-бет):**\n\n" + "\n".join([f"{i}. {r['title']}" for i, r in enumerate(results, 1)])
        await call.message.edit_text(text, reply_markup=build_music_kb(results, query, page, has_next))

@dp.callback_query(F.data.startswith("dl_"))
async def dl_music(call: types.CallbackQuery):
    url = temp_urls.get(call.data)
    if not url: 
        return await call.answer("❌ Хатолик, қайта қидиринг.", show_alert=True)
    
    await call.answer("Мусиқа тайёрланмоқда...")
    msg = await call.message.answer("⏳ Юкланмоқда...")
    path = await download_task(url, "audio")
    
    if path:
        await call.message.answer_audio(types.FSInputFile(path))
        os.remove(path)
    else:
        await call.message.answer("❌ Кечирасиз, мусиқани юклаб бўлмади.")
    await msg.delete()

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
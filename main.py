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

TOKEN = "8260660936:AAEfpLwpL9EcOhzNrbzq3bmWZKzftNElKac"
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
    
    # Instagram va TikTok uchun maxsus sozlamalar
    if "instagram.com" in url or "tiktok.com" in url:
        opts['extractor_args'] = {'instagram': {'check_headers': True}, 'tiktok': {'check_headers': True}}
        if os.path.exists('cookies.txt'): # Agar cookies bo'lsa
            opts['cookiefile'] = 'cookies.txt'
    
    if mode == "video":
        opts.update({
            'format': 'bestvideo+bestaudio/best',
            'outtmpl': f"{file_id}.mp4",
            'merge_output_format': 'mp4',
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
            # Musiqa qidiruvini SoundCloud (scsearch) orqali qilamiz - barqarorroq
            info = await asyncio.to_thread(ydl.extract_info, f"scsearch30:{query}", download=False)
            entries = [e for e in info.get('entries', []) if e]
            start = (offset - 1) * 10
            res = [{'title': e.get('title', 'Unknown')[:45], 'url': e.get('url')} for e in entries[start:start+10]]
            return res, len(entries) > (start + 10)
    except Exception as e:
        print(f"Search error: {e}")
        return [], False

async def download_task(url, mode="audio"):
    # Linklarni tozalash
    if "instagram.com" in url or "tiktok.com" in url:
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

# --- Handlerlar ---

@dp.message(Command("start"))
async def cmd_start(m: types.Message):
    await m.answer("👋 Salom! Instagram/TikTok havolasini yuboring yoki musiqa nomini yozing:")

@dp.message(F.text)
async def handle_msg(m: types.Message):
    # Video yuklash (Insta/TikTok)
    if any(x in m.text for x in ["instagram.com", "tiktok.com", "v.douyin.com"]):
        st = await m.answer("⚡️ Video yuklanmoqda...")
        path = await download_task(m.text, "video")
        if path:
            await m.answer_video(types.FSInputFile(path))
            os.remove(path)
        else:
            await m.answer("❌ Yuklab bo'lmadi. Havola noto'g'ri yoki bot bloklangan.")
        await st.delete()
    
    # Musiqa qidirish
    else:
        st = await m.answer("🔍 Qidirilmoqda...")
        results, has_next = await search_music(m.text, 1)
        if not results:
            await m.answer("❌ Topilmadi.")
        else:
            text = f"🎶 **Natijalar (1-bet):**\n\n" + "\n".join([f"{i}. {r['title']}" for i, r in enumerate(results, 1)])
            await m.answer(text, reply_markup=build_music_kb(results, m.text, 1, has_next))
        await st.delete()

# ... (build_music_kb, change_page va dl_music funksiyalari o'zgarishsiz qoladi)

def build_music_kb(results, query, page, has_next):
    kb = InlineKeyboardBuilder()
    for i, r in enumerate(results, 1):
        key = f"dl_{abs(hash(r['url']))}"
        temp_urls[key] = r['url']
        kb.button(text=str(i), callback_data=key)
    kb.adjust(5)
    nav = []
    if page > 1: nav.append(types.InlineKeyboardButton(text="⬅️ Ortga", callback_data=f"page_{query}_{page-1}"))
    if has_next: nav.append(types.InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"page_{query}_{page+1}"))
    if nav: kb.row(*nav)
    return kb.as_markup()

@dp.callback_query(F.data.startswith("page_"))
async def change_page(call: types.CallbackQuery):
    _, query, page = call.data.split("_")
    page = int(page)
    results, has_next = await search_music(query, page)
    if results:
        text = f"🎶 **Natijalar ({page}-bet):**\n\n" + "\n".join([f"{i}. {r['title']}" for i, r in enumerate(results, 1)])
        await call.message.edit_text(text, reply_markup=build_music_kb(results, query, page, has_next))

@dp.callback_query(F.data.startswith("dl_"))
async def dl_music(call: types.CallbackQuery):
    url = temp_urls.get(call.data)
    if not url: return await call.answer("Xatolik, qayta qidiring.")
    msg = await call.message.answer("⏳ Yuklanmoqda...")
    path = await download_task(url, "audio")
    if path:
        await call.message.answer_audio(types.FSInputFile(path))
        os.remove(path)
    await msg.delete()

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
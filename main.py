import os
import asyncio
import yt_dlp
import threading
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

# --- Настройкалар ---
TOKEN = "8260660936:AAH52t9eFso4wNpSOb3Pss9BeJnAL3Pdz1I"
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Хотирада вақтинча сақлаш (Кенгайтирилган)
temp_urls = {}

COMMON_OPTS = {
    'quiet': True,
    'no_warnings': True,
    'nocheckcertificate': True,
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'geo_bypass': True,
}

# Қидирув функцияси (YouTube + SoundCloud комбинацияси)
async def search_music(query, offset=1):
    # scsearch қидируви баъзан Render'да ишламаса, ytsearch ишлатилади
    search_query = f"ytsearch30:{query}" 
    opts = {**COMMON_OPTS, 'extract_flat': True}
    
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = await asyncio.to_thread(ydl.extract_info, search_query, download=False)
            if not info or 'entries' not in info:
                return [], False
            
            entries = [e for e in info['entries'] if e]
            start = (offset - 1) * 10
            end = start + 10
            
            results = []
            for entry in entries[start:end]:
                results.append({
                    'title': entry.get('title', 'Unknown')[:45],
                    'url': entry.get('url') or entry.get('webpage_url')
                })
            return results, len(entries) > end
    except:
        return [], False

# Юклаш функцияси
async def download_task(url, mode="audio"):
    file_id = f"dl_{abs(hash(url))}"
    opts = {**COMMON_OPTS}
    if mode == "video":
        opts.update({'format': 'best', 'outtmpl': f"{file_id}.mp4"})
    else:
        opts.update({
            'format': 'bestaudio/best',
            'outtmpl': f"{file_id}.%(ext)s",
            'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}]
        })
    
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            await asyncio.to_thread(ydl.download, [url])
            ext = "mp4" if mode == "video" else "mp3"
            filename = f"{file_id}.{ext}"
            return filename if os.path.exists(filename) else None
    except:
        return None

# Клавиатура ясаш
def build_music_kb(results, query, page, has_next):
    kb = InlineKeyboardBuilder()
    for i, r in enumerate(results, 1):
        key = f"dl_{abs(hash(r['url']))}"
        temp_urls[key] = r['url'] # Глобал луғатга URLни ёзиш
        kb.button(text=str(i), callback_data=key)
    
    kb.adjust(5)
    nav_btns = []
    if page > 1:
        nav_btns.append(types.InlineKeyboardButton(text="⬅️ Ортга", callback_data=f"page_{query}_{page-1}"))
    if has_next:
        nav_btns.append(types.InlineKeyboardButton(text="Кейинги ➡️", callback_data=f"page_{query}_{page+1}"))
    
    if nav_btns:
        kb.row(*nav_btns)
    return kb.as_markup()

# --- Handlerлар ---

@dp.message(Command("start"))
async def cmd_start(m: types.Message):
    await m.answer("👋 Салом! Мусиқа номини ёзинг ёки Instagram ҳаволасини юборинг:")

@dp.message(F.text)
async def handle_msg(m: types.Message):
    if "instagram.com" in m.text:
        st = await m.answer("⚡️ Инстаграм юкланмоқда...")
        path = await download_task(m.text, "video")
        if path:
            await m.answer_video(types.FSInputFile(path), caption="✅ Тайёр!")
            os.remove(path)
        else:
            await m.answer("❌ Бу видеони юклаб бўлмади (Чеклов бор).")
        await st.delete()
    else:
        st = await m.answer("🔍 Қидирилмоқда...")
        results, has_next = await search_music(m.text, 1)
        if not results:
            await m.answer("❌ Ҳеч нарса топилмади.")
        else:
            text = f"🎶 **Натижалар (Саҳифа: 1):**\n\n"
            for i, r in enumerate(results, 1):
                text += f"{i}. {r['title']}\n"
            await m.answer(text, reply_markup=build_music_kb(results, m.text, 1, has_next))
        await st.delete()

@dp.callback_query(F.data.startswith("page_"))
async def change_page(call: types.CallbackQuery):
    _, query, page = call.data.split("_")
    page = int(page)
    results, has_next = await search_music(query, page)
    
    if results:
        text = f"🎶 **Натижалар (Саҳифа: {page}):**\n\n"
        for i, r in enumerate(results, 1):
            text += f"{i}. {r['title']}\n"
        await call.message.edit_text(text, reply_markup=build_music_kb(results, query, page, has_next))

@dp.callback_query(F.data.startswith("dl_"))
async def dl_music(call: types.CallbackQuery):
    url = temp_urls.get(call.data)
    if not url:
        await call.answer("❌ Хатолик: Қайта қидириб кўринг.", show_alert=True)
        return
    
    msg = await call.message.answer("⏳ Мусиқа юкланмоқда, бироз кутинг...")
    path = await download_task(url, "audio")
    if path:
        await call.message.answer_audio(types.FSInputFile(path))
        os.remove(path)
        await msg.delete()
    else:
        await call.answer("❌ Файлни юклашда хатолик.", show_alert=True)
        await msg.delete()

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
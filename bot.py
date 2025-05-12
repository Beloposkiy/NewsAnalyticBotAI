import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message
from topics import extract_topics


from config import BOT_TOKEN
from rss_reader import get_rss_news
from rss_sources import RSS_SOURCES
from sentiment import analyze_sentiment



bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())

@dp.message(commands=["sentiment"])
async def sentiment_cmd(message: types.Message):
    await message.answer("✉️ Пришли мне новость, и я скажу, какая у неё тональность.")

@dp.message(lambda msg: msg.reply_to_message and msg.text and msg.reply_to_message.text.startswith("📰"))
async def analyze_reply(message: types.Message):
    text = message.reply_to_message.text
    result = analyze_sentiment(text)
    await message.answer(f"🔍 Тональность: {result}")

@dp.message(commands=["topics"])
async def topics_cmd(message: types.Message):
    await message.answer("🔍 Собираю новости и анализирую темы...")

    try:
        # Загружаем новости сразу из нескольких популярных источников
        urls = [
            "https://meduza.io/rss/all",
            "https://tass.ru/rss/v2.xml",
            "https://rssexport.rbc.ru/rbcnews/news/30/full.rss",
        ]

        all_news = []
        for url in urls:
            news_items = get_rss_news(url, limit=10)
            all_news.extend([item.split('\n')[0].replace("📰", "").strip() for item in news_items])

        top_topics = extract_topics(all_news)

        if not top_topics:
            await message.answer("Не удалось выделить темы.")
        else:
            await message.answer("🔥 Главные темы по новостям:\n\n" + "\n\n".join(top_topics), parse_mode="HTML")

    except Exception as e:
        await message.answer(f"⚠️ Ошибка анализа: {e}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
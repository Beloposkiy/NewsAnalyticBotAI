import logging
import warnings
from aiogram import Bot, Dispatcher, F, types
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from init_settings.config import BOT_TOKEN
from bot_commands.topics import extract_topics
from tg.reader import NewsReader
from tg.source import SourceList
from tg.validator import Validator


warnings.filterwarnings("ignore", category=UserWarning, module="torch")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("👋 Привет! Я бот для анализа новостей. Используй /topics или /report для начала.")


@dp.message(Command("sentiment"))
async def sentiment_cmd(message: types.Message):
    await message.answer("✉️ Пришли мне новость, и я скажу, какая у неё тональность. (пока в разработке)")


# bot.py (фрагмент /topics команда)

@dp.message(Command("topics"))
async def topics_cmd(message: types.Message):
    logger.info("✅ Команда /topics получена. Бот начал обработку.")
    msg = await message.answer("🔍 Проверяю Telegram-каналы и анализирую темы за последние сутки...")

    try:
        reader = NewsReader()
        await reader.init()
        logger.info("🤖 Бот подключён к TelegramClient.")

        sources_obj = SourceList()
        telegram_channels = sources_obj.get_telegram_channels()
        logger.info(f"📡 Загружено {len(telegram_channels)} Telegram-каналов для анализа.")

        validator = Validator(reader.client)
        working_tg, _ = await validator.validate_telegram_channels(telegram_channels)

        all_news = []
        for channel in working_tg:
            messages = await reader.telegram_reader(channel, limit=30, days=1)
            logger.info(f"✅ Считано {len(messages)} сообщений из @{channel}")
            all_news.extend(messages)

        if not all_news:
            await msg.edit_text("⚠️ Не удалось загрузить ни одной новости за последние сутки.")
            return

        top_topics = extract_topics(all_news)
        top_topics = top_topics[:10]  # только топ-10

        if not top_topics:
            await msg.edit_text("😕 Темы не были выделены.")
            return

        # Сборка красивого сообщения с эмодзи и карточками ссылок
        final_text = "\n\n".join(top_topics).strip()
        logger.info(f"📨 Итоговый текст:\n{final_text}")

        if not final_text:
            await msg.edit_text("⚠️ Не удалось собрать новости — результат пуст.")
            return

        await msg.edit_text(final_text, parse_mode="HTML", disable_web_page_preview=False)


    except Exception as e:
        logger.exception("Ошибка при анализе Telegram-каналов:")
        await msg.edit_text(f"⚠️ Ошибка: {e}")



@dp.message(Command("report"))
async def report_cmd(message: types.Message):
    await message.answer("📄 Генерация PDF-отчёта в разработке...")


@dp.message(F.text & ~F.text.startswith("/"))
async def debug_log(message: types.Message):
    logger.info(f"💬 Получено сообщение: {message.text}")


async def main():
    logger.info("🚀 Бот запускается...")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await bot.set_my_commands([
            BotCommand(command="start", description="Запустить бота"),
            BotCommand(command="topics", description="Показать главные темы"),
            BotCommand(command="sentiment", description="Проанализировать тональность новости"),
            BotCommand(command="report", description="Создать PDF-отчёт (в разработке)"),
        ])
        logger.info("🤖 Бот запущен и готов к работе!")
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        print("🛑 Бот остановлен пользователем")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

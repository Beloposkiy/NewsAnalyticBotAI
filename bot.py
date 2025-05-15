import logging
import warnings
import re
from pathlib import Path

from aiogram import Bot, Dispatcher, F, types
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, FSInputFile
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from init_settings.config import BOT_TOKEN
from bot_commands.topics import extract_topics
from bot_commands.sentiment import analyze_sentiment
from tg.reader import NewsReader
from tg.source import SourceList
from tg.validator import Validator
from bot_commands.pdf_report import generate_pdf
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from init_settings.config import ADMIN_CHAT_ID

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())
scheduler = AsyncIOScheduler()

async def scheduled_report():
    # Здесь можно указать ID канала или администратора
    chat_id = ADMIN_CHAT_ID

    reader = NewsReader()
    await reader.init()

    sources = SourceList()
    validator = Validator(reader.client)
    working_channels, _ = await validator.validate_telegram_channels(sources.get_telegram_channels())

    all_news = []
    for channel in working_channels:
        messages = await reader.telegram_reader(channel, limit=30, days=1)
        all_news.extend(messages)

    top_topics = extract_topics(all_news)
    if not top_topics:
        await bot.send_message(chat_id, "⚠️ Темы не были найдены.")
        return

    pdf_path = generate_pdf(topics=top_topics)
    await bot.send_document(chat_id, FSInputFile(pdf_path), caption="🗂 Ежедневный PDF-отчёт по темам")
class SentimentStates(StatesGroup):
    waiting_for_text = State()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("👋 Привет! Я бот для анализа новостей. Используй /topics, /sentiment или /report для начала.")

@dp.message(SentimentStates.waiting_for_text)
async def process_sentiment(message: types.Message, state: FSMContext):
    result = "⚠️ Не удалось обработать сообщение."

    if message.forward_from_chat and message.text:
        result = analyze_sentiment(message.text.strip())
    elif message.text and message.text.startswith("http") and "t.me" in message.text:
        from bot_commands.sentiment import analyze_telegram_post
        result = await analyze_telegram_post(message.text.strip())
    elif message.text:
        result = analyze_sentiment(message.text.strip())

    await message.answer(f"📊 Результат анализа:\n{result}")
    await state.clear()

@dp.message(Command("sentiment"))
async def sentiment_cmd(message: types.Message, state: FSMContext):
    await message.answer("✍️ Введите текст, ссылку на статью или прикрепите .txt-файл со ссылками:")
    await state.set_state(SentimentStates.waiting_for_text)

@dp.callback_query(F.data == "generate_pdf_from_topics")
async def callback_generate_pdf(call: types.CallbackQuery):
    await call.answer("⏳ Генерация PDF...")
    text = call.message.text

    # Просто разбиваем темы из сообщения (как они были выведены)
    topics = text.split("\u2063") if "\u2063" in text else text.split("\n\n")

    pdf_path = generate_pdf(topics=topics)
    await call.message.answer_document(FSInputFile(pdf_path), caption="🖨️ PDF-версия тем из /topics")

@dp.message(Command("topics"))
async def topics_cmd(message: types.Message):
    logger.info("✅ Команда /topics получена. Бот начал обработку.")
    msg = await message.answer("🔍 Проверяю Telegram-каналы и анализирую темы за последние сутки...")

    try:
        reader = NewsReader()
        await reader.init()

        sources_obj = SourceList()
        telegram_channels = sources_obj.get_telegram_channels()

        validator = Validator(reader.client)
        working_tg, _ = await validator.validate_telegram_channels(telegram_channels)

        all_news = []
        for channel in working_tg:
            messages = await reader.telegram_reader(channel, limit=30, days=1)
            all_news.extend(messages)

        if not all_news:
            await msg.edit_text("⚠️ Не удалось загрузить ни одной новости за последние сутки.")
            return

        top_topics = extract_topics(all_news)[:10]
        if not top_topics:
            await msg.edit_text("😕 Темы не были выделены.")
            return

        text_lines = []
        for raw in top_topics:
            cleaned = re.sub(r'[^\w\s.,:;!?–—()\"\'«»№@/%\\-]', '', raw)
            lines = cleaned.strip().split("\n")
            if not lines:
                continue
            header = lines[0].lstrip("•").strip()
            header = f"📰 {header}"
            link = next((l.strip() for l in lines if "http" in l or "t.me/" in l), None)
            count_line = next((l.strip() for l in lines if "Упоминаний" in l), None)
            count_str = "0"
            if count_line:
                match = re.search(r"\d+", count_line)
                if match:
                    count_str = match.group(0)
            sentiment = analyze_sentiment("\n".join(lines))
            entry = f"{header}"
            if link:
                entry += f"\n🔗 {link}"
            entry += f"\n🗣️ Упоминаний: {count_str}"
            entry += f"\n🧠 Тональность: {sentiment}"
            entry += "\n⁣"
            text_lines.append(entry.strip())

        final_text = "\n\n".join(text_lines).strip()
        await msg.edit_text(final_text, parse_mode="HTML", disable_web_page_preview=False)

    except Exception as e:
        logger.exception("Ошибка при анализе Telegram-каналов:")
        await msg.edit_text(f"⚠️ Ошибка: {e}")

        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🖨️ Скачать PDF-отчёт", callback_data="generate_pdf_from_topics")]
        ])
        await msg.edit_text(final_text, reply_markup=markup, parse_mode="HTML", disable_web_page_preview=False)


@dp.message(Command("report"))
async def report_cmd(message: types.Message):
    await message.answer("📄 Генерация PDF-отчёта по темам...")

    try:
        reader = NewsReader()
        await reader.init()

        sources = SourceList()
        validator = Validator(reader.client)
        working_channels, _ = await validator.validate_telegram_channels(sources.get_telegram_channels())

        all_news = []
        for channel in working_channels:
            messages = await reader.telegram_reader(channel, limit=30, days=1)
            all_news.extend(messages)

        if not all_news:
            await message.answer("⚠️ Не удалось загрузить ни одной новости.")
            return

        top_topics = extract_topics(all_news)
        if not top_topics:
            await message.answer("😕 Темы не были выделены.")
            return

        pdf_path = generate_pdf(topics=top_topics)
        await message.answer_document(FSInputFile(pdf_path), caption="🗂 Ваш PDF-отчёт готов!")

    except Exception as e:
        logger.exception("Ошибка при генерации отчёта:")
        await message.answer(f"❌ Ошибка при создании отчёта: {e}")

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
            BotCommand(command="sentiment", description="Проанализировать тональность текста/ссылки/файла"),
            BotCommand(command="report", description="Создать PDF-отчёт"),
        ])

        # 📅 Запускаем планировщик
        scheduler.add_job(scheduled_report, trigger="cron", hour=10, minute=0)
        scheduler.start()

        logger.info("🤖 Бот запущен и готов к работе!")
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        print("🛑 Бот остановлен пользователем")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())



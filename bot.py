import logging
from datetime import datetime

from aiogram import Bot, Dispatcher, F, types
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (BotCommand, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bot_commands.classifier import classify_topic
from bot_commands.sentiment import analyze_sentiment
from bot_commands.topics import extract_topics
from bot_commands.utils import generate_pdf
from bot_commands.utils import (
    get_period_label,
    get_category_buttons,
    get_dynamic_period_buttons,
    format_topic_block,
    build_report_filename
)
from init_settings.config import BOT_TOKEN, ADMIN_CHAT_ID
from tg.reader import NewsReader
from tg.source import SourceList
from tg.validator import Validator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())
scheduler = AsyncIOScheduler()


class SentimentStates(StatesGroup):
    waiting_for_text = State()


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("👋 Привет! Я бот для анализа новостей. Используй /topics, /sentiment или /report для начала.")


@dp.message(Command("sentiment"))
async def sentiment_cmd(message: types.Message, state: FSMContext):
    await message.answer("✍️ Введите текст, ссылку на статью или прикрепите .txt-файл со ссылками:")
    await state.set_state(SentimentStates.waiting_for_text)


@dp.message(SentimentStates.waiting_for_text)
async def process_sentiment(message: types.Message, state: FSMContext):
    text = message.text.strip()
    if message.forward_from_chat and text:
        result = analyze_sentiment(text)
    elif text.startswith("http") and "t.me" in text:
        from bot_commands.sentiment import analyze_telegram_post
        result = await analyze_telegram_post(text)
    else:
        result = analyze_sentiment(text)
    await message.answer(f"📊 Результат анализа:\n{result}")
    await state.clear()


@dp.message(Command("topics"))
async def topics_cmd(message: types.Message, state: FSMContext):
    msg = await message.answer("🔍 Анализирую темы за сутки...")

    reader = NewsReader()
    await reader.init()
    sources = SourceList()
    validator = Validator(reader.client)
    working_channels, _ = await validator.validate_telegram_channels(sources.get_telegram_channels())

    all_news = []
    for ch in working_channels:
        all_news.extend(await reader.telegram_reader(ch, days=1))

    top_topics = extract_topics(all_news)
    if not top_topics:
        await msg.edit_text("⚠️ Не удалось найти темы.")
        return

    entries = [format_topic_block(t) for t in top_topics[:5]]
    categories = [classify_topic(t["title"]) for t in top_topics[:5]]

    await state.set_data({
        "all_topics": top_topics[:5],  # Сырой список словарей
        "topic_categories": categories,
        "period_days": 1,
        "current_category": "общие"
    })

    label = get_period_label(1)
    header = f"<b>Отчёт по всем постам за {label}</b>\n\n"
    text = header + "\n\n".join(entries)
    await msg.edit_text(text, parse_mode="HTML", reply_markup=get_category_buttons(current_days=1))

@dp.callback_query(F.data.startswith("filter_category:"))
async def filter_by_category(call: types.CallbackQuery, state: FSMContext):
    category = call.data.split(":")[1]
    data = await state.get_data()
    all_topics = data.get("all_topics", [])
    cats = data.get("topic_categories", [])
    days = data.get("period_days", 1)

    filtered = [t for t, c in zip(all_topics, cats) if c == category]
    await state.update_data(filtered_topics=filtered[:5], current_category=category)

    await call.message.edit_text(
        "\n\n".join(filtered[:5]),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_all")],
            [InlineKeyboardButton(text=f"🕒 Период анализа ({get_period_label(days)})", callback_data="choose_period_category")],
            [InlineKeyboardButton(text="🖨️ PDF этой категории", callback_data="generate_pdf_filtered")]
        ])
    )
    await call.answer()


@dp.callback_query(F.data.in_({"generate_pdf_from_topics", "generate_pdf_filtered"}))
async def callback_generate_pdf(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    topics = data.get("filtered_topics") or data.get("all_topics", [])
    category = data.get("current_category", "all")
    days = data.get("period_days", 1)

    if topics and isinstance(topics[0], str):
        topics = [{
            "title": topics[0],
            "url": "",
            "mentions": 0,
            "created_at": datetime.now().strftime("%d.%m.%Y")
        }]

    filename, title = build_report_filename(category, days)
    pdf_path = generate_pdf(topics=topics, filename=filename, category=category, days=days)
    await call.message.answer_document(FSInputFile(pdf_path), caption=title)
    await call.answer()


@dp.callback_query(F.data.in_({"choose_period", "choose_period_category"}))
async def choose_period_universal(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    days = data.get("period_days", 1)
    is_category = call.data == "choose_period_category"
    back_cb = "back_to_category_buttons" if is_category else "back_to_all"
    keyboard = get_dynamic_period_buttons(current=days, back_cb=back_cb)
    text = "📊 Выберите другой период анализа:" if not is_category else "📊 Выберите другой период анализа для этой категории:"
    await call.message.edit_text(text, reply_markup=keyboard)
    await call.answer()


@dp.callback_query(F.data.startswith("set_period:"))
async def set_period(call: types.CallbackQuery, state: FSMContext):
    days = int(call.data.split(":")[1])
    await state.update_data(period_days=days)

    data = await state.get_data()
    category = data.get("current_category", "общие")

    reader = NewsReader()
    await reader.init()
    sources = SourceList()
    validator = Validator(reader.client)
    working_channels, _ = await validator.validate_telegram_channels(sources.get_telegram_channels())

    all_news = []
    for channel in working_channels:
        all_news.extend(await reader.telegram_reader(channel, days=days))

    top_topics = extract_topics(all_news)
    entries = [format_topic_block(t) for t in top_topics[:5]]
    categories = [classify_topic(t["title"]) for t in top_topics[:5]]

    await state.update_data(
        all_topics=entries,
        topic_categories=categories,
        current_category="общие"
    )

    label = get_period_label(days)
    text = f"🔝 Топ-5 общих новостей за {label}:\n\n" + "\n\n".join(entries)
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=get_category_buttons(current_days=days))
    await call.answer()


@dp.callback_query(F.data == "back_to_all")
async def back_to_all_topics(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    entries = data.get("all_topics", [])
    days = data.get("period_days", 1)
    await call.message.answer("\n\n".join(entries), parse_mode="HTML")
    await call.message.answer("👇 Выберите категорию:", reply_markup=get_category_buttons(current_days=days))
    await call.answer()


@dp.message(Command("report"))
async def report_cmd(message: types.Message, state: FSMContext):
    data = await state.get_data()
    days = data.get("period_days", 1)
    await generate_and_send_report(message.chat.id, days=days)


async def scheduled_report():
    await generate_and_send_report(chat_id=ADMIN_CHAT_ID, days=1)


async def generate_and_send_report(chat_id: int, days: int, category: str = "all", topics: list[dict] = None):
    if not topics:
        reader = NewsReader()
        await reader.init()
        sources = SourceList()
        validator = Validator(reader.client)
        working_channels, _ = await validator.validate_telegram_channels(sources.get_telegram_channels())
        all_news = []
        for channel in working_channels:
            all_news.extend(await reader.telegram_reader(channel, days=days))
        topics = extract_topics(all_news)

    if not topics:
        await bot.send_message(chat_id, "⚠️ Темы не найдены.")
        return

    filename, title = build_report_filename(category, days)
    pdf_path = generate_pdf(topics=topics, filename=filename, category=category, days=days)
    await bot.send_document(chat_id, FSInputFile(pdf_path), caption=title)


async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_my_commands([
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="topics", description="Показать главные темы"),
        BotCommand(command="sentiment", description="Анализ тональности"),
        BotCommand(command="report", description="Создать PDF-отчёт")
    ])
    scheduler.add_job(scheduled_report, trigger="cron", hour=10, minute=0)
    scheduler.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
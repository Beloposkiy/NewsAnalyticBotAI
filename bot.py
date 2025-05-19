from aiogram import Bot, Dispatcher, F, types
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (BotCommand, FSInputFile,
                           InlineKeyboardMarkup, InlineKeyboardButton)
from aiogram.fsm.state import State, StatesGroup
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
import logging

from init_settings.config import BOT_TOKEN, ADMIN_CHAT_ID
from bot_commands.topics import extract_topics
from bot_commands.sentiment import analyze_sentiment
from bot_commands.classifier import classify_topic, CANDIDATE_LABELS, CATEGORY_EN, CATEGORY_PDF_TITLES
from bot_commands.pdf_report import generate_pdf
from tg.reader import NewsReader
from tg.source import SourceList
from tg.validator import Validator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())
scheduler = AsyncIOScheduler()

emoji_map = {
    "политика": "🏛️", "экономика": "💰", "технологии": "💻",
    "культура": "🎝️"
}

class SentimentStates(StatesGroup):
    waiting_for_text = State()

# ---------- Универсальные функции ----------

import re

def strip_emojis(text: str) -> str:
    emoji_pattern = re.compile(
        "["
        u"\U0001F600-\U0001F64F"
        u"\U0001F300-\U0001F5FF"
        u"\U0001F680-\U0001F6FF"
        u"\U0001F1E0-\U0001F1FF"
        u"\u2600-\u26FF"
        u"\u2700-\u27BF"
        "]+", flags=re.UNICODE
    )
    return emoji_pattern.sub(r'', text).strip()

def get_period_label(days: int) -> str:
    return {1: "день", 7: "неделя", 30: "месяц"}.get(days, f"{days} дней")

def get_category_buttons(current_days: int = 1):
    period_label = get_period_label(current_days)
    buttons = [
        InlineKeyboardButton(
            text=f"{emoji_map.get(label.lower(), '🗂️')} {label.capitalize()}",
            callback_data=f"filter_category:{label.lower()}"
        ) for label in CANDIDATE_LABELS
    ]
    rows = [buttons[i:i+2] for i in range(0, len(buttons), 2)]
    rows.append([InlineKeyboardButton(text=f"🕒 Период анализа ({period_label})", callback_data="choose_period")])
    rows.append([InlineKeyboardButton(text="🖨️ Скачать PDF-отчёт", callback_data="generate_pdf_from_topics")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def get_period_buttons(back_cb: str = "back_to_all", pdf_cb: str = "generate_pdf_from_topics"):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🕐 За день", callback_data="set_period:1"),
         InlineKeyboardButton(text="📅 За неделю", callback_data="set_period:7")],
        [InlineKeyboardButton(text="📆 За месяц", callback_data="set_period:30")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data=back_cb)],
        [InlineKeyboardButton(text="🖨️ Создать PDF-отчёт", callback_data=pdf_cb)]
    ])

def format_topic_block(raw: str) -> str:
    lines = [line.strip() for line in raw.split("\n") if line.strip()]
    if not lines:
        return ""

    # Очистка заголовка от эмодзи
    raw_header = lines[0].lstrip("•").strip()
    header = f"📰 {strip_emojis(raw_header)}"

    link = next((l for l in lines if "http" in l), "")
    count = next((l for l in lines if "Упоминаний" in l), "")

    # Формируем текст для анализа тональности
    sentiment_input = "\n".join([
        line for line in lines
        if all(x not in line.lower() for x in ["http", "тональность", "упоминаний", "🔗", "➡", "🧠"])
    ])

    sentiment = analyze_sentiment(sentiment_input)

    result = header
    if link:
        result += f"\n{link}"
    if count:
        result += f"\n{count}"
    if sentiment:
        result += f"\n🧠 Тональность: {sentiment}"

    return result

def build_report_filename(category: str, days: int):
    date_str = datetime.now().strftime("%d.%m.%Y")
    cat_en = CATEGORY_EN.get(category, "all")
    title_ru = CATEGORY_PDF_TITLES.get(category, "всем постам")
    period_map = {1: "день", 7: "неделю", 30: "месяц"}
    period = period_map.get(days, f"{days} дней")
    filename = f"news_{cat_en}_{date_str}_report.pdf"
    title = f"Отчёт по {title_ru} за {period}"
    return filename, title

async def generate_and_send_report(chat_id: int, days: int, category: str = "all", topics: list[str] = None):
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
        await bot.send_message(chat_id, "⚠️ Не найдено новостей.")
        return

    filename, title = build_report_filename(category, days)
    path = generate_pdf(topics=topics, filename=filename)
    await bot.send_document(chat_id, FSInputFile(path), caption=title)

# ---------- Команды ----------

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
    entries = [format_topic_block(t) for t in top_topics[:6]]
    await state.set_data({
        "all_topics": entries,
        "topic_categories": [classify_topic(t) for t in entries],
        "period_days": 1,
        "current_category": "общие"
    })
    await msg.delete()
    await message.answer("\n\n".join(entries), parse_mode="HTML")
    await message.answer("👇 Выберите категорию:", reply_markup=get_category_buttons(current_days=1))

@dp.callback_query(F.data.startswith("filter_category:"))
async def filter_by_category(call: types.CallbackQuery, state: FSMContext):
    category = call.data.split(":")[1]
    data = await state.get_data()
    all_topics = data.get("all_topics", [])
    cats = data.get("topic_categories", [])
    days = data.get("period_days", 1)
    filtered = [t for t, c in zip(all_topics, cats) if c == category]
    await state.update_data(filtered_topics=filtered[:5], current_category=category)
    await call.message.answer(
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
    filename, title = build_report_filename(category, days)
    pdf_path = generate_pdf(topics=topics, filename=filename)
    await call.message.answer_document(FSInputFile(pdf_path), caption=title)
    await call.answer()

@dp.callback_query(F.data == "choose_period")
async def choose_period_main(call: types.CallbackQuery):
    await call.message.answer("📊 Период анализа:", reply_markup=get_period_buttons())
    await call.answer()

@dp.callback_query(F.data == "choose_period_category")
async def choose_period_cat(call: types.CallbackQuery):
    await call.message.answer("📊 Период для категории:", reply_markup=get_period_buttons("back_to_category_buttons", "generate_pdf_filtered"))
    await call.answer()

@dp.callback_query(F.data == "back_to_category_buttons")
async def back_to_cat_view(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    filtered = data.get("filtered_topics", [])
    period_days = data.get("period_days", 1)
    await call.message.answer(
        "\n\n".join(filtered[:5]),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_all")],
            [InlineKeyboardButton(text=f"🕒 Период анализа ({get_period_label(period_days)})", callback_data="choose_period_category")],
            [InlineKeyboardButton(text="🖨️ PDF этой категории", callback_data="generate_pdf_filtered")]
        ])
    )
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

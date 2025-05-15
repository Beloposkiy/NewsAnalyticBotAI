import logging
import warnings
import re
from collections import defaultdict

from aiogram import Bot, Dispatcher, F, types
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from init_settings.config import BOT_TOKEN, ADMIN_CHAT_ID
from bot_commands.topics import extract_topics
from bot_commands.sentiment import analyze_sentiment
from bot_commands.classifier import classify_topic
from tg.reader import NewsReader
from tg.source import SourceList
from tg.validator import Validator
from bot_commands.pdf_report import generate_pdf
from bot_commands.classifier import CANDIDATE_LABELS

warnings.filterwarnings("ignore", category=FutureWarning, module="huggingface_hub.file_download")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())
scheduler = AsyncIOScheduler()

class SentimentStates(StatesGroup):
    waiting_for_text = State()

async def scheduled_report():
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

@dp.callback_query(F.data.startswith("select_topic:"))
async def callback_show_full_topic(call: types.CallbackQuery):
    topic_index = int(call.data.split(":")[1])
    user_data = call.message.text.split("\n\n")
    if topic_index < len(user_data):
        await call.message.answer(f"📄 Полный текст темы:\n\n{user_data[topic_index].strip()}")
    await call.answer()

@dp.callback_query(F.data.in_({"generate_pdf_from_topics", "generate_pdf_filtered"}))
async def callback_generate_pdf(call: types.CallbackQuery, state: FSMContext):
    logger.info(f"📁 Кнопка PDF нажата: {call.data}")
    await call.answer("⏳ Генерация PDF...")

    data = await state.get_data()
    topics = data.get("filtered_topics") or data.get("all_topics", [])
    category = data.get("current_category", "all")

    if not topics:
        await call.message.answer("⚠️ Нет доступных тем для отчёта.")
        return

    from datetime import datetime
    date_str = datetime.now().strftime("%d.%m.%Y")
    filename = f"news_{category}_{date_str}_report.pdf"

    pdf_path = generate_pdf(topics=topics, filename=filename)
    await call.message.answer_document(FSInputFile(pdf_path), caption=f"📄 PDF-отчёт по темам «{category.capitalize()}»")

@dp.message(Command("topics"))
async def topics_cmd(message: types.Message, state: FSMContext):
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

        top_topics = sorted(extract_topics(all_news), key=lambda t: int(re.search(r"Упоминаний: (\d+)", t).group(1)) if re.search(r"Упоминаний: (\d+)", t) else 0, reverse=True)[:6]
        if not top_topics:
            await msg.edit_text("😕 Темы не были выделены.")
            return

        grouped = defaultdict(list)
        raw_entries = []
        topic_categories = []
        emoji_map = {
            "политика": "🏛️",
            "экономика": "💰",
            "технологии": "💻",
            "культура": "🎭",
            "прочее": "🗂️"
        }

        for raw in top_topics:
            cleaned = re.sub(r'[^\w\s.,:;!?–—()\"\'«»№@/%\\-]', '', raw)
            lines = cleaned.strip().split("\n")
            if not lines:
                continue
            header_text = lines[0].lstrip("•").strip()
            category = classify_topic(header_text).lower()
            topic_categories.append(category)
            header = f"📰 {header_text}"
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
            entry += "\n\u2063"
            grouped[category].append(entry.strip())
            raw_entries.append(entry.strip())

        full_text = "\n\n".join(raw_entries).strip()

        # создаём кнопки по списку лейблов
        topic_buttons = []
        for label in CANDIDATE_LABELS:
            emoji = emoji_map.get(label.lower(), "🗂️")
            topic_buttons.append(
                InlineKeyboardButton(text=f"{emoji} {label.capitalize()}",
                                     callback_data=f"filter_category:{label.lower()}")
            )

        inline_rows = [topic_buttons[i:i + 2] for i in range(0, len(topic_buttons), 2)]
        inline_rows.append([
            InlineKeyboardButton(text="🖨️ Скачать PDF-отчёт", callback_data="generate_pdf_from_topics")
        ])
        markup = InlineKeyboardMarkup(inline_keyboard=inline_rows)

        await state.set_data({
            "all_topics": raw_entries,
            "topic_categories": [classify_topic(re.search(r'📰 (.+)', t).group(1)) for t in raw_entries]
        })

        await msg.delete()
        await message.answer(full_text, parse_mode="HTML", disable_web_page_preview=True)
        await message.answer("👇 Выберите категорию для фильтрации:", reply_markup=markup)

    except Exception as e:
        logger.exception("Ошибка при анализе Telegram-каналов:")
        await msg.edit_text(f"⚠️ Ошибка: {e}")

@dp.callback_query(F.data.startswith("filter_category:"))
async def filter_by_category(call: types.CallbackQuery, state: FSMContext):
    cat = call.data.split(":")[1]
    logger.info(f"📂 Пользователь выбрал категорию: {cat}")
    data = await state.get_data()
    all_topics = data.get("all_topics", [])
    categories = data.get("topic_categories", [])

    filtered = [t for t, c in zip(all_topics, categories) if c.lower() == cat.lower()]

    if not filtered:
        await call.message.answer(f"⚠️ Нет тем в категории «{cat.capitalize()}».")
        return

    preview = "\n\n".join(filtered[:5])
    # Сохраняем выбранную категорию и отфильтрованные топики
    await state.update_data(filtered_topics=filtered[:5], current_category=cat)

    # Показываем 5 новостей и 2 кнопки
    await call.message.answer(
        f"📂 Топ-5 новостей категории «{cat.capitalize()}»:\n\n{preview}",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_all")],
            [InlineKeyboardButton(text="🖨️ PDF этой категории", callback_data="generate_pdf_filtered")]
        ])
    )
    await call.answer()


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

@dp.callback_query(F.data == "back_to_all")
async def back_to_all(call: types.CallbackQuery, state: FSMContext):
    logger.info("🔙 Пользователь вернулся к списку всех тем")
    data = await state.get_data()
    topics = data.get("all_topics", [])

    if not topics:
        await call.message.answer("⚠️ Темы не найдены.")
        return

    full_text = "\n\n".join(topics).strip()

    from bot_commands.classifier import CANDIDATE_LABELS
    emoji_map = {
        "политика": "🏛️", "экономика": "💰", "технологии": "💻",
        "культура": "🎭", "прочее": "🗂️"
    }

    topic_buttons = []
    for label in CANDIDATE_LABELS:
        emoji = emoji_map.get(label.lower(), "🗂️")
        topic_buttons.append(
            InlineKeyboardButton(text=f"{emoji} {label.capitalize()}", callback_data=f"filter_category:{label.lower()}")
        )

    rows = [topic_buttons[i:i+2] for i in range(0, len(topic_buttons), 2)]
    rows.append([InlineKeyboardButton(text="🖨️ Скачать PDF-отчёт", callback_data="generate_pdf_from_topics")])
    markup = InlineKeyboardMarkup(inline_keyboard=rows)

    await call.message.answer(full_text, parse_mode="HTML", disable_web_page_preview=True)
    await call.message.answer("👇 Выберите категорию для фильтрации:", reply_markup=markup)
    await call.answer()


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
        scheduler.add_job(scheduled_report, trigger="cron", hour=10, minute=0)
        scheduler.start()
        logger.info("🤖 Бот запущен и готов к работе!")
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        print("🛑 Бот остановлен пользователем")
    finally:
        scheduler.shutdown(wait=False)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

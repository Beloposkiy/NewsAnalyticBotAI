from aiogram.types import FSInputFile
from transformers import pipeline

from shared import bot
from bot_commands.pdf_report import generate_pdf
from bot_commands.topics import extract_topics
from init_settings.config import ADMIN_CHAT_ID
from tg.reader import NewsReader
from tg.source import SourceList
from tg.validator import Validator

# Инициализация zero-shot классификатора
classifier = pipeline("zero-shot-classification", model="MoritzLaurer/deberta-v3-base-zeroshot-v1")

CANDIDATE_LABELS = [
    "политика",
    "экономика",
    "технологии",
    "культура",
]

CATEGORY_EN = {
    "политика": "politics",
    "экономика": "economy",
    "технологии": "technology",
    "культура": "culture",
    "общие": "all"
}

CATEGORY_PDF_TITLES = {
    "политика": "политическим постам",
    "экономика": "экономическим постам",
    "технологии": "технологическим постам",
    "культура": "культурным постам",
    "общие": "всем постам"
}


def classify_topic(text: str) -> str:
    result = classifier(text, CANDIDATE_LABELS, multi_label=False)
    return result["labels"][0]


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

import os
import types
from datetime import datetime, timezone, timedelta

import dp
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from telethon import TelegramClient
from telethon.errors import UsernameInvalidError, UsernameNotOccupiedError, ChannelPrivateError
from telethon.tl.functions.messages import GetHistoryRequest

from bot import SentimentStates, generate_and_send_report, logger
from bot_commands.sentiment import analyze_sentiment, run_model
from bot_commands.topics import extract_topics
from bot_commands.utils import log_user_action, get_category_buttons, format_topic_block
from init_settings.config import api_id, api_hash
from tg.reader import NewsReader
from tg.source import SourceList
from tg.validator import Validator


import re
import logging
import torch
import numpy as np
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from telethon import TelegramClient
from telethon.errors import MessageIdInvalidError
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from init_settings.config import BOT_TOKEN, api_id, api_hash, session_path

# --- Логирование ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s]: %(message)s",
    handlers=[
        logging.FileHandler("newsbot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- Инициализация бота ---
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# --- Состояния FSM ---
class SentimentStates(StatesGroup):
    waiting_for_text = State()

# --- Модели тональности ---
base_model_name = "blanchefort/rubert-base-cased-sentiment"
base_tokenizer = AutoTokenizer.from_pretrained(base_model_name)
base_model = AutoModelForSequenceClassification.from_pretrained(base_model_name)
labels = ['negative', 'neutral', 'positive']

fallback_model_name = "cointegrated/rubert-tiny-sentiment-balanced"
fallback_tokenizer = AutoTokenizer.from_pretrained(fallback_model_name)
fallback_model = AutoModelForSequenceClassification.from_pretrained(fallback_model_name)

NEGATIVE_KEYWORDS = [
    "провал", "разочарование", "санкци", "не будет", "отказ",
    "авария", "снизился", "бактерии", "заражён", "кишечная палочка",
    "инфекция", "отравление"
]

# --- Функция анализа с моделью ---
def run_model(text: str, tokenizer, model) -> tuple[str, float]:
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
    with torch.no_grad():
        logits = model(**inputs).logits
    probs = torch.nn.functional.softmax(logits, dim=-1).squeeze().numpy()
    top = int(np.argmax(probs))
    return labels[top], probs[top]

# --- Анализ тональности с эвристиками ---
def analyze_sentiment(text: str) -> str:
    try:
        text_lower = text.lower()
        # Ручная эвристика
        if any(word in text_lower for word in NEGATIVE_KEYWORDS):
            return "😠 Негативная (по ключевым словам)"

        label, score = run_model(text, base_tokenizer, base_model)
        if score < 0.75:
            label, score = run_model(text, fallback_tokenizer, fallback_model)

        if label == "neutral" and any(word in text_lower for word in NEGATIVE_KEYWORDS):
            label = "negative"

        if label == "positive":
            return f"😊 Позитивная ({score:.2f})"
        elif label == "neutral":
            return f"😐 Нейтральная ({score:.2f})"
        elif label == "negative":
            return f"😠 Негативная ({score:.2f})"
        else:
            return "🤷 Не удалось определить"
    except Exception as e:
        logger.error(f"Ошибка анализа тональности: {e}")
        return "⚠️ Ошибка анализа тональности"

# --- Извлечение полного текста из Telegram-поста ---
async def extract_text_from_telegram(url: str) -> str:
    match = re.match(r"https?://t\.me/(\w+)/(\d+)", url)
    if not match:
        return "⚠️ Неверная ссылка на Telegram-пост."

    channel_username, msg_id = match.groups()
    msg_id = int(msg_id)

    try:
        async with TelegramClient(session_path, api_id, api_hash) as client:
            message = await client.get_messages(channel_username, ids=msg_id)
            if not message:
                return "[⛔ Сообщение не найдено]"
            parts = [
                message.text or "",
                getattr(message, "message", ""),
                getattr(message, "caption", ""),
            ]
            combined = "\n".join(set(filter(None, map(str.strip, parts))))
            logger.info(f"[Текст Telegram-поста]: {combined}")
            return combined if combined else "[Пост пуст или недоступен]"
    except MessageIdInvalidError:
        return "[⛔ Сообщение не найдено]"
    except Exception as e:
        logger.warning(f"[Ошибка доступа к Telegram]: {e}")
        return f"[⚠️ Ошибка доступа к Telegram: {e}]"

# --- Обёртка для анализа поста по ссылке ---
async def analyze_telegram_post(url: str) -> str:
    text = await extract_text_from_telegram(url)
    if text.startswith("[") or text.startswith("⚠️"):
        return text
    return analyze_sentiment(text)

# --- Хендлер команды /sentiment ---
@dp.message(Command("sentiment"))
async def sentiment_cmd(message: types.Message, state: FSMContext):
    log_user_action(message.from_user.id, message.from_user.username, message.from_user.full_name, "Команда /sentiment")
    await message.answer("✍️ Введите текст, ссылку на статью или прикрепите .txt-файл со ссылками:")
    await state.set_state(SentimentStates.waiting_for_text)

# --- Хендлер обработки текста или ссылки ---
@dp.message(SentimentStates.waiting_for_text)
async def process_sentiment(message: types.Message, state: FSMContext):
    text = message.text.strip()

    log_user_action(
        user_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
        action="Анализ тональности текста"
    )

    if message.forward_from_chat and text:
        result = analyze_sentiment(text)
    elif text.startswith("http") and "t.me" in text:
        result = await analyze_telegram_post(text)
    else:
        result = analyze_sentiment(text)

    await message.answer(f"📊 Результат анализа:\n{result}")
    await state.clear()



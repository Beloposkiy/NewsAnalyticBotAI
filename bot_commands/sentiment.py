import re
import torch
import numpy as np
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from telethon import TelegramClient
from telethon.errors import MessageIdInvalidError
from init_settings.config import api_id, api_hash, session_path

# === Основная модель: Blanchefort (точнее, но тяжелее) ===
base_model_name = "blanchefort/rubert-base-cased-sentiment"
base_tokenizer = AutoTokenizer.from_pretrained(base_model_name)
base_model = AutoModelForSequenceClassification.from_pretrained(base_model_name)
labels = ['negative', 'neutral', 'positive']

# === Резервная модель: Cointegrated (лёгкая) ===
fallback_model_name = "cointegrated/rubert-tiny-sentiment-balanced"
fallback_tokenizer = AutoTokenizer.from_pretrained(fallback_model_name)
fallback_model = AutoModelForSequenceClassification.from_pretrained(fallback_model_name)

# === Ключевые слова для ручной коррекции ===
NEGATIVE_KEYWORDS = ["провал", "разочарование", "санкци", "не будет", "отказ", "авария", "снизился"]

# === Анализ с основной моделью ===
def run_model(text: str, tokenizer, model) -> tuple[str, float]:
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
    with torch.no_grad():
        logits = model(**inputs).logits
    probs = torch.nn.functional.softmax(logits, dim=-1).squeeze().numpy()
    top = int(np.argmax(probs))
    return labels[top], probs[top]

# === Главная функция анализа ===
def analyze_sentiment(text: str) -> str:
    try:
        label, score = run_model(text, base_tokenizer, base_model)

        # Если уверенность низкая — подключаем fallback-модель
        if score < 0.75:
            label, score = run_model(text, fallback_tokenizer, fallback_model)

        # Ручная коррекция: если слово негативное, а метка нейтральная
        lowered = text.lower()
        if label == "neutral" and any(word in lowered for word in NEGATIVE_KEYWORDS):
            label = "negative"

        if label == "positive":
            return f"😊 Позитивная ({score:.2f})"
        elif label == "neutral":
            return f"😐 Нейтральная ({score:.2f})"
        elif label == "negative":
            return f"😠 Негативная ({score:.2f})"
        else:
            return f"🤷 Не удалось определить"
    except Exception as e:
        return f"⚠️ Ошибка анализа: {e}"

# === Асинхронное извлечение текста из Telegram-поста ===
async def extract_text_from_telegram(url: str) -> str:
    match = re.match(r"https?://t\.me/([\w\d_]+)/([0-9]+)", url)
    if not match:
        return "⚠️ Неверная ссылка на Telegram-пост."

    channel_username, msg_id = match.groups()
    msg_id = int(msg_id)

    try:
        async with TelegramClient(session_path, api_id, api_hash) as client:
            message = await client.get_messages(channel_username, ids=msg_id)
            return message.text.strip() if message and message.text else "[Пост пуст или недоступен]"
    except MessageIdInvalidError:
        return "[⛔ Сообщение не найдено]"
    except Exception as e:
        return f"[⚠️ Ошибка доступа к Telegram: {e}]"

# === Обёртка для анализа по ссылке ===
async def analyze_telegram_post(url: str) -> str:
    text = await extract_text_from_telegram(url)
    if text.startswith("[") or text.startswith("⚠️"):
        return text
    return analyze_sentiment(text)

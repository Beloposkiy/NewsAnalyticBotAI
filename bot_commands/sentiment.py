import re
import torch
import numpy as np
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from telethon import TelegramClient
from telethon.errors import MessageIdInvalidError
from init_settings.config import api_id, api_hash

# ✅ Используем ту же сессию, что и reader.py
SESSION_PATH = "sessions/news_monitoring"

# === Инициализация модели ===
model_name = "cointegrated/rubert-tiny-sentiment-balanced"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSequenceClassification.from_pretrained(model_name)
labels = ['negative', 'neutral', 'positive']

# === Основной анализ тональности текста ===
def analyze_sentiment(text: str) -> str:
    try:
        inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
        with torch.no_grad():
            logits = model(**inputs).logits
        probs = torch.nn.functional.softmax(logits, dim=-1).squeeze().numpy()

        top = int(np.argmax(probs))
        score = probs[top]
        label = labels[top]

        lowered = text.lower()
        if label == "neutral" and score > 0.85 and any(word in lowered for word in ["провал", "разочарование"]):
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
    match = re.match(r"https?://t\.me/([\w\d_]+)/(\d+)", url)
    if not match:
        return "⚠️ Неверная ссылка на Telegram-пост."

    channel_username, msg_id = match.groups()
    msg_id = int(msg_id)

    try:
        async with TelegramClient(SESSION_PATH, api_id, api_hash) as client:
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

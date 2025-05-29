import re
import unicodedata
import torch
import numpy as np
import logging
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from telethon import TelegramClient
from telethon.errors import MessageIdInvalidError
from init_settings.config import api_id, api_hash, session_path

logger = logging.getLogger(__name__)

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

def clean_and_trim(text: str, max_length: int = 200) -> str:
    # Удаление emoji
    emoji_pattern = re.compile(
        "[" +
        u"\U0001F600-\U0001F64F" +
        u"\U0001F300-\U0001F5FF" +
        u"\U0001F680-\U0001F6FF" +
        u"\U0001F1E0-\U0001F1FF" +
        u"\u2600-\u26FF" +
        u"\u2700-\u27BF" +
        "]+", flags=re.UNICODE
    )
    text = emoji_pattern.sub('', text)

    # Удаление символа замены и управляющих символов
    text = text.replace('\uFFFD', '')  # символ �
    text = ''.join(c for c in text if unicodedata.category(c)[0] != 'C')

    return text.strip()[:max_length]

def run_model(text: str, tokenizer, model) -> tuple[str, float]:
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
    with torch.no_grad():
        logits = model(**inputs).logits
    probs = torch.nn.functional.softmax(logits, dim=-1).squeeze().numpy()
    top = int(np.argmax(probs))
    return labels[top], probs[top]

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

            parts = []
            for attr in ('message', 'caption', 'text', 'raw_text'):
                val = getattr(message, attr, None)
                if val and isinstance(val, str) and val.strip():
                    parts.append(val.strip())

            # Удаляем дубликаты и объединяем
            seen = set()
            unique_parts = []
            for part in parts:
                if part not in seen:
                    unique_parts.append(part)
                    seen.add(part)

            combined_text = "\n\n".join(unique_parts)
            logger.info(f"[Извлечённый текст Telegram-поста]: {combined_text}")
            return combined_text if combined_text else "[Пост пуст или содержит только медиа]"

    except MessageIdInvalidError:
        return "[⛔ Сообщение не найдено]"
    except Exception as e:
        logger.warning(f"[Ошибка доступа к Telegram]: {e}")
        return f"[⚠️ Ошибка доступа к Telegram: {e}]"

async def analyze_telegram_post(url: str) -> str:
    full_text = await extract_text_from_telegram(url)
    cleaned_text = clean_and_trim(full_text)
    logger.info(f"[Очищенный текст для анализа]: {cleaned_text}")
    if cleaned_text.startswith("[") or cleaned_text.startswith("⚠️"):
        return cleaned_text
    return analyze_sentiment(cleaned_text)

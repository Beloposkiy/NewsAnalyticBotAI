import warnings
from transformers import pipeline, logging as transformers_logging
from config.logger import logger

warnings.filterwarnings("ignore")
transformers_logging.set_verbosity_error()

sentiment_classifier = None

def load_models():
    global sentiment_classifier

    base_dir = "./local_models"

    try:
        sentiment_classifier = pipeline(
            "sentiment-analysis",
            model=f"{base_dir}/sentiment_classifier",
            device=-1
        )
        logger.info("Классификатор тональности загружен (blanchefort rubert-base-cased-sentiment-rusentiment)")
    except Exception as e:
        logger.error(f"Ошибка загрузки тонального классификатора: {e}")

def analyze_sentiment(text: str) -> tuple:
    if sentiment_classifier is None:
        logger.warning("Классификатор тональности не инициализирован")
        return ("neutral", 0.0)

    try:
        truncated_text = text[:512]  # Обрезаем текст, чтобы избежать ошибок
        res = sentiment_classifier(truncated_text)[0]
        return res['label'], res['score']
    except Exception as e:
        logger.error(f"Ошибка при анализе тональности: {e}")
        return ("neutral", 0.0)

# Загружаем модель при импорте модуля
load_models()
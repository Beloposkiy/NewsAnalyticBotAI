import warnings
from transformers import pipeline, logging as transformers_logging
from config.logger import logger

warnings.filterwarnings("ignore")
transformers_logging.set_verbosity_error()

sentiment_classifier_1 = None
sentiment_classifier_2 = None

def load_models():
    global sentiment_classifier_1, sentiment_classifier_2

    try:
        sentiment_classifier_1 = pipeline(
            "sentiment-analysis",
            model="sismetanin/rubert-ru-sentiment-rusentiment",
            device=-1
        )
        logger.info("Классификатор тональности 1 загружен (sismetanin rubert-ru-sentiment-rusentiment)")
    except Exception as e:
        logger.error(f"Ошибка загрузки тонального классификатора 1: {e}")

    try:
        sentiment_classifier_2 = pipeline(
            "sentiment-analysis",
            model="seara/rubert-tiny2-russian-sentiment",
            device=-1
        )
        logger.info("Классификатор тональности 2 загружен (seara rubert-tiny2-russian-sentiment)")
    except Exception as e:
        logger.error(f"Ошибка загрузки тонального классификатора 2: {e}")

def merge_sentiment_results(res1, res2):
    return (res1['label'], res1['score']) if res1['score'] >= res2['score'] else (res2['label'], res2['score'])

def analyze_sentiment(text: str) -> tuple:
    if sentiment_classifier_1 is None or sentiment_classifier_2 is None:
        logger.warning("Классификаторы тональности не инициализированы")
        return ("neutral", 0.0)

    try:
        truncated_text = text[:512]  # Обрезаем текст, чтобы избежать ошибок
        res1 = sentiment_classifier_1(truncated_text)[0]
        res2 = sentiment_classifier_2(truncated_text)[0]
        label, score = merge_sentiment_results(res1, res2)
        return label, score
    except Exception as e:
        logger.error(f"Ошибка при анализе тональности: {e}")
        return ("neutral", 0.0)

# Загружаем модели один раз при импорте
load_models()
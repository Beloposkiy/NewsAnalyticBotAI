import warnings
from transformers import pipeline, logging as transformers_logging
from config.logger import logger, print_progress_bar

warnings.filterwarnings("ignore")
transformers_logging.set_verbosity_error()

CATEGORIES = [
    "politics", "economics", "society", "tech",
    "military", "sports", "science", "culture", "incident"
]

category_classifier_1 = None
category_classifier_2 = None

def load_models():
    global category_classifier_1, category_classifier_2

    try:
        category_classifier_1 = pipeline(
            "zero-shot-classification",
            model="cointegrated/rubert-tiny2-cedr-emotion-detection",
            device=-1
        )
        logger.info("Категорийный классификатор 1 загружен (cointegrated rubert-tiny2-cedr-emotion-detection)")
    except Exception as e:
        logger.error(f"Ошибка загрузки классификатора 1: {e}")

    try:
        category_classifier_2 = pipeline(
            "zero-shot-classification",
            model="apanc/russian-sensitive-topics",
            device=-1
        )
        logger.info("Категорийный классификатор 2 загружен (apanc russian-sensitive-topics)")
    except Exception as e:
        logger.error(f"Ошибка загрузки классификатора 2: {e}")

def merge_category_results(results1, results2, threshold=0.35):
    cats1 = [cat for cat, score in zip(results1['labels'], results1['scores']) if score > threshold]
    cats2 = [cat for cat, score in zip(results2['labels'], results2['scores']) if score > threshold]
    merged = list(set(cats1 + cats2))
    return merged or ["other"]

def classify_post(text: str, threshold: float = 0.35) -> list:
    if category_classifier_1 is None or category_classifier_2 is None:
        logger.warning("Категорийные классификаторы не инициализированы")
        return ["other"]

    try:
        truncated_text = text[:512]  # обрезаем для предотвращения ошибок
        res1 = category_classifier_1(truncated_text, candidate_labels=CATEGORIES, multi_label=True)
        res2 = category_classifier_2(truncated_text, candidate_labels=CATEGORIES, multi_label=True)
        cats = merge_category_results(res1, res2, threshold=threshold)
        return cats or ["other"]
    except Exception as e:
        logger.error(f"Ошибка при классификации поста: {e}")
        return ["other"]

def classify_and_analyze(news_list):
    total = len(news_list)
    results = []
    for i, news in enumerate(news_list, 1):
        text = news.get('text', '')
        categories = classify_post(text)
        results.append({
            "text": text,
            "categories": categories,
            "created_at": news.get('created_at'),
            "url": news.get('url'),
            "channel": news.get('channel'),
        })
        print_progress_bar(i, total)
    print()  # перевод строки после прогресс-бара
    return results

# Загружаем модели при импорте модуля
load_models()
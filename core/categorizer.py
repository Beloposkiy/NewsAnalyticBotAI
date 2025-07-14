import warnings
from transformers import pipeline, logging as transformers_logging
from config.logger import logger, print_progress_bar
from collections import Counter
from pathlib import Path
import json
import threading
from datetime import datetime

from shared.constants import CATEGORY_KEYWORDS, CATEGORIES  # импортируем словарь и категории

warnings.filterwarnings("ignore")
transformers_logging.set_verbosity_error()

category_classifier = None
MEMORY_DIR = Path(__file__).parent.parent / "category_memory"
MEMORY_DIR.mkdir(parents=True, exist_ok=True)
LOCK = threading.Lock()

def load_models():
    global category_classifier
    try:
        model_path = Path(__file__).parent.parent / "local_models" / "category_classifier"
        category_classifier = pipeline(
            "zero-shot-classification",
            model=str(model_path),
            device=-1
        )
        logger.info("Категорийный классификатор загружен (DeepPavlov/rubert-base-cased)")
    except Exception as e:
        logger.error(f"Ошибка загрузки классификатора: {e}")

def contains_keywords(text: str, keywords: list) -> bool:
    text_lower = text.lower()
    return any(keyword.lower() in text_lower for keyword in keywords)

def save_to_memory(post: dict, assigned_categories: list):
    try:
        with LOCK:
            post_copy = post.copy()
            for key, value in post_copy.items():
                if isinstance(value, datetime):
                    post_copy[key] = value.isoformat()

            for category in assigned_categories:
                category_dir = MEMORY_DIR / category
                category_dir.mkdir(exist_ok=True)
                filename = category_dir / f"{hash(post_copy.get('text',''))}.json"
                if not filename.exists():
                    with open(filename, "w", encoding="utf-8") as f:
                        json.dump(post_copy, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка при сохранении поста в память: {e}")

def classify_post(text: str, post: dict = None, threshold: float = 0.6, max_categories: int = 2):
    if category_classifier is None:
        logger.warning("Категорийный классификатор не инициализирован")
        return ["other"]

    text_lower = text.lower()

    matched_categories = []
    # Поиск категорий по ключевым словам
    for category in CATEGORIES:
        keywords = CATEGORY_KEYWORDS.get(category, [])
        if contains_keywords(text_lower, keywords):
            matched_categories.append(category)
        if len(matched_categories) == max_categories:
            break

    if len(matched_categories) < max_categories:
        # Если категорий меньше max_categories, дополняем классификатором
        try:
            truncated_text = text[:512]
            res = category_classifier(truncated_text, candidate_labels=CATEGORIES, multi_label=True)
            labels_scores = list(zip(res['labels'], res['scores']))
            # Отфильтровать категории, уже найденные по ключевым словам
            labels_scores = [ls for ls in labels_scores if ls[0] not in matched_categories]
            # Отсортировать по уверенности
            labels_scores_sorted = sorted(labels_scores, key=lambda x: x[1], reverse=True)
            # Добавить из классификатора до max_categories
            for cat, score in labels_scores_sorted:
                if score >= threshold:
                    matched_categories.append(cat)
                if len(matched_categories) == max_categories:
                    break
        except Exception as e:
            logger.error(f"Ошибка при классификации поста: {e}")

    if not matched_categories and post:
        save_to_memory(post, ["other"])
        return ["other"]

    if post:
        save_to_memory(post, matched_categories)

    return matched_categories

def classify_and_analyze(news_list, threshold=0.6, max_categories=2):
    total = len(news_list)
    results = []
    category_counts = Counter()

    for i, news in enumerate(news_list, 1):
        text = news.get('text', '')
        categories = classify_post(text, post=news, threshold=threshold, max_categories=max_categories)
        results.append({
            "text": text,
            "categories": categories,
            "created_at": news.get('created_at'),
            "url": news.get('url'),
            "channel": news.get('channel'),
        })
        for cat in categories:
            category_counts[cat] += 1

        print_progress_bar(i, total)

    GREEN = "\033[92m"
    RESET = "\033[0m"
    log_lines = [f"{cat}: {count} пост(ов)" for cat, count in category_counts.items()]
    if log_lines:
        logger.info(f"{GREEN}Количество постов по категориям:\n" + "\n".join(log_lines) + f"{RESET}")
    else:
        logger.info(f"{GREEN}Постов не найдено ни в одной категории.{RESET}")

    return results

# Загружаем модель при импорте
load_models()
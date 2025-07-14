from transformers import pipeline
from config.logger import logger

models = {
    "category_classifier_1": "cointegrated/rubert-tiny2-cedr-emotion-detection",
    "category_classifier": "apanc/russian-sensitive-topics",
    "sentiment_classifier": "sismetanin/rubert-ru-sentiment-rusentiment",
    "sentiment_classifier_2": "seara/rubert-tiny2-russian-sentiment",
}

if __name__ == "__main__":
    for name, model_name in models.items():
        try:
            task = "zero-shot-classification" if "category" in name else "sentiment-analysis"
            logger.info(f"Загружаем модель {name}: {model_name}")
            _ = pipeline(task, model=model_name)
            logger.info(f"Модель {name} успешно загружена и сохранена в кэш")
        except Exception as e:
            logger.error(f"Ошибка при загрузке модели {name} ({model_name}): {e}")
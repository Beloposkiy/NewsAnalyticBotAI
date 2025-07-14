from transformers import AutoModelForSequenceClassification, AutoTokenizer
from pathlib import Path
from config.logger import logger

models = {
    "category_classifier": "DeepPavlov/rubert-base-cased",
    "sentiment_classifier": "blanchefort/rubert-base-cased-sentiment-rusentiment",
}

LOCAL_MODELS_DIR = Path("./local_models")
LOCAL_MODELS_DIR.mkdir(exist_ok=True)  # Создаёт папку local_models, если её нет

def download_and_save_models():
    for name, model_name in models.items():
        model_dir = LOCAL_MODELS_DIR / name
        try:
            logger.info(f"Скачиваю модель {name} ({model_name}) в {model_dir} ...")
            model_dir.mkdir(parents=True, exist_ok=True)  # Создаём директорию модели, если нет
            model = AutoModelForSequenceClassification.from_pretrained(model_name)
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            model.save_pretrained(model_dir)
            tokenizer.save_pretrained(model_dir)
            logger.info(f"Модель {name} успешно сохранена в {model_dir}")
        except Exception as e:
            logger.error(f"Ошибка при скачивании или сохранении модели {name}: {e}")

if __name__ == "__main__":
    download_and_save_models()
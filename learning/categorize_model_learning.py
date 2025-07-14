import logging
from datetime import datetime
from pathlib import Path
import json
import shutil
from transformers import AutoModelForSequenceClassification, AutoTokenizer, Trainer, TrainingArguments
from datasets import Dataset

# ANSI escape codes для цветов
BLUE = "\033[94m"
WHITE = "\033[97m"
GREEN = "\033[92m"
RESET = "\033[0m"

# Настройка логгера с белым цветом по умолчанию
class ColorfulFormatter(logging.Formatter):
    def format(self, record):
        message = super().format(record)
        # Перекрашиваем все логи в белый цвет
        return f"{WHITE}{message}{RESET}"

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger("model_training")

# Заменяем форматтер для основного обработчика
for handler in logger.handlers:
    handler.setFormatter(ColorfulFormatter(handler.formatter._fmt))

CATEGORIES = [
    "politics", "economics", "society", "tech",
    "military", "sports", "science", "culture", "incident"
]

MEMORY_DIR = Path(__file__).parent.parent / "category_memory"
MODEL_SAVE_DIR = Path(__file__).parent.parent / "local_models" / "category_classifier"

def load_training_data():
    records = []
    for category_dir in MEMORY_DIR.iterdir():
        if category_dir.is_dir() and category_dir.name in CATEGORIES:
            for json_file in category_dir.glob("*.json"):
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    text = data.get("text", "")
                    label_idx = CATEGORIES.index(category_dir.name)
                    records.append({"text": text, "label": label_idx})
                except Exception as e:
                    logger.error(f"Ошибка при чтении файла {json_file}: {e}")

    if not records:
        logger.warning("Нет данных для обучения")
        return None

    return Dataset.from_list(records)

def tokenize_function(examples, tokenizer):
    return tokenizer(examples["text"], truncation=True, padding="max_length", max_length=512)

def clear_training_data():
    try:
        if MEMORY_DIR.exists() and MEMORY_DIR.is_dir():
            shutil.rmtree(MEMORY_DIR)
            MEMORY_DIR.mkdir(parents=True, exist_ok=True)
            logger.info(f"{GREEN}Папка {MEMORY_DIR} успешно очищена после обучения.{RESET}")
    except Exception as e:
        logger.error(f"Ошибка при очистке папки с обучающими данными: {e}")

def main():
    print(f"{BLUE}[{datetime.now().strftime('%H:%M:%S')}] Старт дообучения классификатора категорий...{RESET}")

    dataset = load_training_data()
    if dataset is None:
        logger.error("Данные для обучения не найдены. Завершение.")
        return

    tokenizer = AutoTokenizer.from_pretrained(str(MODEL_SAVE_DIR))

    tokenized_dataset = dataset.map(lambda examples: tokenize_function(examples, tokenizer), batched=True)

    model = AutoModelForSequenceClassification.from_pretrained(
        str(MODEL_SAVE_DIR),
        num_labels=len(CATEGORIES),
        ignore_mismatched_sizes=True
    )

    training_args = TrainingArguments(
        output_dir=str(MODEL_SAVE_DIR),
        num_train_epochs=3,
        per_device_train_batch_size=8,
        save_steps=100,
        save_total_limit=2,
        logging_dir="./logs",
        logging_steps=50,
        load_best_model_at_end=False,
        report_to=[]
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_dataset,
        tokenizer=tokenizer
    )

    trainer.train()

    logger.info(f"Сохраняем дообученную модель в {MODEL_SAVE_DIR} ...")
    print(f"{BLUE}[{datetime.now().strftime('%H:%M:%S')}] Сохраняем дообученную модель в {MODEL_SAVE_DIR} ...{RESET}")
    model.save_pretrained(MODEL_SAVE_DIR)
    tokenizer.save_pretrained(MODEL_SAVE_DIR)

    print(f"{BLUE}[{datetime.now().strftime('%H:%M:%S')}] Дообучение завершено.{RESET}")

    # Очищаем папку с обучающими данными после успешного дообучения
    clear_training_data()

if __name__ == "__main__":
    main()
import logging
import warnings
from pathlib import Path
import json
from transformers import AutoModelForSequenceClassification, AutoTokenizer, Trainer, TrainingArguments, TrainerCallback
from datasets import Dataset
from datetime import datetime
import torch

# Подавляем warnings
warnings.filterwarnings("ignore")
logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("torch").setLevel(logging.ERROR)

# Цвета ANSI
BLUE = "\033[94m"
WHITE = "\033[97m"
RESET = "\033[0m"

# Логгер с белым цветом по умолчанию
class WhiteFormatter(logging.Formatter):
    def format(self, record):
        message = super().format(record)
        return f"{WHITE}{message}{RESET}"

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("model_training")
for handler in logger.handlers:
    handler.setFormatter(WhiteFormatter(handler.formatter._fmt))

CATEGORIES = [
    "politics", "economics", "society", "tech",
    "military", "sports", "science", "culture", "incident"
]

SENTIMENT_LABELS = ["POSITIVE", "NEUTRAL", "NEGATIVE"]

DATASET_FILE = Path(__file__).parent.parent / "dataset" / "generated_dataset_10000.json"
CATEGORY_MODEL_DIR = Path(__file__).parent.parent / "local_models" / "category_classifier"
SENTIMENT_MODEL_DIR = Path(__file__).parent.parent / "local_models" / "sentiment_classifier"

def load_dataset():
    records = []
    try:
        with open(DATASET_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            for item in data:
                text = item.get("text", "")
                category = item.get("category", "").lower()
                sentiment = item.get("sentiment", "").upper()

                if category in CATEGORIES and sentiment in SENTIMENT_LABELS:
                    records.append({
                        "text": text,
                        "category_label": CATEGORIES.index(category),
                        "sentiment_label": SENTIMENT_LABELS.index(sentiment)
                    })
    except Exception as e:
        logger.error(f"Ошибка при чтении файла {DATASET_FILE}: {e}")
        return None

    if not records:
        logger.warning("Нет данных для обучения")
        return None

    return Dataset.from_list(records)

def prepare_dataset_for_label(dataset: Dataset, label_field: str):
    return dataset.rename_column(label_field, "labels")

def tokenize_function(examples, tokenizer):
    return tokenizer(examples["text"], truncation=True, padding="max_length", max_length=512)

def print_progress_bar(current: int, total: int, bar_length=30):
    progress = current / total
    filled_len = int(bar_length * progress)
    bar = "█" * filled_len + "-" * (bar_length - filled_len)
    print(f"\rПрогресс: |{bar}| {current}/{total}", end="")
    if current == total:
        print()  # Перевод строки

class ProgressCallback(TrainerCallback):
    def __init__(self, total_posts=10000):
        self.total_posts = total_posts
        self.current = 0

    def on_step_end(self, args, state, control, **kwargs):
        # Прибавляем к прогрессу количество обработанных постов (приблизительно)
        self.current = min(state.global_step * args.per_device_train_batch_size, self.total_posts)

        bar_length = 30
        filled_len = int(bar_length * self.current / self.total_posts)
        bar = "█" * filled_len + "-" * (bar_length - filled_len)

        print(f"\rПрогресс: |{bar}| {self.current}/{self.total_posts}", end="")

        if self.current >= self.total_posts:
            print()  # Перевод строки при окончании

def train_model(model_dir: Path, dataset: Dataset, label_field: str, num_labels: int, log_prefix: str):
    dataset_for_train = prepare_dataset_for_label(dataset, label_field)

    tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
    tokenized_dataset = dataset_for_train.map(lambda examples: tokenize_function(examples, tokenizer), batched=True)

    model = AutoModelForSequenceClassification.from_pretrained(
        str(model_dir),
        num_labels=num_labels,
        ignore_mismatched_sizes=True
    )

    device = "mps" if torch.backends.mps.is_available() else "cpu"

    training_args = TrainingArguments(
        output_dir=str(model_dir),
        num_train_epochs=2,
        per_device_train_batch_size=2,
        save_steps=100,
        save_total_limit=1,
        logging_dir=f"./logs/{log_prefix}",
        logging_steps=1000,
        load_best_model_at_end=False,
        report_to=[],
        no_cuda=True
    )

    print(f"{BLUE}[{datetime.now().strftime('%H:%M:%S')}] Начинается дообучение {log_prefix}...{RESET}")
    trainer = Trainer(
        model=model.to(device),
        args=training_args,
        train_dataset=tokenized_dataset,
        tokenizer=tokenizer,
        callbacks=[ProgressCallback(total_posts=10000)],
    )
    trainer.train()
    print(f"{BLUE}[{datetime.now().strftime('%H:%M:%S')}] Дообучение {log_prefix} завершено.{RESET}")

    logger.info(f"{log_prefix} сохранена в {model_dir}")
    model.save_pretrained(model_dir)
    tokenizer.save_pretrained(model_dir)

def main():
    dataset = load_dataset()
    if dataset is None:
        logger.error("Данные для обучения не найдены. Завершение.")
        return

    train_model(CATEGORY_MODEL_DIR, dataset, "category_label", len(CATEGORIES), "Категорийный классификатор")
    train_model(SENTIMENT_MODEL_DIR, dataset, "sentiment_label", len(SENTIMENT_LABELS), "Классификатор тональности")

if __name__ == "__main__":
    main()
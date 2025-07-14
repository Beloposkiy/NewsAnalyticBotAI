import logging
from pathlib import Path
import json
from transformers import AutoModelForSequenceClassification, AutoTokenizer, Trainer, TrainingArguments
from datasets import Dataset

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sentiment_training")

# Категории тональности — 3 класса (позитив, нейтрально, негатив)
SENTIMENT_LABELS = ["POSITIVE", "NEUTRAL", "NEGATIVE"]

# Путь к папке с JSON файлами для обучения
TRAIN_DATA_DIR = Path(__file__).parent.parent / "sentiment_memory"

# Путь для сохранения локальной модели после обучения
MODEL_SAVE_DIR = Path(__file__).parent.parent / "local_models" / "sentiment_classifier"

def load_training_data():
    records = []
    for json_file in TRAIN_DATA_DIR.glob("*.json"):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            text = data.get("text", "")
            label_str = data.get("label", "").upper()
            if label_str in SENTIMENT_LABELS:
                label_idx = SENTIMENT_LABELS.index(label_str)
                records.append({"text": text, "label": label_idx})
        except Exception as e:
            logger.error(f"Ошибка чтения файла {json_file}: {e}")

    if not records:
        logger.warning("Нет данных для обучения")
        return None

    return Dataset.from_list(records)

def tokenize_function(examples, tokenizer):
    return tokenizer(examples["text"], truncation=True, padding="max_length", max_length=512)

def main():
    logger.info("Старт дообучения классификатора тональности...")

    dataset = load_training_data()
    if dataset is None:
        logger.error("Данные для обучения не найдены. Завершение.")
        return

    tokenizer = AutoTokenizer.from_pretrained(str(MODEL_SAVE_DIR))

    tokenized_dataset = dataset.map(lambda examples: tokenize_function(examples, tokenizer), batched=True)

    model = AutoModelForSequenceClassification.from_pretrained(
        str(MODEL_SAVE_DIR),
        num_labels=len(SENTIMENT_LABELS),
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
        load_best_model_at_end=True,
        evaluation_strategy="steps",
        eval_steps=100,
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
    model.save_pretrained(MODEL_SAVE_DIR)
    tokenizer.save_pretrained(MODEL_SAVE_DIR)

    logger.info("Дообучение завершено.")

if __name__ == "__main__":
    main()
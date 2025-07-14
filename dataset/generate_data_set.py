import random
import json
from pathlib import Path
from shared.constants import CATEGORY_KEYWORDS, CATEGORIES

def generate_post(category: str, min_sentences=5, min_words=40) -> dict:
    """
    Генерируем один пост для заданной категории, с использованием ключевых слов.
    Текст будет из min_sentences предложений минимум, с минимум min_words слов.
    """
    keywords = CATEGORY_KEYWORDS.get(category, [])
    if not keywords:
        keywords = ["текст", "новость", "информация"]  # запасные слова

    sentences = []
    word_count = 0
    while len(sentences) < min_sentences or word_count < min_words:
        sentence_length = random.randint(8, 15)
        sentence_words = []

        kw_in_sentence = random.sample(keywords, min(len(keywords), random.randint(2,3)))
        filler_words = ["это", "важно", "сегодня", "эксперт", "обсуждение", "новость", "аналитика", "данные", "информация", "проект", "ситуация"]
        filler_count = sentence_length - len(kw_in_sentence)

        sentence_words.extend(kw_in_sentence)
        sentence_words.extend(random.choices(filler_words, k=filler_count))
        random.shuffle(sentence_words)
        sentence = " ".join(sentence_words).capitalize() + "."
        sentences.append(sentence)
        word_count += len(sentence_words)

    text = " ".join(sentences)
    sentiment = random.choice(["POSITIVE", "NEGATIVE", "NEUTRAL"])

    post = {
        "text": text,
        "category": category,
        "sentiment": sentiment
    }
    return post

def generate_dataset(total_posts=10000):
    posts_per_category = total_posts // len(CATEGORIES)
    dataset = []
    for category in CATEGORIES:
        for _ in range(posts_per_category):
            post = generate_post(category)
            dataset.append(post)
    return dataset

if __name__ == "__main__":
    data_dir = Path("dataset")
    data_dir.mkdir(exist_ok=True)

    data = generate_dataset(10000)

    file_path = data_dir / "generated_dataset_10000.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Генерация датасета завершена, файл сохранён как {file_path}")
from bertopic import BERTopic

# Инициализация модели
topic_model = BERTopic(language="multilingual", min_topic_size=2, verbose=True)

def extract_topics(texts_with_links: list[dict], top_n=5):
    if not texts_with_links:
        print("❌ Нет входных данных для анализа.")
        return []

    # Заголовки новостей
    texts = [item["title"] for item in texts_with_links]
    print(f"📥 Получено {len(texts)} текстов для анализа.")

    # Тематическое моделирование
    topics, _ = topic_model.fit_transform(texts)

    # Информация о выделенных темах
    topic_info = topic_model.get_topic_info()
    print("📊 Информация о темах:")
    print(topic_info)

    # Можно отключить фильтр, если нужно увидеть все темы, включая -1
    filtered = topic_info.head(top_n)
    print("🔎 Отфильтрованные темы:")
    print(filtered)

    # Репрезентативные документы
    topic_representatives = topic_model.get_representative_docs()

    results = []
    for _, row in filtered.iterrows():
        topic_id = row["Topic"]
        try:
            example_text = topic_representatives[topic_id][0].strip()
        except (IndexError, KeyError):
            example_text = "(нет примера)"
        else:
            example_text = example_text[0].upper() + example_text[1:]

        # Поиск ссылки
        link = next(
            (item["url"] for item in texts_with_links
             if item["title"].strip() in example_text or example_text in item["title"].strip()),
            None
        )

        entry = f"• {example_text}"
        if link:
            entry += f"\n➡ {link}"
        entry += f"\n— Упоминаний: {row['Count']}"
        results.append(entry)

    print(f"✅ Темы, готовые к отображению: {len(results)}")
    return results



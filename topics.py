from bertopic import BERTopic

# Создание объекта модели (один раз на запуск)
topic_model = BERTopic(language="multilingual", calculate_probabilities=True)


def extract_topics(texts, top_n=5):
    """
    Принимает список новостных текстов, возвращает top_n ключевых тем
    """
    if not texts:
        return []

    topics, _ = topic_model.fit_transform(texts)
    topic_info = topic_model.get_topic_info()

    # Пропускаем -1 (мусор)
    filtered_topics = topic_info[topic_info.Topic != -1].head(top_n)

    result = []
    for _, row in filtered_topics.iterrows():
        result.append(f"🧠 <b>{row['Name']}</b>\nУпоминаний: {row['Count']}")
    return result
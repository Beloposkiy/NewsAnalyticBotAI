from bertopic import BERTopic
from datetime import datetime

topic_model = BERTopic(language="multilingual", min_topic_size=2, verbose=True)

def extract_topics(texts_with_links: list[dict], top_n=5):
    if not texts_with_links:
        print("❌ Нет входных данных для анализа.")
        return []

    texts = [item["title"] for item in texts_with_links]
    print(f"📥 Получено {len(texts)} текстов для анализа.")

    topics, _ = topic_model.fit_transform(texts)
    topic_info = topic_model.get_topic_info()
    filtered = topic_info[topic_info.Topic != -1].sort_values("Count", ascending=False)
    topic_representatives = topic_model.get_representative_docs()

    results = []

    for _, row in filtered.iterrows():
        topic_id = row["Topic"]
        try:
            example_text = topic_representatives[topic_id][0].strip()
        except (IndexError, KeyError):
            continue

        example_text_norm = example_text.lower()

        matched_item = next(
            (item for item in texts_with_links
             if item["title"].lower().strip() in example_text_norm
             or example_text_norm in item["title"].lower().strip()),
            None
        )

        if not matched_item:
            continue

        url = matched_item.get("url", "")
        created_at_dt = matched_item.get("created_at")

        if isinstance(created_at_dt, datetime):
            created_at_str = created_at_dt.strftime("%d.%m.%Y")
        elif isinstance(created_at_dt, str):
            created_at_str = created_at_dt
        else:
            created_at_str = ""

        results.append({
            "title": example_text,
            "url": url,
            "mentions": int(row["Count"]),
            "created_at": created_at_str
        })

        if len(results) >= top_n:
            break

    print(f"✅ Темы, готовые к отображению: {len(results)}")
    return results
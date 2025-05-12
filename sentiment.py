from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline

model_path = "models/rubert-sentiment"  # локальный путь

tokenizer = AutoTokenizer.from_pretrained(model_path)
model = AutoModelForSequenceClassification.from_pretrained(model_path)
sentiment_pipeline = pipeline("sentiment-analysis", model=model, tokenizer=tokenizer)

def analyze_sentiment(text: str) -> str:
    try:
        result = sentiment_pipeline(text[:512])[0]
        label = result["label"]
        score = result["score"]
        if label == "NEGATIVE":
            return f"😠 Негативная ({score:.2f})"
        elif label == "NEUTRAL":
            return f"😐 Нейтральная ({score:.2f})"
        elif label == "POSITIVE":
            return f"😊 Позитивная ({score:.2f})"
        else:
            return f"🤷 Не удалось определить (label={label})"
    except Exception as e:
        return f"⚠️ Ошибка анализа: {e}"
from transformers import pipeline

# Инициализация zero-shot классификатора
classifier = pipeline("zero-shot-classification", model="MoritzLaurer/deberta-v3-base-zeroshot-v1")

CANDIDATE_LABELS = [
    "политика",
    "экономика",
    "технологии",
    "культура",
    "прочее"
]

def classify_topic(text: str) -> str:
    result = classifier(text, CANDIDATE_LABELS, multi_label=False)
    return result["labels"][0]

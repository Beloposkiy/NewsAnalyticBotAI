import os
import re
from datetime import datetime
from weasyprint import HTML
from shared.constants import CATEGORY_LABELS
from config.logger import logger  # импортируем логгер


def clean_text(text: str) -> str:
    """
    Универсальная очистка текста:
    - удаляет эмодзи,
    - удаляет нежелательные специальные символы (кроме кавычек и основных знаков препинания),
    - удаляет звездочки,
    - сохраняет буквы, цифры, пробелы, знаки препинания, кавычки.

    Возвращает очищенный текст.
    """
    # Удаляем эмодзи и спецсимволы Unicode из определённых диапазонов
    emoji_pattern = re.compile(
        "[" 
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags
        "\u2600-\u26FF\u2700-\u27BF"  # misc symbols
        "]", flags=re.UNICODE)
    text = emoji_pattern.sub("", text)

    # Удаляем все символы, кроме букв (латиница и кириллица), цифр, пробелов, знаков препинания и кавычек
    # Разрешаем: . , ! ? « » “ ” " ' - и пробелы
    text = re.sub(r"[^a-zA-Zа-яА-Я0-9\s.,!?«»“”\"'\-]", "", text)

    # Удаляем все звездочки (одинарные и множественные)
    text = re.sub(r"\*+", "", text)

    # Обрезаем пробелы в начале и конце
    return text.strip()


def extract_first_paragraph(text: str) -> str:
    """Возвращает первый непустой абзац из очищенного текста."""
    paragraphs = text.split('\n')
    for p in paragraphs:
        p_clean = clean_text(p.strip())
        if p_clean:
            return p_clean
    return clean_text(text.strip())


def build_html_report(news: list, period: str, category: str) -> str:
    """
    Генерирует HTML-отчёт по новостям.
    :param news: Список новостей (dict с 'text', 'created_at', 'url', 'sentiment').
    :param period: 'day', 'week', 'month'
    :param category: ключ категории
    :return: Путь к HTML-файлу.
    """
    if not os.path.exists("reports"):
        os.makedirs("reports")
        logger.info("Создана папка reports для отчетов")

    SENTIMENT_LABELS = {
        "POSITIVE": "Позитивная",
        "NEGATIVE": "Негативная",
        "NEUTRAL": "Нейтральная",
        "LABEL_0": "Позитивная",
        "LABEL_1": "Нейтральная",
        "LABEL_2": "Негативная",
    }

    category_title = CATEGORY_LABELS.get(category, category)
    items = ""
    for n in news:
        try:
            dt = n.get('created_at')
            if isinstance(dt, datetime):
                dt_str = dt.strftime('%d.%m.%Y %H:%M')
            elif isinstance(dt, str):
                dt_str = dt
            else:
                dt_str = "Дата неизвестна"
        except Exception:
            dt_str = "Дата неизвестна"

        url = n.get('url') or "Ссылка отсутствует"
        sentiment_raw = n.get('sentiment', 'неизвестна').upper()
        sentiment_str = SENTIMENT_LABELS.get(sentiment_raw, n.get('sentiment', 'неизвестна'))

        text_raw = n.get('text', '')
        text_clean = clean_text(text_raw).replace('\n', '<br>')

        items += (
            f"<div style='margin-bottom:20px; border-bottom:1px solid #eee; padding-bottom:10px;'>"
            f"<b>{dt_str}</b><br>"
            f"{text_clean}<br>"
            f"— <a href='{url}'>{url}</a><br>"
            f"— Тональность: {sentiment_str}"
            f"</div>"
        )

    html = f"""
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        body {{ font-family: Arial, 'DejaVu Sans', sans-serif; font-size: 15px; margin: 2em; }}
        h2 {{ margin-bottom: 1em; }}
        a {{ color: blue; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
      </style>
    </head>
    <body>
      <h2>Отчёт по категории {category_title} за {period}</h2>
      {items}
    </body>
    </html>
    """

    filename_html = f"reports/posts_{datetime.now():%Y_%m_%d}_report.html"
    with open(filename_html, "w", encoding="utf-8") as f:
        f.write(html)
    logger.info(f"HTML отчет сохранён: {filename_html}")
    return filename_html


def build_pdf_report(news: list, period: str, category: str) -> str:
    """
    Генерирует PDF-отчёт по новостям через HTML + WeasyPrint.
    :param news: Список новостей.
    :param period: 'day', 'week', 'month'
    :param category: ключ категории
    :return: Путь к PDF-файлу.
    """
    try:
        html_path = build_html_report(news, period, category)
        pdf_path = html_path.replace(".html", ".pdf")
        HTML(html_path).write_pdf(pdf_path)
        logger.info(f"PDF отчет сформирован: {pdf_path}")
        return pdf_path
    except Exception as e:
        logger.error(f"Ошибка при формировании PDF отчёта: {e}")
        raise
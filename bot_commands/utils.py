import os
import pdfkit

from datetime import datetime

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot_commands.constants import CANDIDATE_LABELS, CATEGORY_PDF_TITLES, CATEGORY_EN

emoji_map = {
    "политика": "🏛️",
    "экономика": "💰",
    "технологии": "💻",
    "культура": "🎭"
}

def get_period_label(days: int) -> str:
    return {1: "день", 7: "неделю", 30: "месяц"}.get(days, f"{days} дней")

def get_category_buttons(current_days: int = 1):
    period_label = get_period_label(current_days)
    buttons = [
        InlineKeyboardButton(
            text=f"{emoji_map.get(label.lower(), '🗂️')} {label.capitalize()}",
            callback_data=f"filter_category:{label.lower()}"
        ) for label in CANDIDATE_LABELS
    ]
    rows = [buttons[i:i+2] for i in range(0, len(buttons), 2)]
    rows.append([InlineKeyboardButton(text=f"🕒 Период анализа ({period_label})", callback_data="choose_period")])
    rows.append([InlineKeyboardButton(text="🖨️ Скачать PDF-отчёт", callback_data="generate_pdf_from_topics")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def get_dynamic_period_buttons(current: int, back_cb: str):
    available = {1: ("7", "30"), 7: ("1", "30"), 30: ("1", "7")}.get(current, ("1", "7"))
    label_map = {"1": "🕐 За день", "7": "📅 За неделю", "30": "📆 За месяц"}
    buttons = [InlineKeyboardButton(text=label_map[d], callback_data=f"set_period:{d}") for d in available]
    return InlineKeyboardMarkup(inline_keyboard=[
        buttons,
        [InlineKeyboardButton(text="🔙 Назад", callback_data=back_cb)]
    ])

def strip_emojis(text: str) -> str:
    emoji_pattern = re.compile(
        "["
        u"\U0001F600-\U0001F64F"
        u"\U0001F300-\U0001F5FF"
        u"\U0001F680-\U0001F6FF"
        u"\U0001F1E0-\U0001F1FF"
        u"\u2600-\u26FF"
        u"\u2700-\u27BF"
        "]+", flags=re.UNICODE
    )
    return emoji_pattern.sub(r'', text).strip()


from bot_commands.sentiment import analyze_sentiment
import re


def format_topic_block(topic: dict, for_pdf: bool = False) -> str:
    title = topic.get("title", "").strip()
    url = topic.get("url", "")
    mentions = topic.get("mentions", 0)
    created_at = topic.get("created_at", "")
    sentiment = analyze_sentiment(title)

    if for_pdf:
        return (
            f"Дата публикации: {created_at}\n"
            f"{title}\n"
            f"→ {url}\n"
            f"- Упоминаний: {mentions}\n"
            f"- Тональность: {sentiment}"
        )
    else:
        return (
            f"📅 <b>Дата публикации:</b> {created_at}\n"
            f"📰 {title}\n"
            f"🔗 {url}\n"
            f"🗣️ Упоминаний: {mentions}\n"
            f"🧠 Тональность: {sentiment}"
        )

def build_report_filename(category: str, days: int):
    date_str = datetime.now().strftime("%d.%m.%Y")
    cat_en = CATEGORY_EN.get(category, "all")
    title_ru = CATEGORY_PDF_TITLES.get(category, "всем постам")
    period_map = {1: "день", 7: "неделю", 30: "месяц"}
    period = period_map.get(days, f"{days} дней")
    filename = f"news_{cat_en}_{date_str}_report.pdf"
    title = f"Отчёт по {title_ru} за {period}"
    return filename, title

def generate_pdf(topics: list[dict], filename: str = None,
                 category: str = "all", days: int = 1) -> str:
    now = datetime.now()
    formatted_date = now.strftime("%d.%m.%Y")
    timestamp = now.strftime("%d.%m.%Y %H:%M")

    if not filename:
        filename = f"news_{formatted_date}_report.pdf"

    output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "reports"))
    os.makedirs(output_dir, exist_ok=True)
    html_path = os.path.join(output_dir, f"news_{formatted_date}_report.html")
    pdf_path = os.path.join(output_dir, filename)

    # Заголовок
    cat_title = CATEGORY_PDF_TITLES.get(category, "")
    period_label = get_period_label(days)
    base = f"Отчёт по {cat_title} за {period_label}" if cat_title else f"Отчёт по всем постам за {period_label}"

    html_content = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <title>{base}</title>
        <style>
            body {{ font-family: sans-serif; font-size: 14px; }}
            .topic {{ margin-bottom: 20px; }}
            .title {{ font-size: 15px; margin-bottom: 5px; }}
        </style>
    </head>
    <body>
        <h2>{base}</h2>
        <p>Сформировано: {timestamp}</p>
        <hr>
    """

    for topic in topics:
        title_line = topic.get("title", "").strip()
        url = topic.get("url", "").strip()
        mentions = topic.get("mentions", 0)
        created_at = topic.get("created_at", "")

        sentiment = analyze_sentiment(title_line)
        sentiment_clean = re.sub(r"^[^A-Za-zА-Яа-яЁё]+", "", sentiment)

        html_content += f"""
        <div class="topic">
            <p>Дата публикации: {created_at}</p>
            <p class="title">{title_line}</p>
            <p>→ {url}<br>
            - Упоминаний: {mentions}<br>
            - Тональность: {sentiment_clean}</p>
        </div>
        <hr>
        """

    html_content += "</body></html>"

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    options = {
        "encoding": "UTF-8",
        "quiet": "",
        "enable-local-file-access": "",
        "margin-top": "10mm",
        "margin-bottom": "10mm",
        "margin-left": "15mm",
        "margin-right": "15mm",
    }

    config = pdfkit.configuration(wkhtmltopdf="/usr/local/bin/wkhtmltopdf")
    pdfkit.from_file(html_path, pdf_path, options=options, configuration=config)

    return pdf_path

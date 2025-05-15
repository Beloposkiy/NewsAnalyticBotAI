import os
import re
import pdfkit
from datetime import datetime
from bot_commands.sentiment import analyze_sentiment

def generate_pdf(topics: list[str], filename: str = None) -> str:
    now = datetime.now()
    formatted_date = now.strftime("%d.%m.%Y")
    timestamp = now.strftime("%d.%m.%Y %H:%M")

    if not filename:
        filename = f"news_{formatted_date}_report.pdf"

    output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "reports"))
    os.makedirs(output_dir, exist_ok=True)
    html_path = os.path.join(output_dir, f"temp_{formatted_date}.html")
    pdf_path = os.path.join(output_dir, filename)

    html_content = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <title>Отчёт по новостям</title>
        <style>
            body {{ font-family: sans-serif; font-size: 14px; }}
            .topic {{ margin-bottom: 20px; }}
        </style>
    </head>
    <body>
        <h2>Отчёт по ключевым темам</h2>
        <p>Сформировано: {timestamp}</p>
        <hr>
    """

    for topic in topics:
        lines = topic.replace("\\n", "\n").split("\n")
        lines = [line.strip() for line in lines if line.strip()]
        if not lines:
            continue

        title = re.sub(r"[^\w\s.,:;!?–—()\"\'«»№@/%\\-]", "", lines[0]).strip()
        title = f"• {title}"

        link = next((l for l in lines if "http" in l or "t.me/" in l), "").strip()

        count_line = next((l for l in lines if "Упоминаний" in l), "")
        count_match = re.search(r"\d+", count_line)
        count = count_match.group(0) if count_match else "0"
        mentions = f"— Упоминаний: {count}"

        sentiment = analyze_sentiment("\n".join(lines))
        sentiment_clean = re.sub(r"^[^A-Za-zА-Яа-яЁё]+", "", sentiment)  # удалить смайлик в начале
        tone_line = f"— Тональность: {sentiment_clean}"

        html_content += f"""
        <div class="topic">
            <p>{title}<br>
            {link}<br>
            {mentions}<br>
            {tone_line}</p>
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

    pdfkit.from_file(html_path, pdf_path, options=options)
    return pdf_path

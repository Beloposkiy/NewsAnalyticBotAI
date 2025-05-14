import os
from datetime import datetime  # ✅ используем только нужный класс

def generate_html(topics: list[str], filename: str = None) -> str:
    now = datetime.now()
    formatted_date = now.strftime("%d.%m.%Y")
    timestamp = now.strftime("%d.%m.%Y %H:%M")

    if not filename:
        filename = f"news_{formatted_date}_report.html"

    output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "reports"))
    os.makedirs(output_dir, exist_ok=True)

    file_path = os.path.join(output_dir, filename)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write("<html><head><meta charset='utf-8'><title>Отчёт по новостям</title></head><body>")
        f.write(f"<h2>Отчёт по ключевым темам</h2>")
        f.write(f"<p>Сформировано: {timestamp}</p><hr>")

        for topic in topics:
            block = topic.replace("<b>", "<strong>").replace("</b>", "</strong>").replace("\n", "<br>")
            f.write(f"<p>{block}</p><hr>")

        f.write("</body></html>")

    return file_path

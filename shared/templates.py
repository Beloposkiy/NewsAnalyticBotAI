"""
Шаблоны текстов для сообщений, уведомлений, PDF и т.д.
"""

REPORT_HEADER = (
    "Отчёт по категории \"{category}\" за период \"{period}\".\n"
    "Дата формирования: {date}\n\n"
)

NO_NEWS_TEMPLATE = "Нет новостей по категории \"{category}\" за выбранный период."

PDF_NEWS_TEMPLATE = (
    "{date}\n"
    "{text}\n"
    "{url}\n"
    "---"
)
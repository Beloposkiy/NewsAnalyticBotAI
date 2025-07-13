"""
Универсальные хелперы: парсинг дат, генерация ссылок, форматирование текста и др.
"""

from datetime import datetime

def parse_date(date_str: str, fmt: str = "%Y-%m-%d %H:%M:%S") -> datetime:
    """
    Преобразует строку в объект datetime.
    """
    return datetime.strptime(date_str, fmt)

def format_datetime(dt: datetime) -> str:
    """
    Форматирует datetime в строку по-русски.
    """
    return dt.strftime("%d.%m.%Y %H:%M")

def get_news_url(channel: str, message_id: int) -> str:
    """
    Генерирует ссылку на сообщение в Telegram-канале.
    """
    return f"https://t.me/{channel}/{message_id}"
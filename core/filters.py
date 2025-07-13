"""
Фильтрация новостей по периоду.
"""

from datetime import datetime, timedelta, timezone

def filter_news_by_period(news: list, period: str) -> list:
    """
    Фильтрует список новостей по периоду (день/неделя/месяц).
    :param news: Список новостей (dict c ключом 'created_at' - datetime).
    :param period: 'day' | 'week' | 'month'
    :return: Список отфильтрованных новостей.
    """
    now = datetime.now(timezone.utc)  # Делаем now timezone-aware
    if period == "day":
        start = now - timedelta(days=1)
    elif period == "week":
        start = now - timedelta(weeks=1)
    elif period == "month":
        start = now - timedelta(days=30)
    else:
        raise ValueError("Unknown period")
    # Сравниваем только aware-datetimes
    return [n for n in news if n['created_at'] >= start]
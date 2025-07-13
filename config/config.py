"""
Глобальные настройки проекта (пути, параметры, токены).
BOT_TOKEN обязательно хранится в .env.
"""

import os
from dotenv import load_dotenv

# Загрузить переменные окружения из .env (автоматически один раз на проект)
load_dotenv()

# Токен Telegram-бота (необходим для запуска aiogram)
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("В .env не найден BOT_TOKEN! Пропишите его в формате:\nBOT_TOKEN=xxx:yyy")

# Дополнительные общие параметры (при необходимости)
DEFAULT_REPORTS_FOLDER = "reports"
DEFAULT_SESSIONS_FOLDER = "sessions"
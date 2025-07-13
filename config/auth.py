"""
Авторизационные данные Telegram API для Telethon/pyrogram.
API_ID и API_HASH берутся из https://my.telegram.org, SESSION_NAME — любое имя сессии.
Все данные должны храниться в .env и подгружаться через dotenv.
"""

import os
from dotenv import load_dotenv

load_dotenv()

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
SESSION_NAME = os.getenv("SESSION_NAME", "anon")

# Преобразование API_ID к int и проверка
try:
    API_ID = int(API_ID)
except (TypeError, ValueError):
    API_ID = None

if not API_ID or not API_HASH:
    raise ValueError(
        "В .env должны быть заданы API_ID и API_HASH для Telegram API!\n"
        "Пример .env:\nAPI_ID=123456\nAPI_HASH=xxxxxxxxx\nSESSION_NAME=anon"
    )
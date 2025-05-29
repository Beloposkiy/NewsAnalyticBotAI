#ЗАПУСКАТЬ СТРОГО ИЗ КОНСОЛИ!!!
from telethon.sync import TelegramClient
from dotenv import load_dotenv
import os

# Загрузка переменных из .env
load_dotenv()

# Получение API ID и HASH
api_id = int(os.getenv("TG_API_ID"))
api_hash = os.getenv("TG_API_HASH")

# Абсолютный путь к папке sessions/
session_dir = os.path.join(os.getcwd(), "sessions")
os.makedirs(session_dir, exist_ok=True)

# Путь к session-файлу без расширения
session_path = os.path.join(session_dir, "news_monitoring")

# Инициализация клиента
client = TelegramClient(session_path, api_id, api_hash)

# Проверка подключения и авторизации
if not client.is_connected():
    client.connect()

if not client.is_user_authorized():
    print("🔐 Требуется авторизация. Введите код из Telegram.")
    client.start()  # запускает интерактивную авторизацию
    print("✅ Авторизация завершена!")
else:
    print("✅ Уже авторизован!")



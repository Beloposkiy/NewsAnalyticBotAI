from dotenv import load_dotenv
import os

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
api_id = int(os.getenv("TG_API_ID"))
api_hash = os.getenv("TG_API_HASH")
session_path = os.getenv("TG_SESSION_PATH", "../sessions/news_monitoring")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID"))


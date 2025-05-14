from dotenv import load_dotenv
import os

load_dotenv()  # загружает переменные из .env

BOT_TOKEN = os.getenv("BOT_TOKEN")
api_id = int(os.getenv("TG_API_ID"))
api_hash = os.getenv("TG_API_HASH")
from telethon import TelegramClient
from datetime import datetime, timedelta, timezone
from init_settings.config import api_id, api_hash
import os

class NewsReader:
    def __init__(self):
        session_dir = os.path.join(os.getcwd(), "sessions")
        os.makedirs(session_dir, exist_ok=True)
        session_path = os.path.join(session_dir, "news_monitoring")
        self.client = TelegramClient(session_path, api_id, api_hash)

    async def init(self):
        await self.client.connect()
        if not await self.client.is_user_authorized():
            raise RuntimeError("\u274c Не авторизован TelegramClient. Запусти auth_tg.py.")

    async def telegram_reader(self, channel_username: str, limit=100, days=1):
        messages = []
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

        async with self.client:
            try:
                result = await self.client.get_messages(channel_username, limit=limit)
                for message in result:
                    if (message.message
                            and message.date >= cutoff_date
                            and not self._is_noise(message.message)):
                        messages.append({
                            "title": message.message.strip(),
                            "url": f"https://t.me/{channel_username}/{message.id}",
                            "created_at": message.date.astimezone()
                        })
            except Exception as e:
                print(f"❌ Ошибка при получении новостей из @{channel_username}: {e}")
        return messages

    @staticmethod
    def _is_noise(text):
        mentions = text.count("@")
        links = text.count("http")
        if mentions >= 3 and links == 0:
            return True
        if len(text) < 30:
            return True
        return False
from telethon import TelegramClient
from telethon.tl.functions.messages import GetHistoryRequest
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

    async def telegram_reader(self, channel_username: str, limit=50, days=1):
        messages = []
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

        async with self.client:
            try:
                result = await self.client(GetHistoryRequest(
                    peer=channel_username,
                    limit=limit,
                    offset_date=None,
                    offset_id=0,
                    max_id=0,
                    min_id=0,
                    add_offset=0,
                    hash=0
                ))
                for message in result.messages:
                    if (message.message
                            and message.date >= cutoff_date
                            and not self._is_noise(message.message)):
                        messages.append({
                            "title": message.message.strip()[:150],
                            "url": f"https://t.me/{channel_username}/{message.id}"
                        })
            except Exception as e:
                print(f"❌ Ошибка при получении новостей из @{channel_username}: {e}")

        return messages

    def _is_noise(self, text):
        mentions = text.count("@")
        links = text.count("http")
        if mentions >= 3 and links == 0:
            return True
        if len(text) < 30:
            return True
        return False
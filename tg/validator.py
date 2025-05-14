from telethon.tl.functions.messages import GetHistoryRequest
from telethon.errors import ChannelPrivateError, UsernameInvalidError, UsernameNotOccupiedError
import logging

logger = logging.getLogger(__name__)

class Validator:
    def __init__(self, telegram_client):
        self.client = telegram_client

    async def validate_telegram_channels(self, channels: list, limit: int = 10):
        """
        Проверяет доступность Telegram-каналов.
        Возвращает два списка: рабочие каналы и нерабочие с причинами.
        """
        working = []
        failed = {}

        async with self.client:
            for channel in channels:
                try:
                    result = await self.client(GetHistoryRequest(
                        peer=channel,
                        limit=limit,
                        offset_date=None,
                        offset_id=0,
                        max_id=0,
                        min_id=0,
                        add_offset=0,
                        hash=0
                    ))
                    if result.messages:
                        working.append(channel)
                        logger.info(f"✅ TG @{channel}: {len(result.messages)} сообщений")
                    else:
                        failed[channel] = "Нет сообщений"
                        logger.warning(f"⚠️ TG @{channel}: нет сообщений")
                except (UsernameInvalidError, UsernameNotOccupiedError):
                    failed[channel] = "Канал не существует"
                    logger.warning(f"❌ TG @{channel}: канал не существует")
                except ChannelPrivateError:
                    failed[channel] = "Приватный канал"
                    logger.warning(f"🔒 TG @{channel}: приватный канал")
                except Exception as e:
                    failed[channel] = str(e)
                    logger.warning(f"❌ TG @{channel}: {e}")

        return working, failed
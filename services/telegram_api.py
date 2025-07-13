import yaml
from telethon import TelegramClient
from datetime import datetime, timezone, timedelta
from config.auth import API_ID, API_HASH, SESSION_NAME
from config.logger import logger

def load_channels(path="data/sources.yaml") -> list:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    logger.info(f"Загружено {len(data.get('channels', []))} каналов из {path}")
    return data["channels"]

CHANNELS = load_channels()

def log_sources_status(sources_info: dict):
    lines = []
    for source, counts in sources_info.items():
        loaded = counts.get("loaded", 0)
        expected = counts.get("expected", 0)

        if expected == 0:
            emoji = "❌"  # нет данных
        elif loaded == 0:
            emoji = "❌"
        elif loaded < expected:
            emoji = "⚠️"
        else:
            emoji = "✅"

        line = f"{source}: {loaded}/{expected} {emoji}"
        lines.append(line)

    log_message = "Статус загрузки каналов:\n" + "\n".join(lines)
    logger.info(log_message)

async def fetch_news_from_channels(period_days) -> list:
    news_list = []
    sources_info = {}

    now = datetime.now(timezone.utc)
    since_date = now - timedelta(days=period_days)

    try:
        async with TelegramClient(SESSION_NAME, API_ID, API_HASH) as client:
            logger.info("Подключение к Telegram выполнено успешно")

            for channel in CHANNELS:
                loaded_count = 0
                expected_count = 0

                try:
                    # Без offset_date — перебираем с самого свежего сообщения
                    async for msg in client.iter_messages(channel):
                        msg_date = msg.date
                        if msg_date.tzinfo is None:
                            msg_date = msg_date.replace(tzinfo=timezone.utc)
                        else:
                            msg_date = msg_date.astimezone(timezone.utc)

                        if msg_date < since_date:
                            break  # прекращаем, если сообщение старее нужного периода

                        expected_count += 1

                        if not msg.text:
                            continue

                        news_list.append({
                            "text": msg.text,
                            "created_at": msg_date.astimezone(),  # локальное время
                            "url": f"https://t.me/{channel}/{msg.id}",
                            "channel": channel,
                        })
                        loaded_count += 1

                except Exception as err:
                    logger.error(f"Ошибка при чтении канала {channel}: {err}")
                    loaded_count = 0
                    expected_count = 0

                sources_info[channel] = {
                    "loaded": loaded_count,
                    "expected": expected_count
                }

    except Exception as e:
        logger.error(f"Ошибка подключения к Telegram: {e}")

    logger.info(f"Всего получено постов: {len(news_list)}")
    log_sources_status(sources_info)

    return news_list
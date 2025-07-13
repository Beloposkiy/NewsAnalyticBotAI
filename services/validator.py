"""
Проверка доступности каналов и корректности ссылок.
"""

from telethon import TelegramClient
from config.auth import API_ID, API_HASH, SESSION_NAME

def validate_channels(channel_list: list) -> dict:
    """
    Проверяет, доступны ли указанные каналы.
    :param channel_list: список юзернеймов/id каналов
    :return: dict {channel: True/False}
    """
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    result = {}
    try:
        client.start()
        for channel in channel_list:
            try:
                entity = client.get_entity(channel)
                result[channel] = True
            except Exception:
                result[channel] = False
        client.disconnect()
    except Exception:
        result = {ch: False for ch in channel_list}
    return result
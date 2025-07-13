from aiogram.types import BotCommand
from config.logger import logger

async def set_bot_commands(bot):
    commands = [
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="topics", description="Показать топ-постов по категориям")
    ]
    try:
        await bot.set_my_commands(commands)
        logger.info("Команды бота успешно установлены")
    except Exception as e:
        logger.error(f"Ошибка при установке команд бота: {e}")
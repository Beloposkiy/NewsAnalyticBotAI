import asyncio
from datetime import datetime

from aiogram import Bot, Dispatcher

from bot.bot_commands import set_bot_commands
from config.config import BOT_TOKEN
from bot.handlers import router
from config.logger import logger

# Дополнительно, для окраски в синий используем ANSI коды
BLUE = "\033[94m"
RESET = "\033[0m"

print(f"{BLUE}[{datetime.now().strftime('%H:%M:%S')}] Старт бота{RESET}")
print(f"{BLUE}[{datetime.now().strftime('%H:%M:%S')}] Инициализация бота...{RESET}")

async def main():
    try:
        bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
        dp = Dispatcher()
        dp.include_router(router)
        await set_bot_commands(bot)
        await dp.start_polling(bot)
    except Exception as e:
        logger.exception(f"Ошибка в main: {e}")
    finally:
        await bot.session.close()
        print(f"{BLUE}[{datetime.now().strftime('%H:%M:%S')}] Бот завершил работу{RESET}")

if __name__ == "__main__":
    asyncio.run(main())
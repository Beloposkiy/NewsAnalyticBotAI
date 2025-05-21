# shared.py
from aiogram import Bot
from aiogram.enums import ParseMode
from init_settings.config import BOT_TOKEN

bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)

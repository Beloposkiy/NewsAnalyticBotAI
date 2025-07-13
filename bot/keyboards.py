from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from shared.constants import PERIODS, CATEGORY_LABELS

def get_period_keyboard():
    buttons = [
        [InlineKeyboardButton(text=label.capitalize(), callback_data=period)]
        for period, label in zip(PERIODS, ["день", "неделя", "месяц"])
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_categories_keyboard():
    buttons = [
        [InlineKeyboardButton(text=label, callback_data=f"category_{key}")]
        for key, label in CATEGORY_LABELS.items()
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
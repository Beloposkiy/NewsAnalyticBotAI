from aiogram.fsm.state import StatesGroup, State

class NewsStates(StatesGroup):
    waiting_for_period = State()
    waiting_for_category = State()
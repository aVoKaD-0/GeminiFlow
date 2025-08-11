from aiogram.fsm.state import State, StatesGroup

class ApiKeyStates(StatesGroup):
    waiting_for_key = State()

class ChatStates(StatesGroup):
    waiting_for_title = State()
    waiting_for_rename = State()

class AdminStates(StatesGroup):
    waiting_for_broadcast = State()
    waiting_for_user_id = State()
    waiting_for_premium_days = State()
    waiting_for_limits = State()
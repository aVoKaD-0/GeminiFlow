from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List
from database.models import Chat
import uuid
import config

def get_start_keyboard() -> InlineKeyboardMarkup:
    """Main start keyboard"""
    keyboard = [
        [InlineKeyboardButton(text="🔑 API ключ", callback_data="manage_key")],
        [InlineKeyboardButton(text="💬 Мои чаты", callback_data="manage_chats")],
        [InlineKeyboardButton(text="⭐️ Premium", callback_data="premium_info")],
        [InlineKeyboardButton(text="🎁 Пригласи друга", callback_data="referral_info")],
        [InlineKeyboardButton(text="❓ Помощь", callback_data="help")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_api_key_keyboard(has_key: bool = False) -> InlineKeyboardMarkup:
    """API key management keyboard"""
    keyboard = []
    
    if has_key:
        keyboard.append([InlineKeyboardButton(text="🔄 Изменить ключ", callback_data="set_key")])
        keyboard.append([InlineKeyboardButton(text="🗑 Удалить ключ", callback_data="delete_key")])
        keyboard.append([InlineKeyboardButton(text="✅ Проверить ключ", callback_data="test_key")])
    else:
        keyboard.append([InlineKeyboardButton(text="➕ Добавить ключ", callback_data="set_key")])
    
    keyboard.append([InlineKeyboardButton(text="❓ Где взять ключ?", callback_data="key_help")])
    keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_start")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_chats_keyboard(chats: List[Chat], current_chat_id: uuid.uuid4 = None, has_premium: bool = False) -> InlineKeyboardMarkup:
    """Chats management keyboard"""
    keyboard = []
    
    # Chat list
    for chat in chats:
        emoji = "📝" if chat.id == current_chat_id else "💬"
        text = f"{emoji} {chat.title}"
        keyboard.append([InlineKeyboardButton(text=text, callback_data=f"select_chat:{chat.id}")])
    
    # Action buttons
    action_buttons = []
    
    # Create new chat button
    if has_premium or len(chats) < 1:
        action_buttons.append(InlineKeyboardButton(text="➕ Новый чат", callback_data="create_chat"))
    else:
        action_buttons.append(InlineKeyboardButton(text="🔒 Новый чат (Premium)", callback_data="premium_info"))
    
    if action_buttons:
        keyboard.append(action_buttons)
    
    keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_start")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_premium_keyboard(has_premium: bool = False, expires_at = None) -> InlineKeyboardMarkup:
    """Premium info keyboard"""
    keyboard = []
    
    if not has_premium:
        keyboard.append([InlineKeyboardButton(text=f"💳 1 месяц - {config.PREMIUM_PLANS['1']['stars']}⭐", callback_data="buy_premium:1")])
        keyboard.append([InlineKeyboardButton(text=f"💳 3 месяца - {config.PREMIUM_PLANS['3']['stars']}⭐", callback_data="buy_premium:3")])
        keyboard.append([InlineKeyboardButton(text=f"💳 6 месяцев - {config.PREMIUM_PLANS['6']['stars']}⭐", callback_data="buy_premium:6")])
        keyboard.append([InlineKeyboardButton(text=f"💳 1 год - {config.PREMIUM_PLANS['12']['stars']}⭐", callback_data="buy_premium:12")])
    
    keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_start")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_referral_keyboard(telegram_id: int) -> InlineKeyboardMarkup:
    """Referral system keyboard"""
    ref_link = f"https://t.me/your_bot_name?start=ref{telegram_id}"
    
    keyboard = [
        [InlineKeyboardButton(text="📤 Поделиться", url=f"https://t.me/share/url?url={ref_link}")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_start")]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_admin_keyboard() -> InlineKeyboardMarkup:
    """Admin panel keyboard"""
    keyboard = [
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="👤 Инфо о пользователе", callback_data="admin_userinfo")],
        [InlineKeyboardButton(text="⭐ Выдать Premium", callback_data="admin_grant_premium")],
        [InlineKeyboardButton(text="🚫 Забанить", callback_data="admin_ban_user")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Cancel action keyboard"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
    ])

def get_confirm_keyboard(action: str) -> InlineKeyboardMarkup:
    """Confirmation keyboard"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да", callback_data=f"confirm:{action}")],
        [InlineKeyboardButton(text="❌ Нет", callback_data="cancel")]
    ])

def get_chat_settings_keyboard(chat_id: uuid.uuid4) -> InlineKeyboardMarkup:
    """Клавиатура настроек чата."""
    keyboard = [
        [InlineKeyboardButton(text="🤖 Модель", callback_data=f"chat_settings:model:{chat_id}")],
        [InlineKeyboardButton(text="🌡️ Температура", callback_data=f"chat_settings:temperature:{chat_id}")],
        [InlineKeyboardButton(text="🎭 Личность (System Prompt)", callback_data=f"chat_settings:system:{chat_id}")],
        [InlineKeyboardButton(text="⚙️ Продвинутые настройки", callback_data=f"chat_settings:advanced:{chat_id}")],
        [InlineKeyboardButton(text="✏️ Переименовать чат", callback_data=f"rename_chat:{chat_id}"),
         InlineKeyboardButton(text="🗑 Удалить чат", callback_data=f"delete_chat:{chat_id}")],
        # [InlineKeyboardButton(text="💾 Скачать чат", callback_data=f"chat_settings:download:{chat_id}")], # Пока не реализуем
        [InlineKeyboardButton(text="⬅️ Назад к чатам", callback_data="chats")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_model_selection_keyboard(models: list, chat_id: uuid.uuid4) -> InlineKeyboardMarkup:
    """Клавиатура выбора модели."""
    keyboard = []
    for idx, model in enumerate(models):
        # Передаём индекс вместо названия модели, чтобы уложиться в лимит callback_data (<=64 байт)
        keyboard.append([InlineKeyboardButton(text=model, callback_data=f"model_select:{idx}:{chat_id}")])
    keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=f"back_to_chat_settings:{chat_id}")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_temperature_keyboard(chat_id: uuid.uuid4) -> InlineKeyboardMarkup:
    """Клавиатура выбора температуры (или кнопка для ввода)."""
    # Можно сделать кнопки для шагов 0.0, 0.2, ..., 2.0
    # Или просто кнопку для ввода значения
    keyboard = [
        # [InlineKeyboardButton(text="0.0", callback_data=f"temp_set:0.0:{chat_id}"),
        #  InlineKeyboardButton(text="0.2", callback_data=f"temp_set:0.2:{chat_id}"),
        #  InlineKeyboardButton(text="0.4", callback_data=f"temp_set:0.4:{chat_id}")],
        # [InlineKeyboardButton(text="0.6", callback_data=f"temp_set:0.6:{chat_id}"),
        #  InlineKeyboardButton(text="0.8", callback_data=f"temp_set:0.8:{chat_id}"),
        #  InlineKeyboardButton(text="1.0", callback_data=f"temp_set:1.0:{chat_id}")],
        # [InlineKeyboardButton(text="1.2", callback_data=f"temp_set:1.2:{chat_id}"),
        #  InlineKeyboardButton(text="1.4", callback_data=f"temp_set:1.4:{chat_id}"),
        #  InlineKeyboardButton(text="1.6", callback_data=f"temp_set:1.6:{chat_id}")],
        # [InlineKeyboardButton(text="1.8", callback_data=f"temp_set:1.8:{chat_id}"),
        #  InlineKeyboardButton(text="2.0", callback_data=f"temp_set:2.0:{chat_id}")],
        [InlineKeyboardButton(text="✏️ Ввести значение", callback_data=f"temp_input:{chat_id}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"back_to_chat_settings:{chat_id}")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_advanced_settings_keyboard(chat_id: uuid.uuid4) -> InlineKeyboardMarkup:
    """Клавиатура продвинутых настроек."""
    keyboard = [
        [InlineKeyboardButton(text="✏️ Ввести Top-P и Top-K", callback_data=f"advanced_input:{chat_id}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"back_to_chat_settings:{chat_id}")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_system_prompt_presets_keyboard(chat_id: uuid.uuid4) -> InlineKeyboardMarkup:
    """Клавиатура с пресетами системных промптов."""
    presets = [
        "Эксперт по Python",
        "Креативный копирайтер",
        "Помощник в путешествиях",
        "Саркастичный ассистент",
        "Переводчик"
    ]
    keyboard = []
    for idx, preset in enumerate(presets):
        # Передаём индекс вместо полного текста пресета
        keyboard.append([InlineKeyboardButton(text=preset, callback_data=f"preset_select:{idx}:{chat_id}")])
    keyboard.append([InlineKeyboardButton(text="✏️ Ввести свой", callback_data=f"custom_prompt_input:{chat_id}")])
    keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=f"back_to_chat_settings:{chat_id}")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_back() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_start")]
    ])

def get_create_new_chat_keyboard(chat_id: uuid.uuid4) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="параметры чата", callback_data=f"select_chat:{chat_id}")]
    ])
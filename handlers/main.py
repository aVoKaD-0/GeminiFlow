# handlers/main.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from database.models import User
from keyboards import get_api_key_keyboard, get_chats_keyboard, get_premium_keyboard
from services.user_service import UserService
from services.chat_service import ChatService
import config
from handlers.premium import PREMIUM_PLANS

router = Router()

# --- Обработчики команд ---
@router.message(Command("api_key"))
async def cmd_api_key_command(message: Message, user: User, **kwargs):
    """
    Обработчик команды /api_key.
    Перенаправляет в меню управления API ключом.
    """
    has_key = bool(user.api_key_encrypted)
    if has_key:
        text = """🔑 <b>Управление API ключом</b>
✅ <b>Статус:</b> Ключ установлен
🔒 <b>Безопасность:</b> Ключ зашифрован
Выберите действие:"""
    else:
        text = """🔑 <b>Управление API ключом</b>
❌ <b>Статус:</b> Ключ не установлен
Для работы с Gemini необходимо добавить ваш API ключ.
Выберите действие:"""

    await message.answer(
        text,
        reply_markup=get_api_key_keyboard(has_key),
        parse_mode="HTML"
    )

@router.message(Command("chats"))
async def cmd_chat_command(message: Message, user: User, session, has_premium: bool, **kwargs):
    """
    Обработчик команды /chat.
    Перенаправляет в меню управления чатами.
    """
    chats = await ChatService.get_user_chats(session, user.telegram_id)
    current_chat = await UserService.get_current_chat(session, user.telegram_id)
    current_chat_id = current_chat.id if current_chat else None

    text = f"""💬 <b>Управление чатами</b>
📊 <b>Статистика:</b>
• Чатов: {len(chats)}/{config.PREMIUM_CHAT_LIMIT if has_premium else config.FREE_CHAT_LIMIT}
• Статус: {"Premium" if has_premium else "Free"}
• Активный чат: {current_chat.title if current_chat else "Не выбран"}
Выберите чат или создайте новый:"""

    await message.answer(
        text,
        reply_markup=get_chats_keyboard(chats, current_chat_id, has_premium),
        parse_mode="HTML"
    )

@router.message(Command("premium"))
async def cmd_premium_command(message: Message, user: User, session, has_premium: bool, **kwargs):
    """
    Обработчик команды /premium.
    Показывает информацию о Premium.
    """
    # Импортируем необходимые данные из premium.py или определяем здесь
    if has_premium:
        expires_text = ""
        if user.subscription_expires_at:
            expires_text = f"\n🗓 Действует до: {user.subscription_expires_at.strftime('%d.%m.%Y %H:%M')}"
        text = f"""⭐ <b>Premium статус</b>
✅ <b>Статус:</b> Активен{expires_text}
<b>Ваши Premium возможности:</b>
• 🤖 Доступ к современным моделям Gemini
• 💬 До {config.PREMIUM_CHAT_LIMIT} чатов
• ⚡ Приоритетная обработка
• 🎯 Выбор модели для каждого чата
• поддержка файлов до 20 МБ

<b>Спасибо за поддержку проекта! 💖</b>"""
    else:
        text = f"""⭐ <b>Premium подписка</b>
<b>Получите больше возможностей:</b>
• 🤖 Доступ к современным моделям Gemini
• 💬 До {config.PREMIUM_CHAT_LIMIT} чатов вместо 1
• ⚡ Приоритетная обработка запросов
• 🎯 Выбор модели для каждого чата
• поддержка файлов до 20 МБ

<b>💰 Цены:</b>
• 1 месяц - {PREMIUM_PLANS["1"]["stars"]}⭐ (~$1)
• 3 месяца - {PREMIUM_PLANS["3"]["stars"]}⭐ (~$2.5) 🔥
• 6 месяцев - {PREMIUM_PLANS["6"]["stars"]}⭐ (~$4.5) 💎
• 1 год - {PREMIUM_PLANS["12"]["stars"]}⭐ (~$8) ⚡
Выберите подходящий план:"""

    # Предполагаем, что get_premium_keyboard доступен или импортирован
    await message.answer(
        text,
        reply_markup=get_premium_keyboard(has_premium, user.subscription_expires_at),
        parse_mode="HTML"
    )

# --- Обработчики callback_query для кнопок из меню команд ---
# (Если вы хотите, чтобы кнопки меню вели к тем же действиям, что и inline-кнопки)

# Примеры (необязательно, если основная логика уже в других хендлерах):
# @router.callback_query(F.data == "manage_key")
# async def cb_manage_key(callback: CallbackQuery, user: User, **kwargs):
#     # Логика уже есть в handlers/api_key.py
#     pass

# Добавьте другие callback handlers при необходимости...

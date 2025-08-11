from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from database.models import User
from services.user_service import UserService
from keyboards import get_start_keyboard

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, user: User, session, **kwargs):
    # Check for referral link
    if message.text and len(message.text.split()) > 1:
        args = message.text.split()[1]
        if args.startswith("ref"):
            try:
                referrer_id = int(args[3:])  # Remove "ref" prefix
                if referrer_id != user.telegram_id:
                    await UserService.process_referral(session, referrer_id, user.telegram_id)
                    await message.answer("🎉 Вы перешли по реферальной ссылке!")
            except ValueError:
                pass
    
    welcome_text = """🤖 <b>Добро пожаловать в Gemini Flow!</b>

Я современный Telegram-бот для работы с Google Gemini AI.

<b>Что я умею:</b>
• 💬 Ведение умных диалогов с Gemini
• 📚 Управление множественными чатами
• 🔐 Безопасное хранение вашего API-ключа
• ⚡ Оптимизация контекста для экономии токенов

<b>Принцип работы BYOK:</b>
Вы предоставляете свой API-ключ Gemini, а я обеспечиваю удобный интерфейс для работы.

Выберите действие:"""

    await message.answer(
        welcome_text,
        reply_markup=get_start_keyboard(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "back_to_start")
async def back_to_start(callback: CallbackQuery, user: User, **kwargs):
    welcome_text = """🤖 <b>Gemini Flow - Главное меню</b>

Выберите действие:"""

    await callback.message.edit_text(
        welcome_text,
        reply_markup=get_start_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "help")
async def show_help(callback: CallbackQuery, **kwargs):
    help_text = """📖 <b>Справка по Gemini Flow</b>

<b>🔑 API ключ:</b>
• Получите бесплатный ключ: https://aistudio.google.com/app/apikey
• Ключ хранится в зашифрованном виде
• Используется только для ваших запросов

<b>💬 Чаты:</b>
• Free: 1 чат с моделью gemini-2.5-flash
• Premium: до 10 чатов с выбором модели

<b>⭐ Premium возможности:</b>
• Доступ к современным моделям Gemini
• Множественные чаты
• Приоритетная поддержка

<b>🎁 Реферальная программа:</b>
• Пригласите 5 друзей
• Получите месяц Premium бесплатно

<b>📞 Поддержка:</b>
• Telegram: @GuRu_ege_official"""

    keyboard = [[{"text": "◀️ Назад", "callback_data": "back_to_start"}]]
    
    await callback.message.edit_text(
        help_text,
        reply_markup={"inline_keyboard": keyboard},
        parse_mode="HTML"
    )
    await callback.answer()
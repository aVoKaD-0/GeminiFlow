from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from database.models import User
from services.gemini_service import GeminiService
from utils.crypto import encrypt_api_key
from keyboards import get_api_key_keyboard, get_cancel_keyboard, get_back
from states import ApiKeyStates
from services.chat_settings_service import ChatSettingsService
import logging

logger = logging.getLogger(__name__)

router = Router()
gemini_service = GeminiService()

@router.callback_query(F.data == "manage_key")
async def manage_api_key(callback: CallbackQuery, user: User, **kwargs):
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

    await callback.message.edit_text(
        text,
        reply_markup=get_api_key_keyboard(has_key),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "set_key")
async def request_api_key(callback: CallbackQuery, state: FSMContext, **kwargs):
    await state.set_state(ApiKeyStates.waiting_for_key)
    
    text = """🔑 <b>Добавление API ключа</b>

Отправьте ваш API ключ Gemini.

<b>Где получить ключ:</b>
1. Перейдите на https://aistudio.google.com/app/apikey
2. Нажмите "Create API Key"
3. Скопируйте ключ и отправьте его сюда

<b>🔒 Безопасность:</b>
Ключ будет зашифрован и использован только для ваших запросов."""

    await callback.message.edit_text(
        text,
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(ApiKeyStates.waiting_for_key)
async def process_api_key(message: Message, state: FSMContext, user: User, session, **kwargs):
    api_key = message.text.strip()
    
    # Basic validation
    if not api_key or len(api_key) < 20:
        await message.answer("❌ Неверный формат API ключа. Попробуйте еще раз.")
        return
    
    # Delete user message for security
    try:
        await message.delete()
    except:
        pass
    
    await message.answer("🔄 Проверяю ключ...")
    
    try:
        # Encrypt and temporarily save
        encrypted_key = encrypt_api_key(api_key)

        chat_info = await ChatSettingsService.get_chat_info(session, user.current_chat_id, user.telegram_id)
        
        # Validate key
        is_valid = await gemini_service.validate_api_key(encrypted_key, model_name=chat_info['model_name'])
        
        if is_valid:
            # Save to database
            user.api_key_encrypted = encrypted_key
            await session.commit()
            
            await message.answer(
                "✅ API ключ успешно добавлен и проверен!",
                reply_markup=get_api_key_keyboard(True)
            )
        else:
            await message.answer(
                "❌ Неверный API ключ. Проверьте правильность и попробуйте еще раз.",
                reply_markup=get_api_key_keyboard(bool(user.api_key_encrypted))
            )
    
    except Exception as e:
        await message.answer(
            f"❌ Ошибка при проверке ключа: {str(e)}",
            reply_markup=get_api_key_keyboard(bool(user.api_key_encrypted))
        )
    finally:
        await state.clear()

@router.callback_query(F.data == "delete_key")
async def delete_api_key(callback: CallbackQuery, user: User, session, **kwargs):
    user.api_key_encrypted = None
    await session.commit()
    
    await callback.message.edit_text(
        "🗑 API ключ удален.",
        reply_markup=get_api_key_keyboard(False)
    )
    await callback.answer("Ключ удален")

@router.callback_query(F.data == "test_key")
async def test_api_key(callback: CallbackQuery, user: User, session, **kwargs):
    if not user.api_key_encrypted:
        await callback.answer("❌ Ключ не установлен", show_alert=True)
        return
    
    await callback.answer("🔄 Проверяю ключ...")
    
    try:
        chat_info = await ChatSettingsService.get_chat_info(session, user.current_chat_id, user.telegram_id)
        is_valid = await gemini_service.validate_api_key(user.api_key_encrypted, model_name=chat_info['model_name'])
        
        if is_valid:
            await callback.message.answer("✅ API ключ работает корректно!")
        else:
            await callback.message.answer("❌ API ключ не работает. Проверьте его актуальность.")
    
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка при проверке: {str(e)}")

@router.callback_query(F.data == "key_help")
async def show_key_help(callback: CallbackQuery, **kwargs):
    help_text = """🔑 <b>Как получить API ключ Gemini</b>

<b>Шаг 1:</b> Перейдите на сайт Google AI Studio
🔗 https://aistudio.google.com/app/apikey

<b>Шаг 2:</b> Войдите в аккаунт Google

<b>Шаг 3:</b> Нажмите "Create API Key"

<b>Шаг 4:</b> Выберите проект или создайте новый

<b>Шаг 5:</b> Скопируйте созданный ключ

<b>🔒 Безопасность:</b>
• Никому не передавайте ваш ключ
• Ключ хранится в зашифрованном виде
• Используется только для ваших запросов

<b>💰 Стоимость:</b>
Gemini API имеет бесплатный лимит, достаточный для большинства пользователей."""

    keyboard = [[{"text": "◀️ Назад", "callback_data": "manage_key"}]]
    
    await callback.message.edit_text(
        help_text,
        reply_markup={"inline_keyboard": keyboard},
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "cancel")
async def cancel_action(callback: CallbackQuery, state: FSMContext, **kwargs):
    await state.clear()
    await callback.message.edit_text(
        "❌ Действие отменено.",
        reply_markup=get_back()
    )
    await callback.answer()
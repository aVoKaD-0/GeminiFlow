from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from database.models import User, Chat, Message as DBMessage
from services.user_service import UserService
from keyboards import get_admin_keyboard, get_cancel_keyboard
from states import AdminStates
from sqlalchemy import select, func, and_
from datetime import datetime, timedelta
import asyncio
import config

router = Router()

def is_admin(user: User) -> bool:
    """Check if user is admin"""
    return user.is_admin or user.telegram_id in config.ADMIN_IDS

@router.message(Command("admin"))
async def admin_panel(message: Message, user: User, **kwargs):
    if not is_admin(user):
        await message.answer("❌ У вас нет прав администратора.")
        return
    
    text = """👨‍💼 <b>Панель администратора</b>

Выберите действие:"""

    await message.answer(
        text,
        reply_markup=get_admin_keyboard(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "admin_stats")
async def show_stats(callback: CallbackQuery, session, user: User, **kwargs):
    if not is_admin(user):
        await callback.answer("❌ Нет прав", show_alert=True)
        return
    
    # Total users
    result = await session.execute(select(func.count(User.telegram_id)))
    total_users = result.scalar() or 0
    
    # New users today
    today = datetime.utcnow().date()
    result = await session.execute(
        select(func.count(User.telegram_id)).where(
            func.date(User.created_at) == today
        )
    )
    new_today = result.scalar() or 0
    
    # Premium users
    result = await session.execute(
        select(func.count(User.telegram_id)).where(
            and_(
                User.subscription_plan == "pro",
                User.subscription_expires_at > datetime.utcnow()
            )
        )
    )
    premium_users = result.scalar() or 0
    
    # Total chats
    result = await session.execute(select(func.count(Chat.id)))
    total_chats = result.scalar() or 0
    
    # Messages today
    result = await session.execute(
        select(func.count(DBMessage.id)).where(
            func.date(DBMessage.timestamp) == today
        )
    )
    messages_today = result.scalar() or 0
    
    # Users with API keys
    result = await session.execute(
        select(func.count(User.telegram_id)).where(
            User.api_key_encrypted.isnot(None)
        )
    )
    users_with_keys = result.scalar() or 0
    
    text = f"""📊 <b>Статистика бота</b>

👥 <b>Пользователи:</b>
• Всего: {total_users}
• Новых сегодня: {new_today}
• Premium: {premium_users}
• С API ключами: {users_with_keys}

💬 <b>Чаты:</b>
• Всего создано: {total_chats}
• Сообщений сегодня: {messages_today}

📈 <b>Конверсия:</b>
• Активация ключей: {(users_with_keys/total_users*100) if total_users > 0 else 0:.1f}%
• Premium конверсия: {(premium_users/total_users*100) if total_users > 0 else 0:.1f}%

🕐 <b>Обновлено:</b> {datetime.utcnow().strftime('%d.%m.%Y %H:%M')} UTC"""

    keyboard = [[{"text": "🔄 Обновить", "callback_data": "admin_stats"}],
                [{"text": "◀️ Назад", "callback_data": "admin_back"}]]
    
    await callback.message.edit_text(
        text,
        reply_markup={"inline_keyboard": keyboard},
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "admin_broadcast")
async def request_broadcast(callback: CallbackQuery, state: FSMContext, user: User, **kwargs):
    if not is_admin(user):
        await callback.answer("❌ Нет прав", show_alert=True)
        return
    
    await state.set_state(AdminStates.waiting_for_broadcast)
    
    await callback.message.edit_text(
        "📢 <b>Рассылка сообщения</b>\n\n"
        "Отправьте сообщение для рассылки всем пользователям.\n\n"
        "⚠️ <b>Внимание:</b> Рассылка будет отправлена всем активным пользователям.",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(AdminStates.waiting_for_broadcast)
async def process_broadcast(message: Message, state: FSMContext, session, user: User, **kwargs):
    if not is_admin(user):
        return
    
    broadcast_text = message.text
    
    # Get all users
    result = await session.execute(
        select(User.telegram_id).where(User.subscription_plan != "banned")
    )
    user_ids = [row[0] for row in result.fetchall()]
    
    await message.answer(f"📤 Начинаю рассылку для {len(user_ids)} пользователей...")
    
    success_count = 0
    error_count = 0
    
    for user_id in user_ids:
        try:
            await message.bot.send_message(user_id, broadcast_text)
            success_count += 1
            
            # Small delay to avoid rate limits
            await asyncio.sleep(0.05)
            
        except Exception as e:
            error_count += 1
            if error_count <= 10:  # Log first 10 errors
                print(f"Broadcast error for user {user_id}: {e}")
    
    await message.answer(
        f"✅ <b>Рассылка завершена!</b>\n\n"
        f"📤 Отправлено: {success_count}\n"
        f"❌ Ошибок: {error_count}",
        parse_mode="HTML"
    )
    
    await state.clear()

@router.callback_query(F.data == "admin_userinfo")
async def request_user_id(callback: CallbackQuery, state: FSMContext, user: User, **kwargs):
    if not is_admin(user):
        await callback.answer("❌ Нет прав", show_alert=True)
        return
    
    await state.set_state(AdminStates.waiting_for_user_id)
    
    await callback.message.edit_text(
        "👤 <b>Информация о пользователе</b>\n\n"
        "Отправьте Telegram ID пользователя:",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(AdminStates.waiting_for_user_id)
async def show_user_info(message: Message, state: FSMContext, session, user: User, **kwargs):
    if not is_admin(user):
        return
    
    try:
        target_user_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Неверный формат ID. Введите числовой ID.")
        return
    
    # Get user info
    result = await session.execute(
        select(User).where(User.telegram_id == target_user_id)
    )
    target_user = result.scalar_one_or_none()
    
    if not target_user:
        await message.answer("❌ Пользователь не найден.")
        await state.clear()
        return
    
    # Get chat count
    chat_count = await UserService.get_user_chat_count(session, target_user_id)
    
    # Get message count
    result = await session.execute(
        select(func.count(DBMessage.id)).join(Chat).where(Chat.user_id == target_user_id)
    )
    message_count = result.scalar() or 0
    
    # Format subscription info
    sub_info = target_user.subscription_plan
    if target_user.subscription_expires_at:
        sub_info += f" (до {target_user.subscription_expires_at.strftime('%d.%m.%Y')})"
    
    text = f"""👤 <b>Информация о пользователе</b>

🆔 <b>ID:</b> <code>{target_user.telegram_id}</code>
👤 <b>Username:</b> @{target_user.username or 'не указан'}
📅 <b>Регистрация:</b> {target_user.created_at.strftime('%d.%m.%Y %H:%M')}

💰 <b>Подписка:</b> {sub_info}
🔑 <b>API ключ:</b> {"✅ Установлен" if target_user.api_key_encrypted else "❌ Не установлен"}
👨‍💼 <b>Админ:</b> {"✅ Да" if target_user.is_admin else "❌ Нет"}

💬 <b>Активность:</b>
• Чатов: {chat_count}
• Сообщений: {message_count}

🎁 <b>Реферальная награда:</b> {"✅ Получена" if target_user.reward_claimed else "❌ Не получена"}"""

    await message.answer(text, parse_mode="HTML")
    await state.clear()

@router.callback_query(F.data == "admin_grant_premium")
async def request_premium_grant(callback: CallbackQuery, state: FSMContext, user: User, **kwargs):
    if not is_admin(user):
        await callback.answer("❌ Нет прав", show_alert=True)
        return
    
    await state.clear()

    await state.set_state(AdminStates.waiting_for_premium_days)
    
    await callback.message.edit_text(
        "⭐ <b>Выдача Premium</b>\n\n"
        "Отправьте сообщение в формате:\n"
        "<code>USER_ID DAYS</code>\n\n"
        "Например: <code>123456789 30</code>",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(AdminStates.waiting_for_premium_days)
async def grant_premium_access(message: Message, state: FSMContext, session, user: User, **kwargs):
    if not is_admin(user):
        return
    
    try:
        parts = message.text.strip().split()
        if len(parts) != 2:
            raise ValueError("Wrong format")
        
        target_user_id = int(parts[0])
        days = int(parts[1])
        
        if days <= 0 or days > 3650:  # Max 10 years
            raise ValueError("Invalid days")
        
    except ValueError:
        await message.answer("❌ Неверный формат. Используйте: USER_ID DAYS")
        return
    
    # Check if user exists
    result = await session.execute(
        select(User).where(User.telegram_id == target_user_id)
    )
    target_user = result.scalar_one_or_none()
    
    if not target_user:
        await message.answer("❌ Пользователь не найден.")
        await state.clear()
        return
    
    # Grant premium
    await UserService.grant_premium(session, target_user_id, days)
    
    await message.answer(
        f"✅ Premium на {days} дней выдан пользователю {target_user_id}\n"
        f"👤 @{target_user.username or 'без username'}"
    )
    
    # Notify user
    try:
        await message.bot.send_message(
            target_user_id,
            f"🎉 <b>Вам выдан Premium доступ!</b>\n\n"
            f"⭐ Срок: {days} дней\n"
            f"🎁 Подарок от администрации\n\n"
            f"Наслаждайтесь расширенными возможностями!",
            parse_mode="HTML"
        )
    except:
        pass  # User might have blocked the bot
    
    await state.clear()

@router.callback_query(F.data == "admin_ban_user")
async def request_ban_user(callback: CallbackQuery, state: FSMContext, user: User, **kwargs):
    if not is_admin(user):
        await callback.answer("❌ Нет прав", show_alert=True)
        return
    
    await state.set_state(AdminStates.waiting_for_user_id)
    await state.update_data(action="ban")
    
    await callback.message.edit_text(
        "🚫 <b>Блокировка пользователя</b>\n\n"
        "Отправьте Telegram ID пользователя для блокировки:",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(AdminStates.waiting_for_user_id, F.text)
async def process_admin_action(message: Message, state: FSMContext, session, user: User, **kwargs):
    if not is_admin(user):
        return
    
    data = await state.get_data()
    action = data.get("action")
    
    if action == "ban":
        try:
            target_user_id = int(message.text.strip())
        except ValueError:
            await message.answer("❌ Неверный формат ID.")
            return
        
        # Get user
        result = await session.execute(
            select(User).where(User.telegram_id == target_user_id)
        )
        target_user = result.scalar_one_or_none()
        
        if not target_user:
            await message.answer("❌ Пользователь не найден.")
            await state.clear()
            return
        
        # Ban user
        target_user.subscription_plan = "banned"
        await session.commit()
        
        await message.answer(
            f"🚫 Пользователь {target_user_id} заблокирован\n"
            f"👤 @{target_user.username or 'без username'}"
        )
        
        await state.clear()

@router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery, user: User, **kwargs):
    if not is_admin(user):
        await callback.answer("❌ Нет прав", show_alert=True)
        return
    
    text = """👨‍💼 <b>Панель администратора</b>

Выберите действие:"""

    await callback.message.edit_text(
        text,
        reply_markup=get_admin_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "cancel")
async def cancel_admin_action(callback: CallbackQuery, state: FSMContext, user: User, **kwargs):
    if not is_admin(user):
        await callback.answer("❌ Нет прав", show_alert=True)
        return
    
    await state.clear()
    
    text = """👨‍💼 <b>Панель администратора</b>

Выберите действие:"""

    await callback.message.edit_text(
        text,
        reply_markup=get_admin_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer("❌ Действие отменено")
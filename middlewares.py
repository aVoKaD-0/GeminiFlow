from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from typing import Callable, Dict, Any, Awaitable
from database import async_session
from services.user_service import UserService
from database.models import User
import time
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class DatabaseMiddleware(BaseMiddleware):
    """Middleware to provide database session"""
    
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        async with async_session() as session:
            data["session"] = session
            return await handler(event, data)

class UserMiddleware(BaseMiddleware):
    """Middleware to get or create user"""
    
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        session = data.get("session")
        if not session:
            return await handler(event, data)
        
        telegram_id = event.from_user.id
        username = event.from_user.username
        
        user = await UserService.get_or_create_user(session, telegram_id, username)
        data["user"] = user
        
        return await handler(event, data)

class RateLimitMiddleware(BaseMiddleware):
    """Rate limiting middleware"""
    
    def __init__(self):
        self.user_requests = {}
    
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        # Only apply to messages, not callback queries
        if isinstance(event, CallbackQuery):
            return await handler(event, data)
        
        user_id = event.from_user.id
        current_time = time.time()
        
        # Clean old requests
        if user_id in self.user_requests:
            self.user_requests[user_id] = [
                req_time for req_time in self.user_requests[user_id]
                if current_time - req_time < 60  # Keep requests from last minute
            ]
        else:
            self.user_requests[user_id] = []
        
        # Check rate limit
        if len(self.user_requests[user_id]) >= 10:  # 10 messages per minute
            await event.answer("⚠️ Слишком много сообщений. Подождите немного.")
            return
        
        # Add current request
        self.user_requests[user_id].append(current_time)
        
        return await handler(event, data)

class SubscriptionMiddleware(BaseMiddleware):
    """Middleware to check subscription status"""
    
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        session = data.get("session")
        user = data.get("user")
        
        if session and user:
            # Check if user is banned
            if user.subscription_plan == "banned":
                if isinstance(event, Message):
                    await event.answer("🚫 Ваш аккаунт заблокирован.")
                else:
                    await event.answer("🚫 Ваш аккаунт заблокирован.", show_alert=True)
                return
            
            # Update premium status
            has_premium = await UserService.has_premium_access(session, user.telegram_id)
            data["has_premium"] = has_premium

            # Уведомления о скором окончании премиума
            try:
                if has_premium and getattr(user, "subscription_expires_at", None):
                    now = datetime.utcnow()
                    expires_at = user.subscription_expires_at
                    remaining = expires_at - now
                    notify_days = {21, 14, 7, 3, 1}
                    # Отправляем уведомление раз в сутки на указанные дни
                    days_left = remaining.days
                    key = f"last_premium_notify_{user.telegram_id}"
                    # Простейший in-memory кэш на процесс (перезагрузке бота сбросится)
                    if not hasattr(self, "_notified"):  # type: ignore
                        self._notified = {}
                    last = self._notified.get(key)
                    if days_left in notify_days and last != days_left and remaining.total_seconds() > 0:
                        text = (
                            f"⏳ Ваш Premium истекает через {days_left} дн.\n"
                            f"🗓 До: {expires_at.strftime('%d.%m.%Y %H:%M')} MSK\n"
                            f"Продлите, чтобы сохранить доступ к про‑моделям и увеличенным лимитам."
                        )
                        # Сообщение только в приватных чатах-пользовательских событиях
                        if isinstance(event, Message):
                            await event.answer(text)
                        elif isinstance(event, CallbackQuery):
                            await event.message.answer(text)
                        self._notified[key] = days_left
                elif not has_premium and getattr(user, "subscription_expires_at", None) is None and user.subscription_plan == "free":
                    # В момент окончания можно уведомить один раз
                    key = f"ended_premium_notify_{user.telegram_id}"
                    if not hasattr(self, "_notified_ended"):  # type: ignore
                        self._notified_ended = {}
                    if not self._notified_ended.get(key):
                        end_text = "⚠️ Ваш Premium истёк. Доступ к про‑функциям приостановлен. Вы можете продлить подписку в /premium."
                        if isinstance(event, Message):
                            await event.answer(end_text)
                        elif isinstance(event, CallbackQuery):
                            await event.message.answer(end_text)
                        self._notified_ended[key] = True
            except Exception:
                # Не мешаем обработке даже при ошибках уведомлений
                pass
        
        return await handler(event, data)
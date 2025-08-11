from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from typing import Callable, Dict, Any, Awaitable
from database import async_session
from services.user_service import UserService
import time
import logging

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
        
        return await handler(event, data)
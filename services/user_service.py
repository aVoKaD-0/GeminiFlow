from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, update
from database.models import User, Chat, Message, Referral
from datetime import datetime, timedelta
from typing import Optional
import config
import uuid
from zoneinfo import ZoneInfo

class UserService:
    @staticmethod
    def _align_to_next_10_minute_boundary(dt_utc_naive: datetime) -> datetime:
        """Округляет время вверх до ближайшей границы 10 минут по Москве. Возвращает naive UTC."""
        utc = ZoneInfo("UTC")
        msk = ZoneInfo("Europe/Moscow")
        # делаем aware UTC
        dt_utc = dt_utc_naive.replace(tzinfo=utc)
        # переводим в МСК
        dt_msk = dt_utc.astimezone(msk)
        dt_msk = dt_msk.replace(second=0, microsecond=0)
        remainder = dt_msk.minute % 10
        if remainder != 0:
            dt_msk = dt_msk + timedelta(minutes=(10 - remainder))
        # обратно в UTC и возвращаем naive
        dt_utc_aligned = dt_msk.astimezone(utc)
        return dt_utc_aligned.replace(tzinfo=None)
    
    @staticmethod
    async def get_or_create_user(session: AsyncSession, telegram_id: int, username: str = None) -> User:
        """Get existing user or create new one"""
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            user = User(
                telegram_id=telegram_id,
                username=username,
                subscription_plan="free"
            )
            session.add(user)
            
            # Create default chat
            default_chat = Chat(
                user_id=telegram_id,
                title="Основной чат",
                model_name="gemini-1.5-flash"
            )
            session.add(default_chat)
            await session.flush()
            
            # Set current chat
            user.current_chat_id = default_chat.id
            # Trial Premium on registration, с выравниванием на ближайшие 10 минут
            if getattr(config, "TRIAL_PREMIUM_ENABLED", False) and getattr(config, "TRIAL_PREMIUM_DAYS", 0) > 0:
                base_end = datetime.utcnow() + timedelta(days=config.TRIAL_PREMIUM_DAYS)
                aligned_end = UserService._align_to_next_10_minute_boundary(base_end)
                user.subscription_plan = "pro"
                user.subscription_expires_at = aligned_end

            await session.commit()
        
        return user
    
    @staticmethod
    async def has_premium_access(session: AsyncSession, telegram_id: int) -> bool:
        """Check if user has premium access"""
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return False
        
        if user.subscription_plan == "banned":
            return False
        
        if user.subscription_plan == "free":
            return False
        
        if user.subscription_plan == "pro":
            if user.subscription_expires_at and user.subscription_expires_at > datetime.utcnow():
                return True
            else:
                # Expired subscription: жёстко обновляем в БД
                await session.execute(
                    update(User)
                    .where(User.telegram_id == telegram_id)
                    .values(subscription_plan="free", subscription_expires_at=None)
                )
                # Автодаунгрейд моделей чатов на бесплатную
                try:
                    free_models = getattr(config, "GEMINI_FREE_MODELS", ["gemini-1.5-flash"]) or ["gemini-1.5-flash"]
                    default_free_model = free_models[-1]
                    result_chats = await session.execute(select(Chat).where(Chat.user_id == telegram_id))
                    user_chats = result_chats.scalars().all()
                    for chat in user_chats:
                        if chat.model_name not in free_models:
                            chat.model_name = default_free_model
                except Exception:
                    # Не прерываем процесс, даже если обновление моделей не удалось
                    pass
                await session.commit()
        
        return False
    
    @staticmethod
    async def get_user_chat_count(session: AsyncSession, telegram_id: int) -> int:
        """Get number of chats for user"""
        result = await session.execute(
            select(func.count(Chat.id)).where(Chat.user_id == telegram_id)
        )
        return result.scalar() or 0
    
    @staticmethod
    async def can_create_chat(session: AsyncSession, telegram_id: int) -> bool:
        """Check if user can create another chat"""
        has_premium = await UserService.has_premium_access(session, telegram_id)
        chat_count = await UserService.get_user_chat_count(session, telegram_id)
        
        limit = config.PREMIUM_CHAT_LIMIT if has_premium else config.FREE_CHAT_LIMIT
        return chat_count < limit
    
    @staticmethod
    async def get_current_chat(session: AsyncSession, telegram_id: int) -> Optional[Chat]:
        """Get user's current active chat"""
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        
        if not user or not user.current_chat_id:
            return None
        
        result = await session.execute(
            select(Chat).where(
                and_(Chat.id == user.current_chat_id, Chat.user_id == telegram_id)
            )
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def set_current_chat(session: AsyncSession, telegram_id: int, chat_id: uuid.uuid4):
        """Set user's current active chat"""
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        
        if user:
            user.current_chat_id = chat_id
            await session.commit()
    
    @staticmethod
    async def grant_premium(session: AsyncSession, telegram_id: int, days: int):
        """Grant premium access to user"""
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        
        if user:
            base_end = datetime.utcnow() + timedelta(days=days)
            aligned_end = UserService._align_to_next_10_minute_boundary(base_end)
            user.subscription_plan = "pro"
            user.subscription_expires_at = aligned_end
            await session.commit()
    
    @staticmethod
    async def process_referral(session: AsyncSession, referrer_id: int, referred_id: int) -> bool:
        """Process referral registration"""
        # Check if referral already exists
        result = await session.execute(
            select(Referral).where(Referral.referred_id == referred_id)
        )
        if result.scalar_one_or_none():
            return False  # Already referred
        
        # Create referral
        referral = Referral(referrer_id=referrer_id, referred_id=referred_id)
        session.add(referral)
        
        # Check if referrer reached target
        result = await session.execute(
            select(func.count(Referral.id)).where(Referral.referrer_id == referrer_id)
        )
        referral_count = result.scalar() or 0
        
        if referral_count >= config.REFERRAL_TARGET_COUNT:
            # Grant reward
            result = await session.execute(
                select(User).where(User.telegram_id == referrer_id)
            )
            referrer = result.scalar_one_or_none()
            
            if referrer and not referrer.reward_claimed:
                referrer.reward_claimed = True
                await UserService.grant_premium(session, referrer_id, config.REFERRAL_REWARD_DAYS)
        
        await session.commit()
        return True
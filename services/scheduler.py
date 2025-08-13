from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select, update
from database import async_session
from database.models import User, Chat
import config

_scheduler: AsyncIOScheduler | None = None


async def _expire_premiums_job() -> None:
    """Понижает статус и модели у пользователей с истёкшим Premium."""
    now = datetime.utcnow()
    async with async_session() as session:
        # Найти всех с истёкшим премиумом
        result = await session.execute(
            select(User.telegram_id).where(
                User.subscription_plan == "pro",
                User.subscription_expires_at.is_not(None),
                User.subscription_expires_at <= now,
            )
        )
        user_ids = [row[0] for row in result.fetchall()]
        if not user_ids:
            return

        # Перевести пользователей на free
        await session.execute(
            update(User)
            .where(User.telegram_id.in_(user_ids))
            .values(subscription_plan="free", subscription_expires_at=None)
        )

        # Перевести модели чатов на бесплатную
        free_models = getattr(config, "GEMINI_FREE_MODELS", ["gemini-1.5-flash"]) or ["gemini-1.5-flash"]
        default_free_model = free_models[-1]
        result_chats = await session.execute(select(Chat).where(Chat.user_id.in_(user_ids)))
        chats = result_chats.scalars().all()
        for chat in chats:
            if chat.model_name not in free_models:
                chat.model_name = default_free_model

        await session.commit()


def start_scheduler() -> None:
    """Запускает планировщик задач (каждые 10 минут, по границе 10 минут)."""
    global _scheduler
    if _scheduler is not None:
        return
    _scheduler = AsyncIOScheduler(timezone="UTC")
    # Каждые 10 минут на границах: */10
    _scheduler.add_job(_expire_premiums_job, CronTrigger(minute="*/10"))
    _scheduler.start()


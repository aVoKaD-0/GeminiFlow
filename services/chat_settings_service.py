# services/chat_settings_service.py
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from database.models import Chat, Settings
from typing import List, Dict, Any, Optional
import json
import uuid

logger = logging.getLogger(__name__)

class ChatSettingsService:
    @staticmethod
    async def get_available_models(session: AsyncSession, is_premium: bool) -> List[str]:
        """
        Получает список доступных моделей из таблицы settings.
        """
        key = "available_models_premium" if is_premium else "available_models_free"
        try:
            result = await session.execute(select(Settings.value).where(Settings.key == key))
            value = result.scalar_one_or_none()
            if value:
                return json.loads(value)
        except Exception as e:
            logger.error(f"Ошибка при получении доступных моделей ({key}): {e}")
            # Возврат значения по умолчанию на случай ошибки
            return ["gemini-1.5-flash"] if not is_premium else ["gemini-1.5-pro", "gemini-1.5-flash"]
        return ["gemini-1.5-flash"] if not is_premium else ["gemini-1.5-pro", "gemini-1.5-flash"]

    @staticmethod
    async def get_chat_info(session: AsyncSession, chat_id: uuid.uuid4, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает информацию о чате и его настройках.
        """
        try:
            result = await session.execute(
                select(Chat).where(Chat.id == chat_id, Chat.user_id == user_id)
            )
            chat = result.scalar_one_or_none()
            if not chat:
                return None

            # Подсчет сообщений в чате (пример, если есть таблица messages)
            # from database.models import Message
            # msg_count_result = await session.execute(select(func.count(Message.id)).where(Message.chat_id == chat.id))
            # message_count = msg_count_result.scalar() or 0

            return {
                "id": chat.id,
                "title": chat.title,
                "model_name": chat.model_name,
                "temperature": chat.temperature,
                "top_p": chat.top_p,
                "top_k": chat.top_k,
                "system_prompt": chat.system_prompt or "",
                # "message_count": message_count # Добавить, если нужно
            }
        except Exception as e:
            logger.error(f"Ошибка при получении информации о чате {chat_id}: {e}")
            return None

    @staticmethod
    async def update_chat_model(session: AsyncSession, chat_id: uuid.uuid4, user_id: int, model_name: str) -> bool:
        """Обновляет модель чата."""
        try:
            stmt = update(Chat).where(Chat.id == chat_id, Chat.user_id == user_id).values(model_name=model_name)
            await session.execute(stmt)
            await session.commit()
            return True
        except Exception as e:
            await session.rollback()
            logger.error(f"Ошибка при обновлении модели чата {chat_id}: {e}")
            return False

    @staticmethod
    async def update_chat_temperature(session: AsyncSession, chat_id: uuid.uuid4, user_id: int, temperature: float) -> bool:
        """Обновляет температуру чата."""
        try:
            # Валидация температуры
            if not (0.0 <= temperature <= 2.0):
                 return False
            stmt = update(Chat).where(Chat.id == chat_id, Chat.user_id == user_id).values(temperature=temperature)
            await session.execute(stmt)
            await session.commit()
            return True
        except Exception as e:
            await session.rollback()
            logger.error(f"Ошибка при обновлении температуры чата {chat_id}: {e}")
            return False

    @staticmethod
    async def update_chat_advanced(session: AsyncSession, chat_id: uuid.uuid4, user_id: int, top_p: Optional[float], top_k: Optional[int]) -> bool:
        """Обновляет продвинутые настройки чата (Top-P, Top-K)."""
        try:
             # Валидация Top-P
            if top_p is not None and not (0.0 <= top_p <= 1.0):
                 return False
            # Валидация Top-K (обычно положительное целое)
            if top_k is not None and top_k <= 0:
                 return False

            stmt = update(Chat).where(Chat.id == chat_id, Chat.user_id == user_id).values(top_p=top_p, top_k=top_k)
            await session.execute(stmt)
            await session.commit()
            return True
        except Exception as e:
            await session.rollback()
            logger.error(f"Ошибка при обновлении продвинутых настроек чата {chat_id}: {e}")
            return False

    @staticmethod
    async def update_chat_system_prompt(session: AsyncSession, chat_id: uuid.uuid4, user_id: int, system_prompt: str) -> bool:
        """Обновляет системный промпт (личность) чата."""
        try:
            stmt = update(Chat).where(Chat.id == chat_id, Chat.user_id == user_id).values(system_prompt=system_prompt)
            await session.execute(stmt)
            await session.commit()
            return True
        except Exception as e:
            await session.rollback()
            logger.error(f"Ошибка при обновлении системного промпта чата {chat_id}: {e}")
            return False

# Экземпляр сервиса
chat_settings_service = ChatSettingsService()
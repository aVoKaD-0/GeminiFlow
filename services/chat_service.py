from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from database.models import Chat, Message
from typing import List, Optional, Dict
import uuid

class ChatService:
    @staticmethod
    async def get_user_chats(session: AsyncSession, telegram_id: int) -> List[Chat]:
        """Get all user chats"""
        result = await session.execute(
            select(Chat)
            .where(Chat.user_id == telegram_id)
            .order_by(desc(Chat.created_at))
        )
        return result.scalars().all()
    
    @staticmethod
    async def create_chat(session: AsyncSession, telegram_id: int, title: str, model_name: str) -> Chat:
        """Create new chat"""
        chat = Chat(
            user_id=telegram_id,
            title=title,
            model_name=model_name
        )
        session.add(chat)
        await session.flush()
        await session.commit()
        return chat
    
    @staticmethod
    async def get_chat(session: AsyncSession, chat_id: uuid.uuid4, telegram_id: int) -> Optional[Chat]:
        """Get specific chat by ID"""
        result = await session.execute(
            select(Chat).where(
                and_(Chat.id == chat_id, Chat.user_id == telegram_id)
            )
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def delete_chat(session: AsyncSession, chat_id: uuid.uuid4, telegram_id: int) -> bool:
        """Delete chat"""
        result = await session.execute(
            select(Chat).where(
                and_(Chat.id == chat_id, Chat.user_id == telegram_id)
            )
        )
        chat = result.scalar_one_or_none()
        
        if chat:
            await session.delete(chat)
            await session.commit()
            return True
        return False
    
    @staticmethod
    async def rename_chat(session: AsyncSession, chat_id: uuid.uuid4, telegram_id: int, new_title: str) -> bool:
        """Rename chat"""
        result = await session.execute(
            select(Chat).where(
                and_(Chat.id == chat_id, Chat.user_id == telegram_id)
            )
        )
        chat = result.scalar_one_or_none()
        
        if chat:
            chat.title = new_title
            await session.commit()
            return True
        return False
    
    @staticmethod
    async def add_message(session: AsyncSession, chat_id: uuid.uuid4, user_id: int, role: str, content: str) -> Message:
        """Add message to chat"""
        message = Message(
            user_id=user_id,
            chat_id=chat_id,
            role=role,
            content=content
        )
        session.add(message)
        await session.flush()
        await session.commit()
        return message
    
    @staticmethod
    async def get_chat_messages(session: AsyncSession, chat_id: uuid.uuid4, limit: int = 50) -> List[Dict[str, str]]:
        """Get chat messages in format for Gemini"""
        result = await session.execute(
            select(Message)
            .where(Message.chat_id == chat_id)
            .order_by(Message.created_at)
            .limit(limit)
        )
        messages = result.scalars().all()
        
        return [
            {
                "role": msg.role,
                "content": msg.content
            }
            for msg in messages
        ]
        
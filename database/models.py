from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime, Numeric, ForeignKey, Float, JSON, UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    telegram_id = Column(BigInteger, primary_key=True)
    username = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now())
    api_key_encrypted = Column(String, nullable=True)
    subscription_plan = Column(String, default="free")  # free, pro, banned
    subscription_expires_at = Column(DateTime, nullable=True)
    is_admin = Column(Boolean, default=False)
    reward_claimed = Column(Boolean, default=False)
    current_chat_id = Column(UUID, nullable=True)
    
    # Relationships
    chats = relationship("Chat", back_populates="user", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="user", cascade="all, delete-orphan")
    # Пользователь пригласил других (referrer_id в Referral указывает на этого User)
    made_referrals = relationship("Referral", foreign_keys="[Referral.referrer_id]", back_populates="referrer") # Имя "made_referrals" для ясности
    # Пользователь был приглашен (referred_id в Referral указывает на этого User)
    received_referrals = relationship("Referral", foreign_keys="[Referral.referred_id]", back_populates="referred") # Имя "received_referrals" для ясности
    # Удалено referred_by, так как оно дублировало received_referrals / referrals

class Chat(Base):
    __tablename__ = "chats"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    user_id = Column(BigInteger, ForeignKey('users.telegram_id'), nullable=False)
    created_at = Column(DateTime, default=func.now())
    is_active = Column(Boolean, default=True)

    # --- Новые поля для настроек ---
    model_name = Column(String, default="gemini-1.5-flash")
    temperature = Column(Float, default=1.0)
    top_p = Column(Float, nullable=True)
    top_k = Column(Integer, nullable=True)
    system_prompt = Column(Text, default="", nullable=True)

    # --- Отношения ---
    user = relationship("User", back_populates="chats")
    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Chat(id='{self.id}', title='{self.title}', user_id={self.user_id})>"

class Message(Base):
    __tablename__ = "messages"

    id = Column(BigInteger, primary_key=True, autoincrement=True) # Или BigInteger, как в коде из Pasted_Text
    user_id = Column(BigInteger, ForeignKey('users.telegram_id'), nullable=False) # <-- Ключевая строка
    chat_id = Column(UUID, ForeignKey('chats.id'), nullable=False) # Пример другой FK
    role = Column(String, nullable=False) # 'user' или 'model'
    content = Column(Text, nullable=False)
    tokens_used = Column(Integer, default=0) # Пример
    created_at = Column(DateTime, default=func.now())

    # Отношения (если нужно)
    user = relationship("User", back_populates="messages")
    chat = relationship("Chat", back_populates="messages")
class Referral(Base):
    __tablename__ = "referrals"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    referrer_id = Column(BigInteger, ForeignKey("users.telegram_id"))
    referred_id = Column(BigInteger, ForeignKey("users.telegram_id"), unique=True)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    # Пользователь, который пригласил (referrer_id ссылается на его telegram_id)
    referrer = relationship("User", foreign_keys=[referrer_id], back_populates="made_referrals") # Ссылка на made_referrals
    # Пользователь, которого пригласили (referred_id ссылается на его telegram_id)
    referred = relationship("User", foreign_keys=[referred_id], back_populates="received_referrals") # Ссылка на received_referrals

class Settings(Base):
    __tablename__ = "settings"

    key = Column(String, primary_key=True)
    value = Column(String) # Или Text, если значения могут быть большими
    description = Column(Text, nullable=True) # Описание настройки (опционально)

    def __repr__(self):
        return f"<Setting(key='{self.key}', value='{self.value}')>"

class SubscriptionProduct(Base):
    __tablename__ = "subscription_products"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)
    duration_days = Column(Integer)
    price_stars = Column(Integer)
    price_external = Column(Numeric(10, 2))
    currency = Column(String(3), default="USD")
    is_active = Column(Boolean, default=True)

class GeminiLimit(Base):
    __tablename__ = "gemini_limits"
    
    model_name = Column(String, primary_key=True)
    requests_per_minute = Column(Integer)
    requests_per_day = Column(Integer)
    tokens_per_minute = Column(Integer)
    last_updated = Column(DateTime, default=func.now())
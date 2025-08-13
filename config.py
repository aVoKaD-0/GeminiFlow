import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(","))) if os.getenv("ADMIN_IDS") else []

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/gemini_flow")

# Redis Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# Encryption
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

# Gemini Configuration
GEMINI_FREE_MODELS = ["gemini-1.5-flash-lite", "gemini-1.5-flash", "gemini-2.0-flash-lite", "gemini-2.0-flash", "gemini-2.5-flash-lite", "gemini-2.5-flash"]
GEMINI_PRO_MODELS = ["gemini-1.5-flash-lite", "gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash-lite", "gemini-2.0-flash", "gemini-2.0-pro", "gemini-2.5-flash-lite", "gemini-2.5-flash", "gemini-2.5-pro"]

# Subscription Configuration
FREE_CHAT_LIMIT = 1
PREMIUM_CHAT_LIMIT = 10

# File size limits (in megabytes)
FILE_SIZE_LIMIT_FREE_MB = int(os.getenv("FILE_SIZE_LIMIT_FREE_MB", "10"))
FILE_SIZE_LIMIT_PREMIUM_MB = int(os.getenv("FILE_SIZE_LIMIT_PREMIUM_MB", "20"))

# Context Management
MAX_CONTEXT_TOKENS = 20000
CONTEXT_SUMMARY_RATIO = 0.7

# Rate Limiting
USER_MESSAGE_RATE_LIMIT = 10  # messages per minute

# Referral System
REFERRAL_TARGET_COUNT = 5
REFERRAL_REWARD_DAYS = 5

# Trial Premium
TRIAL_PREMIUM_ENABLED = os.getenv("TRIAL_PREMIUM_ENABLED", "true").lower() == "true"
TRIAL_PREMIUM_DAYS = int(os.getenv("TRIAL_PREMIUM_DAYS", "2"))

# Premium plans (Telegram Stars)
PREMIUM_PLANS = {
    "1": {"name": "Premium на 1 месяц", "days": 30, "stars": 50},
    "3": {"name": "Premium на 3 месяца", "days": 90, "stars": 100},
    "6": {"name": "Premium на 6 месяцев", "days": 180, "stars": 250},
    "12": {"name": "Premium на 1 год", "days": 365, "stars": 500},
}
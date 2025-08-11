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
GEMINI_FREE_MODELS = ["gemini-1.5-flash"]
GEMINI_PRO_MODELS = ["gemini-1.5-pro", "gemini-1.5-flash"]

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
REFERRAL_REWARD_DAYS = 30
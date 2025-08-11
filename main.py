import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand, BotCommandScopeAllPrivateChats, BotCommandScopeDefault, BotCommandScopeChat
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
import redis.asyncio as redis

import config
from database import init_db
from middlewares import DatabaseMiddleware, UserMiddleware, RateLimitMiddleware, SubscriptionMiddleware

# Import handlers
from handlers import chat_settings, start, api_key, chat, premium, admin, main as main_handler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s - %(lineno)d - %(message)s',
    handlers=[
        logging.FileHandler('logs/bot.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

async def set_main_menu_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="🚀 Главное меню / Перезапустить"),
        BotCommand(command="api_key", description="🔑 Получить API ключ"),
        BotCommand(command="premium", description="💎 Подписка"),
        BotCommand(command="admin", description="👑 Админ панель"),
        BotCommand(command="chats", description="💬 Чаты"),  
    ]

    # 1) Сносим default и all_private
    await bot.delete_my_commands(scope=BotCommandScopeDefault())
    await bot.delete_my_commands(scope=BotCommandScopeAllPrivateChats())

    # 2) Сносим старые chat-скоупы для админов
    for admin_id in getattr(config, "ADMIN_IDS", []):
        try:
            await bot.delete_my_commands(scope=BotCommandScopeChat(chat_id=int(admin_id)))
        except Exception as e:
            logger.warning(f"Не удалось удалить chat-scope для {admin_id}: {e}")

    # 3) Выставляем новые команды
    await bot.set_my_commands(commands, scope=BotCommandScopeAllPrivateChats())
    await bot.set_my_commands(commands, scope=BotCommandScopeDefault())

async def main():
    # Validate configuration
    if not config.BOT_TOKEN:
        raise ValueError("BOT_TOKEN не установлен")
    if not config.ENCRYPTION_KEY:
        raise ValueError("ENCRYPTION_KEY не установлен")
    
    # Initialize database
    await init_db()
    logger.info("Database initialized")
    
    # Initialize Redis storage for FSM
    redis_client = redis.from_url(config.REDIS_URL)
    storage = RedisStorage(redis_client)
    
    # Initialize bot and dispatcher
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    dp = Dispatcher(storage=storage)
    
    # Register middlewares
    dp.message.middleware(DatabaseMiddleware())
    dp.callback_query.middleware(DatabaseMiddleware())
    
    dp.message.middleware(UserMiddleware())
    dp.callback_query.middleware(UserMiddleware())
    
    dp.message.middleware(RateLimitMiddleware())
    
    dp.message.middleware(SubscriptionMiddleware())
    dp.callback_query.middleware(SubscriptionMiddleware())
    
    # Register handlers
    dp.include_router(start.router)
    dp.include_router(api_key.router)
    dp.include_router(premium.router)
    dp.include_router(admin.router)
    dp.include_router(main_handler.router)
    dp.include_router(chat_settings.router)
    dp.include_router(chat.router)
    # Set main menu commands
    await set_main_menu_commands(bot)
    
    # Start polling
    logger.info("Starting bot...")
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Bot stopped with error: {e}")
    finally:
        await bot.session.close()
        await redis_client.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise
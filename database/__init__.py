from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from database.models import Base
import config

# Create async engine
engine = create_async_engine(
    config.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    echo=False
)

# Create session factory
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def init_db():
    """Initialize database tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_session():
    """Get database session"""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.core.config import settings

# Create the async database engine
engine = create_async_engine(
    settings.database_url,
    echo=settings.app_debug,  # logs SQL queries when debug=True
)

# Session factory - creates database sessions
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Base class for all our models
class Base(DeclarativeBase):
    pass

# Dependency for FastAPI - gives each request its own session
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
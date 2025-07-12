from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel
from typing import AsyncGenerator

from app.core.config import settings


def create_database_engine() -> AsyncEngine:
    """Create optimized database engine"""
    return create_async_engine(
        settings.database_url,
        echo=False,
        future=True,
        pool_size=settings.pool_size,
        max_overflow=settings.max_overflow,
        pool_pre_ping=True,
        pool_recycle=3600,
        connect_args={
            "command_timeout": settings.request_timeout,
            "server_settings": {
                "application_name": "rinha_backend_2025",
                "jit": "off",
            },
        },
    )


engine = create_database_engine()


async def init_db() -> None:
    """Initialize database tables"""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

async_session = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session"""
    async with async_session() as session:
        yield session
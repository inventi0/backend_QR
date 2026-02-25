import os
from typing import Any, Generator

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.declarative import declarative_base

load_dotenv()

DATABASE_URL: Any = os.getenv("DATABASE")
DEBUG = str(os.getenv("DEBUG", "false")).lower() in ("1", "true", "yes")

# ✅ echo=True только в DEBUG mode
engine = create_async_engine(
    DATABASE_URL,
    echo=DEBUG,
    future=True,
    pool_pre_ping=True,
    pool_size=10,  # ✅ Настроен connection pool
    max_overflow=20,
)
async_session = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)
Base = declarative_base()


async def get_db() -> Generator:
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()

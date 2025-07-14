import os

from dotenv import load_dotenv
from sqlalchemy import select
from fastapi import UploadFile, HTTPException
from passlib.context import CryptContext

from app.database import Base, engine, async_session
from app.models.models import User

load_dotenv()


async def to_start():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


async def create_admin():
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.is_superuser == True)
        )
        admin = result.scalars().first()
        if not admin:
            admin = User(
                email="admin@example.com",
                username="admin",
                hashed_password=get_password_hash(os.getenv("ADMIN_PASSWORD")),
                is_superuser=True,
                is_active=True,
                is_verified=True,
            )
            session.add(admin)
            await session.commit()


async def to_shutdown():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


def is_admin(user: User):
    if not user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized as admin")
    return user

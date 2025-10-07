import os
from typing import Optional

from dotenv import load_dotenv
from sqlalchemy import select
from fastapi import HTTPException
from passlib.context import CryptContext

from app.database import Base, engine, async_session
from app.models.models import User, Product
from app.s3.s3 import S3Client
from app.helpers.codegen import ensure_user_editor_and_qr

load_dotenv()

async def to_start():
    """Создать все таблицы (если не используете Alembic)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def to_shutdown():
    """Дропнуть все таблицы (для локальных стендов)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def _build_s3_client_if_possible() -> Optional[S3Client]:
    """
    Собираем S3Client, если заданы переменные окружения.
    Иначе вернём None — генерация PNG для QR будет пропущена, но Editor+QR создадутся.
    """
    access_key = os.getenv("S3_ACCESS_KEY")
    secret_key = os.getenv("S3_SECRET_KEY")
    endpoint_url = os.getenv("S3_ENDPOINT_URL")
    bucket_name = os.getenv("S3_BUCKET_NAME")

    if not (access_key and secret_key and endpoint_url and bucket_name):
        return None

    return S3Client(
        access_key=access_key,
        secret_key=secret_key,
        endpoint_url=endpoint_url,
        bucket_name=bucket_name,
    )


async def create_admin():
    """
    Идемпотентно создаёт суперпользователя и гарантирует ему Editor+QR (+PNG в S3, если S3 настроен).
    """
    admin_password = os.getenv("ADMIN_PASSWORD")
    if not admin_password:
        raise RuntimeError("ENV ADMIN_PASSWORD is required to create admin")

    async with async_session() as session:
        result = await session.execute(select(User).where(User.is_superuser.is_(True)))
        admin = result.scalars().first()

        if not admin:
            admin = User(
                email="admin@example.com",
                username="admin",
                hashed_password=get_password_hash(admin_password),
                is_superuser=True,
                is_active=True,
                is_verified=True,
                role_id=1,
            )
            session.add(admin)
            await session.commit()

        s3_client = _build_s3_client_if_possible()
        await ensure_user_editor_and_qr(session, s3_client, admin)


async def create_product():
    async with async_session() as session:
        result = await session.execute(
            select(Product).where(
                Product.type == "Футболка",
                Product.size == "M",
                Product.color == "Белый",
            )
        )
        product = result.scalars().first()
        if not product:
            product = Product(
                type="Футболка",
                size="M",
                color="Белый",
                description="Базовая белая футболка размера M",
                img_url=os.getenv("SEED_PRODUCT_IMG_URL") or None,
            )
            session.add(product)
            await session.commit()

def is_admin(user: User) -> User:
    """Проверка прав администратора для handler'ов/сервисов."""
    if not user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized as admin")
    return user

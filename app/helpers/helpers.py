import os
import uuid
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from sqlalchemy import select
from fastapi import HTTPException
from passlib.context import CryptContext

from app.database import Base, engine, async_session
from app.models.models import User, Product, Review
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
    Идемпотентно создаёт суперпользователя и гарантирует ему Editor+QR
    (+PNG в S3, если S3 настроен).
    """
    admin_email = os.getenv("ADMIN_EMAIL", "admin@example.com")
    admin_username = os.getenv("ADMIN_USERNAME", "admin")
    admin_password = os.getenv("ADMIN_PASSWORD")
    if not admin_password:
        raise RuntimeError("ENV ADMIN_PASSWORD is required to create admin")

    async with async_session() as session:
        result = await session.execute(select(User).where(User.is_superuser.is_(True)))
        admin = result.scalars().first()

        if not admin:
            admin = User(
                email=admin_email,
                username=admin_username,
                hashed_password=get_password_hash(admin_password),
                is_superuser=True,
                is_active=True,
                is_verified=True,
                role_id=1,
            )
            session.add(admin)
            await session.commit()
            await session.refresh(admin)

        s3_client = _build_s3_client_if_possible()
        await ensure_user_editor_and_qr(session, s3_client, admin)

async def create_product():
    """
    Идемпотентный сидер продукта.
    ENV (не обязательно):
      SEED_PRODUCT_TYPE="Футболка"
      SEED_PRODUCT_SIZE="M"
      SEED_PRODUCT_COLOR="Белый"
      SEED_PRODUCT_DESC="Базовая белая футболка размера M"
      SEED_PRODUCT_PRICE="1500"   # новая переменная
      SEED_PRODUCT_IMG_PATH="/abs/path/to/local/image.png"  # если хотим залить в S3
      SEED_PRODUCT_IMG_URL="https://..."                    # либо готовый URL
    """
    p_type = os.getenv("SEED_PRODUCT_TYPE", "Футболка")
    p_size = os.getenv("SEED_PRODUCT_SIZE", "M")
    p_color = os.getenv("SEED_PRODUCT_COLOR", "Белый")
    p_desc = os.getenv("SEED_PRODUCT_DESC", "Базовая белая футболка размера M")
    p_price = int(os.getenv("SEED_PRODUCT_PRICE", "1000"))  # <--- добавлено

    img_path_env = os.getenv("SEED_PRODUCT_IMG_PATH")
    img_url_env = os.getenv("SEED_PRODUCT_IMG_URL")

    async with async_session() as session:
        result = await session.execute(
            select(Product).where(
                Product.type == p_type,
                Product.size == p_size,
                Product.color == p_color,
            )
        )
        product = result.scalars().first()
        if product:
            # если уже есть — просто обновляем цену (идемпотентно)
            if product.price != p_price:
                product.price = p_price
                await session.commit()
                await session.refresh(product)
            return product

        # создаём новый продукт
        product = Product(
            type=p_type,
            size=p_size,
            color=p_color,
            description=p_desc,
            price=p_price,  # <--- новое поле
        )
        session.add(product)
        await session.flush()

        final_img_url = None
        s3_client = _build_s3_client_if_possible()

        if img_path_env and s3_client:
            p = Path(img_path_env)
            if p.exists() and p.is_file():
                object_key = f"products/{product.id}/{uuid.uuid4().hex[:8]}_{p.name}"
                await s3_client.upload_file(str(p), object_key)
                s3_public = os.getenv(
                    "S3_PUBLIC_BASE",
                    "https://3e06ba26-08cc-45a0-99f2-455006fbe542.selstorage.ru",
                ).rstrip("/")
                final_img_url = f"{s3_public}/{object_key}"

        if not final_img_url and img_url_env:
            final_img_url = img_url_env

        product.img_url = final_img_url
        await session.commit()
        await session.refresh(product)
        return product


def is_admin(user: User) -> User:
    """Проверка прав администратора для handler'ов/сервисов."""
    if not user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized as admin")
    return user

async def create_mock_reviews():
    """Создаёт тестовые отзывы при запуске сервера для проверок авто-модерации"""
    from app.helpers.moderation import check_bad_words
    
    async with async_session() as session:
        # Check if reviews exist
        result = await session.execute(select(Review))
        existing_reviews = result.scalars().all()
        
        if not existing_reviews:
            # Get admin user ID to attach reviews to
            admin_req = await session.execute(select(User).where(User.is_superuser.is_(True)))
            admin = admin_req.scalars().first()
            if not admin:
                return # Can't create reviews without a user
                
            mock_reviews = [
                "Отличный сервис, мне всё очень понравилось! Буду рекомендовать друзьям.",
                "Полный отстой, это просто кошмар и какой-то scam, верните деньги.",
                "Неплохо, но интерфейс сложный. А так всё работает."
            ]
            
            for content in mock_reviews:
                is_flagged = await check_bad_words(session, content)
                r = Review(stars=4, content=content, user_id=admin.id, is_flagged=is_flagged)
                session.add(r)
                
            await session.commit()

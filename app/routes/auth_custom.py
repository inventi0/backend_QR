import os
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.routes.dependecies import current_user
from app.s3.s3 import S3Client
from app.schemas.user_schemas import UserRead, UserCreate
from app.models.models import User
from app.helpers.users import set_user_avatar
from app.auth.manager import get_user_manager
from fastapi_users import models as fu_models

auth_custom_router = APIRouter(prefix="/auth", tags=["auth"])

def _s3_or_500() -> S3Client:
    access_key = os.getenv("S3_ACCESS_KEY")
    secret_key = os.getenv("S3_SECRET_KEY")
    endpoint_url = os.getenv("S3_ENDPOINT_URL")
    bucket_name = os.getenv("S3_BUCKET_NAME")
    if not all([access_key, secret_key, endpoint_url, bucket_name]):
        raise HTTPException(status_code=500, detail="S3 is not configured")
    return S3Client(
        access_key=access_key,
        secret_key=secret_key,
        endpoint_url=endpoint_url,
        bucket_name=bucket_name,
    )

@auth_custom_router.post("/register", response_model=UserRead)
async def register_with_avatar(
    email: EmailStr = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    avatar: UploadFile = File(...),
    user_manager = Depends(get_user_manager),
    db: AsyncSession = Depends(get_db),
):
    """
    Регистрация с обязательным аватаром (multipart/form-data).
    Создаёт пользователя через UserManager.create (что запустит on_after_register → Editor+QR),
    затем загружает файл в S3 и проставляет user.img_url.
    """
    user_create = UserCreate(email=email, username=username, password=password)
    created_user: fu_models.UP = await user_manager.create(user_create, safe=False)

    session = getattr(user_manager.user_db, "session", db)

    s3 = _s3_or_500()
    await set_user_avatar(session, s3, created_user, avatar)

    return created_user


profile_router = APIRouter(prefix="/users", tags=["users"])

@profile_router.patch("/me", response_model=UserRead)
async def update_me(
    username: str | None = Form(default=None),
    avatar: UploadFile | None = File(default=None),
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Обновить профиль: username (опционально) и/или аватар (опционально).
    """
    if username is not None:
        user.username = username

    if avatar is not None:
        s3 = _s3_or_500()
        await set_user_avatar(db, s3, user, avatar)
    else:
        await db.commit()
        await db.refresh(user)

    return user

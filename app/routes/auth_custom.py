import os
import random
import string
import uuid
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import EmailStr, BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from app.database import get_db
from app.routes.dependecies import current_user, current_superuser
from app.s3.s3 import S3Client
from app.schemas.user_schemas import UserRead, UserCreate, AdminUserDetailedResponse
from app.models.models import User, Editor, Template
from app.helpers.users import set_user_avatar
from app.helpers.codegen import ensure_user_editor_and_qr, _editor_url, set_editor_current_template
from app.auth.manager import get_user_manager
from fastapi_users import models as fu_models
from app.error.handler import handle_error
from app.logging_config import app_logger

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
    base_url: Optional[str] = Form(None),
    user_manager = Depends(get_user_manager),
    db: AsyncSession = Depends(get_db),
):
    """
    Регистрация с обязательным аватаром (multipart/form-data).
    Создаёт пользователя через UserManager.create (что запустит on_after_register → Editor+QR),
    затем загружает файл в S3 и проставляет user.img_url.
    """
    user_create = UserCreate(email=email, username=username, password=password)
    created_user: fu_models.UP = await user_manager.create(user_create, safe=False, base_url=base_url)

    session = getattr(user_manager.user_db, "session", db)

    s3 = _s3_or_500()
    await set_user_avatar(session, s3, created_user, avatar)

    return created_user
    return created_user


class GeneratedUserCredentials(BaseModel):
    id: int
    email: str
    username: str
    password: str
    qr_image_url: Optional[str] = None
    editor_url: Optional[str] = None


@auth_custom_router.post("/generate-random", response_model=GeneratedUserCredentials)
async def generate_random_user(
    base_url: Optional[str] = None,
    user_manager = Depends(get_user_manager),
    superuser: User = Depends(current_superuser),
    db: AsyncSession = Depends(get_db),
):
    """
    Генерация рандомного пользователя (для раздачи на бумажках).
    Только для суперюзеров (админов).
    Возвращает логин, пароль и ссылку на QR.
    """
    # 1. Generate random credentials
    # Password: 8 chars (letters + digits)
    alphabet = string.ascii_letters + string.digits
    password = ''.join(random.choice(alphabet) for _ in range(8))
    
    # Username/Email: random UUID part
    uid = uuid.uuid4().hex[:8]
    username = f"user_{uid}"
    email = f"{username}@example.com"
    
    # 2. Create User
    user_create = UserCreate(email=email, username=username, password=password)
    # We pass base_url so QR code is generated with correct link immediately
    created_user = await user_manager.create(
        user_create, 
        safe=False, 
        base_url=base_url,
        is_temporary_data=True  # ✅ Flag as temporary
    )
    
    # 3. Ensure QR and Editor exist (double check, though create() calls on_after_register)
    session = getattr(user_manager.user_db, "session", db)
    s3 = _s3_or_500()
    
    # We call this to get the QR object explicitly to return the link
    # The QR should already be created by on_after_register
    # But we need the object to return the link
    editor, qr, target_url = await ensure_user_editor_and_qr(session, s3, created_user, base_url=base_url)
    
    return GeneratedUserCredentials(
        id=created_user.id,
        email=email,
        username=username,
        password=password,
        qr_image_url=qr.link,
        editor_url=_editor_url(editor.public_id, base_url)
    )



profile_router = APIRouter(prefix="/users", tags=["users"])

@profile_router.patch("/me/avatar", response_model=UserRead)
async def update_avatar(
    avatar: UploadFile = File(...),
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Обновить аватар пользователя.
    """
    s3 = _s3_or_500()
    await set_user_avatar(db, s3, user, avatar)
    return user


@profile_router.get("/admin/detailed", response_model=list[AdminUserDetailedResponse])
async def get_all_users_detailed(
    skip: int = 0,
    limit: int = 100,
    user: User = Depends(current_superuser),
    db: AsyncSession = Depends(get_db),
):
    """
    Эндпоинт для админки — отдает полные данные всех пользователей, 
    с их шаблонами (templates) и ссылкой на QR-код (qr).
    """
    try:
        from sqlalchemy.orm import selectinload
        
        result = await db.execute(
            select(User)
            .options(selectinload(User.templates))
            .options(selectinload(User.qr))
            .options(selectinload(User.editor))
            .order_by(User.id.desc())
            .offset(skip).limit(limit)
        )
        users = result.scalars().all()
        
        response_data = []
        for u in users:
            response_data.append(AdminUserDetailedResponse(
                id=u.id,
                email=u.email,
                username=u.username,
                is_active=u.is_active,
                is_superuser=u.is_superuser,
                is_temporary_data=u.is_temporary_data,
                active_template_id=u.editor.current_template_id if u.editor else None,
                templates=[
                    {"id": t.id, "name": t.name, "thumb_url": t.thumb_url}
                    for t in u.templates
                ],
                qr_link=u.qr.link if u.qr else None,
            ))
            
        return response_data
    except Exception as e:
        raise handle_error(e, app_logger, "get_all_users_detailed")


class SetActiveTemplateRequest(BaseModel):
    template_id: int
    base_url: Optional[str] = None


class PublicProfileResponse(BaseModel):
    user_id: int
    username: str
    avatar_url: Optional[str] = None
    active_template_id: Optional[int] = None
    active_template_file_url: Optional[str] = None
    active_template_name: Optional[str] = None
    is_owner: bool = False
    qr_image_url: Optional[str] = None


@profile_router.patch("/me/active-template")
async def set_active_template(
    payload: SetActiveTemplateRequest,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Установить активный шаблон для профиля пользователя.
    QR-код остается прежним и всегда ведет на /profile/{user_id}.
    Меняется только Editor.current_template_id.
    """
    try:
        s3 = _s3_or_500()
        qr, editor, template, profile_url = await set_editor_current_template(
            db=db,
            user=user,
            template_id=payload.template_id,
            s3=s3,
            base_url=payload.base_url,
            regenerate_qr=False,  # ✅ QR остается прежним!
        )
        return {
            "message": "Active template updated",
            "template_id": template.id,
            "qr_image_url": qr.link,
            "profile_url": profile_url,
        }
    except Exception as e:
        raise handle_error(e, app_logger, "set_active_template")


@profile_router.get("/{user_id}/profile", response_model=PublicProfileResponse)
async def get_public_profile(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user_optional: Optional[User] = Depends(lambda: None),  # Опциональная авторизация
):
    """
    Получить публичный профиль пользователя с активным шаблоном.
    Доступно всем (в т.ч. неавторизованным).
    """
    try:
        # Получаем целевого пользователя
        target_user = await db.get(User, user_id)
        if not target_user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Получаем редактор и активный шаблон
        editor = await db.scalar(
            select(Editor).where(Editor.user_id == user_id)
        )
        
        active_template = None
        if editor and editor.current_template_id:
            active_template = await db.get(Template, editor.current_template_id)
        
        # Получаем QR
        from app.models.models import QRCode
        qr = await db.scalar(select(QRCode).where(QRCode.user_id == user_id))
        
        # Проверяем, является ли текущий пользователь владельцем
        is_owner = current_user_optional and current_user_optional.id == user_id if current_user_optional else False
        
        return PublicProfileResponse(
            user_id=target_user.id,
            username=target_user.username,
            avatar_url=target_user.img_url,
            active_template_id=active_template.id if active_template else None,
            active_template_file_url=active_template.file_url if active_template else None,
            active_template_name=active_template.name if active_template else None,
            is_owner=is_owner,
            qr_image_url=qr.link if qr else None,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise handle_error(e, app_logger, "get_public_profile")

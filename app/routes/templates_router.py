import os
from typing import Optional, List

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.models import User
from app.routes.dependecies import current_user
from app.schemas.templates_schemas import TemplateOut, TemplateUpdateIn, TemplateCountOut
from app.helpers.templates_helpers import (
    create_template_for_user,
    update_template_meta,
    replace_template_file,
    delete_template,
    count_templates_for_user, list_templates_for_user,
)
from app.s3.s3 import S3Client

templates_router = APIRouter(prefix="/templates", tags=["templates"])

s3_client = S3Client(
    access_key=os.getenv("S3_ACCESS_KEY"),
    secret_key=os.getenv("S3_SECRET_KEY"),
    endpoint_url=os.getenv("S3_ENDPOINT_URL"),
    bucket_name=os.getenv("S3_BUCKET_NAME"),
)

@templates_router.post("", response_model=TemplateOut)
async def create_template(
    name: Optional[str] = Form(default=None),
    description: Optional[str] = Form(default=None),
    file: UploadFile = File(...),
    thumb_file: Optional[UploadFile] = File(default=None),
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Создать новый темплейт: загружаем файл (и опц. превью) в S3 и сохраняем Template.
    """
    tpl = await create_template_for_user(
        db=db,
        s3=s3_client,
        user=user,
        file=file,
        name=name,
        description=description,
        thumb_file=thumb_file,
    )
    return tpl

@templates_router.get("/count/{user_id}", response_model=TemplateCountOut)
async def templates_count(
    user_id: int,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Количество темплейтов конкретного юзера по айди.
    Доступ: владелец или суперюзер.
    """
    cnt = await count_templates_for_user(db, user, user_id)
    return TemplateCountOut(user_id=user_id, count=cnt)

@templates_router.patch("/{template_id}", response_model=TemplateOut)
async def update_template(
    template_id: int,
    payload: TemplateUpdateIn,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Обновить метаданные темплейта (name/description/thumb_url).
    """
    tpl = await update_template_meta(
        db=db,
        requester=user,
        template_id=template_id,
        name=payload.name,
        description=payload.description,
        thumb_url=payload.thumb_url,
    )
    return tpl

@templates_router.patch("/{template_id}/file", response_model=TemplateOut)
async def update_template_file(
    template_id: int,
    file: UploadFile = File(...),
    thumb_file: Optional[UploadFile] = File(default=None),
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Заменить файл (и опционально превью) у темплейта. Перезаливает в S3, обновляет ссылки.
    """
    tpl = await replace_template_file(
        db=db,
        s3=s3_client,
        requester=user,
        template_id=template_id,
        new_file=file,
        new_thumb_file=thumb_file,
    )
    return tpl

@templates_router.delete("/{template_id}", status_code=204)
async def remove_template(
    template_id: int,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Удалить конкретный темплейт (из БД). Доступ: владелец или суперюзер.
    """
    await delete_template(db=db, s3=s3_client, requester=user, template_id=template_id)
    return

@templates_router.get("/by-user/{user_id}", response_model=List[TemplateOut])
async def list_user_templates(
    user_id: int,
    include_global: bool = True,
    limit: int = 50,
    offset: int = 0,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Листинг шаблонов конкретного пользователя.
    - include_global=True: вернёт и глобальные шаблоны (owner_user_id IS NULL)
    - limit/offset: пагинация
    Доступ: сам пользователь или суперюзер.
    """
    templates = await list_templates_for_user(
        db=db,
        requester=user,
        target_user_id=user_id,
        include_global=include_global,
        limit=limit,
        offset=offset,
    )
    return templates
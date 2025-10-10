import os
import re
import uuid
from pathlib import Path
from typing import Optional, Type, Sequence

from fastapi import HTTPException, UploadFile
from sqlalchemy import func, select, or_, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Template, User
from app.s3.s3 import S3Client

SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")

def _sanitize_filename(name: str) -> str:
    name = name.strip().replace(" ", "_")
    name = SAFE_NAME_RE.sub("", name)
    return name or uuid.uuid4().hex

def _user_templates_key(user_id: int, original_filename: str) -> str:
    safe = _sanitize_filename(original_filename)
    return f"templates/{user_id}/{uuid.uuid4().hex[:8]}_{safe}"

def _tmp_dir() -> Path:
    p = Path("tmp"); p.mkdir(exist_ok=True)
    return p

def _s3_public_base() -> str:
    return os.getenv("S3_PUBLIC_BASE", "https://3e06ba26-08cc-45a0-99f2-455006fbe542.selstorage.ru").rstrip("/")

async def _save_upload_to_tmp(upload: UploadFile) -> Path:
    tmp = _tmp_dir() / f"upload_{uuid.uuid4().hex[:8]}_{_sanitize_filename(upload.filename or 'file.bin')}"
    content = await upload.read()
    tmp.write_bytes(content)
    await upload.close()
    return tmp

async def create_template_for_user(
    db: AsyncSession,
    s3: S3Client,
    user: User,
    *,
    file: UploadFile,
    name: Optional[str] = None,
    description: Optional[str] = None,
    thumb_file: Optional[UploadFile] = None,
) -> Template:
    """
    Создаёт Template для конкретного юзера, загружая основной файл (и опционально превью) в S3.
    Возвращает ORM-объект Template.
    """
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="File is required")

    tmp_file = await _save_upload_to_tmp(file)
    object_name = _user_templates_key(user.id, file.filename or "template.bin")
    await s3.upload_file(str(tmp_file), object_name)
    tmp_file.unlink(missing_ok=True)
    file_url = f"{_s3_public_base()}/{object_name}"

    thumb_url = None
    if thumb_file and thumb_file.filename:
        tmp_thumb = await _save_upload_to_tmp(thumb_file)
        thumb_object = _user_templates_key(user.id, thumb_file.filename or "thumb.png")
        await s3.upload_file(str(tmp_thumb), thumb_object)
        tmp_thumb.unlink(missing_ok=True)
        thumb_url = f"{_s3_public_base()}/{thumb_object}"

    tpl = Template(
        name=name or (file.filename or "Template"),
        description=description,
        file_url=file_url,
        thumb_url=thumb_url,
        owner_user_id=user.id,
    )
    db.add(tpl)
    await db.flush()
    await db.commit()
    await db.refresh(tpl)
    return tpl

async def update_template_meta(
    db: AsyncSession,
    requester: User,
    template_id: int,
    *,
    name: Optional[str] = None,
    description: Optional[str] = None,
    thumb_url: Optional[str] = None,
) -> Type[Template]:
    """
    Обновляет метаданные темплейта (текстовые поля). Доступ: владелец или суперюзер.
    """
    tpl = await db.get(Template, template_id)
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")

    if (tpl.owner_user_id is not None and tpl.owner_user_id != requester.id) and (not requester.is_superuser):
        raise HTTPException(status_code=403, detail="Forbidden")

    if name is not None:
        tpl.name = name
    if description is not None:
        tpl.description = description
    if thumb_url is not None:
        tpl.thumb_url = thumb_url

    await db.commit()
    await db.refresh(tpl)
    return tpl

async def replace_template_file(
    db: AsyncSession,
    s3: S3Client,
    requester: User,
    template_id: int,
    *,
    new_file: UploadFile,
    new_thumb_file: Optional[UploadFile] = None,
) -> Type[Template]:
    """
    Заменяет файл (и опционально превью) у темплейта, заливая новые версии в S3.
    Старые файлы при необходимости можно удалить из S3 (если добавите delete в S3Client).
    """
    tpl = await db.get(Template, template_id)
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")

    if (tpl.owner_user_id is not None and tpl.owner_user_id != requester.id) and (not requester.is_superuser):
        raise HTTPException(status_code=403, detail="Forbidden")

    tmp_file = await _save_upload_to_tmp(new_file)
    object_name = _user_templates_key(requester.id, new_file.filename or "template.bin")
    await s3.upload_file(str(tmp_file), object_name)
    tmp_file.unlink(missing_ok=True)
    tpl.file_url = f"{_s3_public_base()}/{object_name}"

    if new_thumb_file and new_thumb_file.filename:
        tmp_thumb = await _save_upload_to_tmp(new_thumb_file)
        thumb_object = _user_templates_key(requester.id, new_thumb_file.filename or "thumb.png")
        await s3.upload_file(str(tmp_thumb), thumb_object)
        tmp_thumb.unlink(missing_ok=True)
        tpl.thumb_url = f"{_s3_public_base()}/{thumb_object}"

    await db.commit()
    await db.refresh(tpl)
    return tpl

async def delete_template(
    db: AsyncSession,
    s3: S3Client | None,
    requester: User,
    template_id: int,
) -> None:
    # проверка прав/владельца на стороне БД (без загрузки объекта в identity map)
    tpl = await db.scalar(select(Template).where(Template.id == template_id))
    if not tpl:
        raise HTTPException(status_code=404, detail={"error":"not_found","msg":"Template not found"})

    if (tpl.owner_user_id is not None and tpl.owner_user_id != requester.id) and (not requester.is_superuser):
        raise HTTPException(status_code=403, detail={"error":"forbidden","msg":"Not allowed to delete this template"})

    # при необходимости удаление из S3 (опционально)
    # if s3 and tpl.file_url: await s3.delete_object_by_url(tpl.file_url)
    # if s3 and getattr(tpl, "thumb_url", None): await s3.delete_object_by_url(tpl.thumb_url)

    res = await db.execute(delete(Template).where(Template.id == template_id))
    if res.rowcount == 0:
        # если к моменту удаления кто-то уже удалил — отдадим 404
        raise HTTPException(status_code=404, detail={"error":"not_found","msg":"Template not found"})
    await db.commit()

async def count_templates_for_user(
    db: AsyncSession,
    requester: User,
    target_user_id: int,
) -> int:
    """
    Считает количество темплейтов у конкретного пользователя.
    Доступ: сам пользователь или суперюзер.
    """
    if (requester.id != target_user_id) and (not requester.is_superuser):
        raise HTTPException(status_code=403, detail="Forbidden")

    q = await db.execute(
        select(func.count(Template.id)).where(Template.owner_user_id == target_user_id)
    )
    return int(q.scalar() or 0)

async def list_templates_for_user(
    db: AsyncSession,
    requester: User,
    target_user_id: int,
    *,
    include_global: bool = True,
    limit: int = 50,
    offset: int = 0,
) -> Sequence[Template]:
    """
    Вернёт список шаблонов для target_user_id.
    Доступ: владелец или суперюзер.
    include_global=True — включает глобальные шаблоны (owner_user_id IS NULL).
    """
    if (requester.id != target_user_id) and (not requester.is_superuser):
        raise HTTPException(status_code=403, detail="Forbidden")

    where_clause = Template.owner_user_id == target_user_id
    if include_global:
        where_clause = or_(Template.owner_user_id == target_user_id, Template.owner_user_id.is_(None))

    q = (
        select(Template)
        .where(where_clause)
        .order_by(Template.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = (await db.execute(q)).scalars().all()
    return rows
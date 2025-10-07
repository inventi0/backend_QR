import os
import re
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.models import User
from app.s3.s3 import S3Client

async def get_user_by_id(user_id: int, db: AsyncSession):
    result = await db.execute(
        select(User).filter(User.user_id == user_id)
    )
    user = result.scalars().first()
    if not user:
        raise ValueError("User not found")
    return user

SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")

def _sanitize_filename(name: str) -> str:
    name = (name or "file.bin").strip().replace(" ", "_")
    return SAFE_NAME_RE.sub("", name) or uuid.uuid4().hex

def _tmp_dir() -> Path:
    p = Path("tmp"); p.mkdir(exist_ok=True)
    return p

async def _save_upload_to_tmp(upload: UploadFile) -> Path:
    tmp = _tmp_dir() / f"avatar_{uuid.uuid4().hex[:8]}_{_sanitize_filename(upload.filename)}"
    content = await upload.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")
    tmp.write_bytes(content)
    await upload.close()
    return tmp

def _s3_public_base() -> str:
    return os.getenv("S3_PUBLIC_BASE", "https://3e06ba26-08cc-45a0-99f2-455006fbe542.selstorage.ru").rstrip("/")

async def set_user_avatar(
    db: AsyncSession,
    s3: S3Client,
    user: User,
    file: UploadFile,
) -> User:
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="Avatar file is required")

    tmp = await _save_upload_to_tmp(file)
    object_key = f"avatars/{user.id}/{uuid.uuid4().hex[:8]}_{_sanitize_filename(file.filename)}"
    await s3.upload_file(str(tmp), object_key)
    tmp.unlink(missing_ok=True)

    user.img_url = f"{_s3_public_base()}/{object_key}"
    await db.commit()
    await db.refresh(user)
    return user

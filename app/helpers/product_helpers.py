import os
import re
import uuid
from pathlib import Path
from typing import Optional, Sequence, Type

from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Product, User, QRCode
from app.s3.s3 import S3Client
from app.helpers.codegen import ensure_user_editor_and_qr

SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")

def _sanitize_filename(name: str) -> str:
    name = name.strip().replace(" ", "_")
    name = SAFE_NAME_RE.sub("", name)
    return name or uuid.uuid4().hex

def _tmp_dir() -> Path:
    p = Path("tmp")
    p.mkdir(exist_ok=True)
    return p

async def _save_upload_to_tmp(upload: UploadFile) -> Path:
    tmp = _tmp_dir() / f"upload_{uuid.uuid4().hex[:8]}_{_sanitize_filename(upload.filename or 'file.bin')}"
    content = await upload.read()
    tmp.write_bytes(content)
    await upload.close()
    return tmp

def _s3_public_base() -> str:
    return os.getenv("S3_PUBLIC_BASE", "https://3e06ba26-08cc-45a0-99f2-455006fbe542.selstorage.ru").rstrip("/")


async def list_products(
    db: AsyncSession,
    *,
    type_filter: Optional[str] = None,
    size_filter: Optional[str] = None,
    color_filter: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Sequence[Product]:
    q = select(Product)
    if type_filter:
        q = q.where(Product.type.ilike(f"%{type_filter}%"))
    if size_filter:
        q = q.where(Product.size.ilike(f"%{size_filter}%"))
    if color_filter:
        q = q.where(Product.color.ilike(f"%{color_filter}%"))

    q = q.order_by(Product.id.desc()).limit(limit).offset(offset)
    rows = (await db.execute(q)).scalars().all()
    return rows

async def get_product_by_id(db: AsyncSession, product_id: int) -> Type[Product]:
    product = await db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

async def create_product(
    db: AsyncSession,
    s3: S3Client,
    requester: User,
    *,
    p_type: str,
    size: str,
    color: str,
    description: Optional[str],
    image_file: UploadFile,
) -> Product:
    if not requester.is_superuser:
        raise HTTPException(status_code=403, detail="Forbidden")

    if not image_file or not image_file.filename:
        raise HTTPException(status_code=400, detail="Image file is required")

    qr = await db.scalar(select(QRCode).where(QRCode.user_id == requester.id))
    if not qr:
        _, qr, _ = await ensure_user_editor_and_qr(db, s3, requester)

    product = Product(
        type=p_type,
        size=size,
        color=color,
        description=description,
        qr_id=qr.id,
    )
    db.add(product)
    await db.flush()

    tmp_file = await _save_upload_to_tmp(image_file)
    object_key = f"products/{product.id}/{uuid.uuid4().hex[:8]}_{_sanitize_filename(image_file.filename)}"
    await s3.upload_file(str(tmp_file), object_key)
    tmp_file.unlink(missing_ok=True)

    product.img_url = f"{_s3_public_base()}/{object_key}"
    await db.commit()
    await db.refresh(product)
    return product

async def update_product_meta(
    db: AsyncSession,
    requester: User,
    product_id: int,
    *,
    p_type: Optional[str] = None,
    size: Optional[str] = None,
    color: Optional[str] = None,
    description: Optional[str] = None,
) -> Type[Product]:
    if not requester.is_superuser:
        raise HTTPException(status_code=403, detail="Forbidden")

    product = await get_product_by_id(db, product_id)

    if p_type is not None:
        product.type = p_type
    if size is not None:
        product.size = size
    if color is not None:
        product.color = color
    if description is not None:
        product.description = description

    await db.commit()
    await db.refresh(product)
    return product

async def replace_product_image(
    db: AsyncSession,
    s3: S3Client,
    requester: User,
    product_id: int,
    *,
    new_image_file: UploadFile,
) -> Type[Product]:
    if not requester.is_superuser:
        raise HTTPException(status_code=403, detail="Forbidden")

    product = await get_product_by_id(db, product_id)

    if not new_image_file or not new_image_file.filename:
        raise HTTPException(status_code=400, detail="Image file is required")

    tmp_file = await _save_upload_to_tmp(new_image_file)
    object_key = f"products/{product.id}/{uuid.uuid4().hex[:8]}_{_sanitize_filename(new_image_file.filename)}"
    await s3.upload_file(str(tmp_file), object_key)
    tmp_file.unlink(missing_ok=True)

    product.img_url = f"{_s3_public_base()}/{object_key}"
    await db.commit()
    await db.refresh(product)
    return product

async def delete_product(
    db: AsyncSession,
    requester: User,
    product_id: int,
) -> None:
    if not requester.is_superuser:
        raise HTTPException(status_code=403, detail="Forbidden")

    product = await get_product_by_id(db, product_id)
    await db.delete(product)
    await db.commit()

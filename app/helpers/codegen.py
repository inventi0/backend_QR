import uuid
import qrcode
from datetime import datetime
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.s3.s3 import S3Client
from app.models.models import Canvas, QRCode, Product, User
from fastapi import HTTPException
import os

def _generate_qr_image(data: str, tmp_dir: Path) -> Path:
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    filename = f"qr_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}.png"
    file_path = tmp_dir / filename
    img.save(file_path)
    return file_path


async def _get_or_create_master_qr(db: AsyncSession) -> QRCode:
    """
    Один QR для всех товаров.
    Код берём из окружения QR_MASTER_CODE (или 'main'), создаём при первом вызове.
    """
    code = os.getenv("QR_MASTER_CODE", "main")
    qr = await db.scalar(select(QRCode).where(QRCode.code == code))
    if qr:
        return qr

    qr = QRCode(code=code)
    db.add(qr)
    await db.flush()
    return qr


async def create_qr_for_product_helper(
    db: AsyncSession,
    s3: S3Client,
    user: User,
    product_id: int,
) -> dict:
    product = await db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    qr = await _get_or_create_master_qr(db)

    canvas = Canvas(
        user_id=user.id,
        product_id=product.id,
        image_url="https://example.com",
        qr_id=qr.id,
    )
    db.add(canvas)
    await db.flush()

    frontend_base = os.getenv("PUBLIC_FRONTEND_BASE_URL")
    if frontend_base:
        canvas.public_url = f"{frontend_base.rstrip('/')}/canvas/{canvas.id}"

    qr.current_canvas_id = canvas.id

    api_base = os.getenv("PUBLIC_API_BASE_URL")
    if not api_base:
        api_base = frontend_base or "https://example.com"

    target_url = f"{api_base.rstrip('/')}/qr/{qr.code}"

    tmp_dir = Path("tmp")
    tmp_dir.mkdir(exist_ok=True)
    file_path = _generate_qr_image(target_url, tmp_dir)
    object_name = f"qr_codes/{file_path.name}"

    await s3.upload_file(str(file_path), object_name)
    file_path.unlink(missing_ok=True)

    qr_image_url = f"{os.getenv('S3_PUBLIC_BASE', 'https://3e06ba26-08cc-45a0-99f2-455006fbe542.selstorage.ru').rstrip('/')}/{object_name}"

    qr.link = qr_image_url

    await db.commit()
    await db.refresh(qr)

    return {
        "canvas_id": canvas.id,
        "qr_id": qr.id,
        "qr_image_url": qr_image_url,
        "code": qr.code,
        "target_url": target_url,
    }

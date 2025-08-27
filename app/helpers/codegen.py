import uuid
import qrcode
from PIL import ImageDraw, ImageFont
from datetime import datetime
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from app.s3.s3 import S3Client
from app.models.models import Canvas, QRCode, Product, User
from fastapi import HTTPException

def generate_qr_image(data: str, tmp_dir: Path) -> Path:
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except Exception:
        font = ImageFont.load_default()

    draw = ImageDraw.Draw(img)
    text_width = font.getlength(data)
    text_height = font.getbbox("A")[3] - font.getbbox("A")[1]
    width, height = img.size
    x = (width - text_width) / 2
    y = height - text_height - 10
    draw.text((x, y), data, fill="black", font=font)

    filename = f"qr_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}.png"
    file_path = tmp_dir / filename
    img.save(file_path)

    return file_path


async def create_qr_for_product_helper(
    db: AsyncSession,
    s3: S3Client,
    user: User,
    product_id: int,
) -> dict:

    product = await db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    canvas = Canvas(user_id=user.id, product_id=product.id, image_url="https://example.com")
    db.add(canvas)
    await db.flush()

    tmp_dir = Path("tmp")
    tmp_dir.mkdir(exist_ok=True)
    file_path = generate_qr_image(str(canvas.image_url), tmp_dir)
    object_name = f"qr_codes/{file_path.name}"

    await s3.upload_file(str(file_path), object_name)

    file_path.unlink(missing_ok=True)

    qr_url = f"https://3e06ba26-08cc-45a0-99f2-455006fbe542.selstorage.ru/{object_name}"

    qr_code = QRCode(link=qr_url, canvas_id=canvas.id)
    db.add(qr_code)
    await db.commit()
    await db.refresh(qr_code)

    return {
        "canvas_id": canvas.id,
        "qr_id": qr_code.id,
        "qr_link": qr_code.link,
    }

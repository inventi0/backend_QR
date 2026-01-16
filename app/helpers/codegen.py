import os
import uuid
import qrcode
from datetime import datetime
from pathlib import Path
from typing import Tuple

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import User, QRCode, Editor, Template
from app.s3.s3 import S3Client


def _make_slug(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


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


def _editor_url(editor_public_id: str, base_url: str = None) -> str:
    """Generate editor URL with optional custom base_url"""
    if base_url:
        return f"{base_url.rstrip('/')}/editor/{editor_public_id}"
    frontend_base = os.getenv("PUBLIC_FRONTEND_BASE_URL", "").rstrip("/")
    api_base = os.getenv("PUBLIC_API_BASE_URL", "").rstrip("/")
    base = frontend_base or api_base
    return f"{base}/editor/{editor_public_id}" if base else f"/editor/{editor_public_id}"


def _profile_url(user_id: int, base_url: str = None) -> str:
    """Generate profile URL with optional custom base_url"""
    if base_url:
        return f"{base_url.rstrip('/')}/profile/{user_id}"
    frontend_base = os.getenv("PUBLIC_FRONTEND_BASE_URL", "").rstrip("/")
    api_base = os.getenv("PUBLIC_API_BASE_URL", "").rstrip("/")
    base = frontend_base or api_base
    return f"{base}/profile/{user_id}" if base else f"/profile/{user_id}"


async def ensure_user_editor_and_qr(
    db: AsyncSession,
    s3: S3Client | None,
    user: User,
    base_url: str = None,
    use_profile_url: bool = True,
) -> Tuple[Editor, QRCode, str]:
    """
    Идемпотентно создаёт Editor и QR для пользователя, если их ещё нет.
    Возвращает (editor, qr, target_url).
    
    Args:
        use_profile_url: если True, QR ведет на /profile/{user_id}, иначе на /editor/{public_id}
        base_url: кастомный домен (например, http://localhost:5173)
    """
    editor = await db.scalar(select(Editor).where(Editor.user_id == user.id))
    if not editor:
        editor = Editor(public_id=_make_slug("ed"), user_id=user.id)
        db.add(editor)
        await db.flush()

    qr = await db.scalar(select(QRCode).where(QRCode.user_id == user.id))
    if not qr:
        qr = QRCode(
            code=f"qr-{editor.public_id}",
            user_id=user.id,
            editor_id=editor.id,
        )
        db.add(qr)
        await db.flush()

    # Выбираем URL: профиль или редактор
    if use_profile_url:
        target_url = _profile_url(user.id, base_url)
    else:
        target_url = _editor_url(editor.public_id, base_url)

    if not qr.link and s3:
        tmp_dir = Path("tmp"); tmp_dir.mkdir(exist_ok=True)
        file_path = _generate_qr_image(target_url, tmp_dir)
        object_name = f"qr_codes/{user.id}_{file_path.name}"
        await s3.upload_file(str(file_path), object_name)
        file_path.unlink(missing_ok=True)

        s3_public = os.getenv(
            "S3_PUBLIC_BASE",
            "https://3e06ba26-08cc-45a0-99f2-455006fbe542.selstorage.ru"
        ).rstrip("/")
        qr.link = f"{s3_public}/{object_name}"
        await db.flush()

    await db.commit()
    await db.refresh(editor)
    await db.refresh(qr)
    return editor, qr, target_url


async def get_qr_for_user(
    db: AsyncSession,
    user_id: int,
) -> tuple[QRCode, Editor, str]:
    """Получить QR и Editor по user_id (404 если нет)."""
    qr = await db.scalar(select(QRCode).where(QRCode.user_id == user_id))
    if not qr:
        raise HTTPException(status_code=404, detail="QR not found for user")
    editor = await db.scalar(select(Editor).where(Editor.id == qr.editor_id))
    if not editor:
        raise HTTPException(status_code=404, detail="Editor not found for QR")
    return qr, editor, _editor_url(editor.public_id)


async def set_editor_current_template(
    db: AsyncSession,
    user: User,
    template_id: int,
    s3: S3Client | None = None,
    base_url: str = None,
    regenerate_qr: bool = False,
) -> tuple[QRCode, Editor, Template, str]:
    """
    Переключить активный шаблон редактора.
    
    ⚠️ ВАЖНО: QR-код НЕ перегенерируется! Он постоянный.
    QR всегда ведет на /profile/{user_id}, меняется только Editor.current_template_id.
    
    Это позволяет печатать QR на одежде один раз, и он всегда будет работать,
    показывая текущий активный дизайн пользователя.
    
    Args:
        base_url: кастомный домен для QR-ссылки (используется только при первом создании)
        regenerate_qr: пересоздать QR-изображение (по умолчанию False, обычно не нужно)
    """
    editor = await db.scalar(select(Editor).where(Editor.user_id == user.id))
    if not editor:
        raise HTTPException(status_code=404, detail="Editor not found for user")

    tpl = await db.scalar(select(Template).where(Template.id == template_id))
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")

    if tpl.owner_user_id is not None and tpl.owner_user_id != user.id:
        raise HTTPException(status_code=403, detail="Template belongs to another user")

    editor.current_template_id = tpl.id

    qr = await db.scalar(select(QRCode).where(QRCode.user_id == user.id))
    if not qr:
        raise HTTPException(status_code=404, detail="QR not found for user")

    # QR теперь ведет на профиль, а не на редактор
    profile_url = _profile_url(user.id, base_url)

    if s3 and regenerate_qr:
        tmp_dir = Path("tmp"); tmp_dir.mkdir(exist_ok=True)
        file_path = _generate_qr_image(profile_url, tmp_dir)
        object_name = f"qr_codes/{user.id}_{file_path.name}"
        await s3.upload_file(str(file_path), object_name)
        file_path.unlink(missing_ok=True)

        s3_public = os.getenv(
            "S3_PUBLIC_BASE",
            "https://3e06ba26-08cc-45a0-99f2-455006fbe542.selstorage.ru"
        ).rstrip("/")
        qr.link = f"{s3_public}/{object_name}"

    await db.commit()
    await db.refresh(editor)
    await db.refresh(qr)

    return qr, editor, tpl, profile_url

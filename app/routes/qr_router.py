import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.models import User, QRCode, Editor
from app.routes.dependecies import current_user, current_superuser
from app.schemas.qr_schemas import QRCodeOut, QRSetTemplateIn
from app.helpers.codegen import (
    get_qr_for_user,
    set_editor_current_template,
)

from app.s3.s3 import S3Client
s3_client = S3Client(
    access_key=os.getenv("S3_ACCESS_KEY"),
    secret_key=os.getenv("S3_SECRET_KEY"),
    endpoint_url=os.getenv("S3_ENDPOINT_URL"),
    bucket_name=os.getenv("S3_BUCKET_NAME"),
)

qr_router = APIRouter(prefix="/qr", tags=["qr"])

def _as_qr_out(qr: QRCode, editor: Editor, editor_url: str) -> QRCodeOut:
    return QRCodeOut(
        qr_id=qr.id,
        user_id=qr.user_id,
        code=qr.code,
        qr_image_url=qr.link,
        editor_id=editor.id,
        editor_public_id=editor.public_id,
        editor_url=editor_url,
        current_template_id=editor.current_template_id,
        current_template_file_url=getattr(editor.current_template, "file_url", None) if editor.current_template else None,
    )


@qr_router.get("/by-user/{user_id}", response_model=QRCodeOut)
async def get_qr_by_user(
    user_id: int,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    if (user.id != user_id):
        raise HTTPException(status_code=403, detail="Forbidden")

    qr, editor, editor_url = await get_qr_for_user(db, user_id)
    return _as_qr_out(qr, editor, editor_url)


@qr_router.get("/", response_model=list[QRCodeOut], name="list-qr")
async def list_all_qrs(
    user: User = Depends(current_superuser),
    db: AsyncSession = Depends(get_db),
):
    qrs = (await db.execute(select(QRCode))).scalars().all()
    result: list[QRCodeOut] = []
    for qr in qrs:
        editor = await db.get(Editor, qr.editor_id)
        if not editor:
            continue
        base = os.getenv("PUBLIC_FRONTEND_BASE_URL", "").rstrip("/")
        editor_url = f"{base}/editor/{editor.public_id}" if base else f"/editor/{editor.public_id}"
        result.append(_as_qr_out(qr, editor, editor_url))
    return result


@qr_router.patch("/set-template", response_model=QRCodeOut)
async def update_qr_set_new_template(
    payload: QRSetTemplateIn,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    qr, editor, tpl, editor_url = await set_editor_current_template(
        db=db,
        user=user,
        template_id=payload.template_id,
        s3=s3_client,
    )
    return _as_qr_out(qr, editor, editor_url)

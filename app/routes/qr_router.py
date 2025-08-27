from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.models import User
from app.helpers.codegen import create_qr_for_product_helper
from app.s3.s3 import S3Client
from app.schemas.qr_schemas import QRCodeOut
from .dependecies import current_user
import os

qr_router = APIRouter(prefix="/qr", tags=["qr"])

s3_client = S3Client(
    access_key=os.getenv("S3_ACCESS_KEY"),
    secret_key=os.getenv("S3_SECRET_KEY"),
    endpoint_url=os.getenv("S3_ENDPOINT_URL"),
    bucket_name=os.getenv("S3_BUCKET_NAME"),
)

@qr_router.post("/create/{product_id}", response_model=QRCodeOut)
async def create_qr_for_product(
    product_id: int,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    return await create_qr_for_product_helper(
        db=db,
        s3=s3_client,
        user=user,
        product_id=product_id,
    )

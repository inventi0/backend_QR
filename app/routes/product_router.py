import os
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, UploadFile, File, Form, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.models import User
from app.routes.dependecies import current_user, current_superuser
from app.schemas.product_schemas import ProductOut, ProductUpdateIn
from app.helpers.product_helpers import (
    list_products,
    get_product_by_id,
    create_product,
    update_product_meta,
    replace_product_image,
    delete_product,
)
from app.s3.s3 import S3Client

from app.error.handler import handle_error
from app.logging_config import app_logger

products_router = APIRouter(prefix="/products", tags=["products"])

s3_client = S3Client(
    access_key=os.getenv("S3_ACCESS_KEY"),
    secret_key=os.getenv("S3_SECRET_KEY"),
    endpoint_url=os.getenv("S3_ENDPOINT_URL"),
    bucket_name=os.getenv("S3_BUCKET_NAME"),
)


@products_router.get("/", response_model=List[ProductOut])
async def products_list(
    type: Optional[str] = Query(default=None, description="Фильтр по типу (например, 'Футболка')"),
    size: Optional[str] = Query(default=None, description="Фильтр по размеру (например, 'M')"),
    color: Optional[str] = Query(default=None, description="Фильтр по цвету (например, 'Белый')"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        rows = await list_products(
            db,
            type_filter=type,
            size_filter=size,
            color_filter=color,
            limit=limit,
            offset=offset,
        )
        return rows
    except Exception as e:
        raise handle_error(e, app_logger, "products_list")


@products_router.get("/{product_id}", response_model=ProductOut)
async def product_get(
    product_id: int,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        product = await get_product_by_id(db, product_id)
        return product
    except Exception as e:
        raise handle_error(e, app_logger, "product_get")


@products_router.post("", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
async def product_create(
    p_type: str = Form(..., description="Тип продукта, например 'Футболка'"),
    size: str = Form(..., description="Размер, например 'M'"),
    color: str = Form(..., description="Цвет, например 'Белый'"),
    description: Optional[str] = Form(default=None),
    image: UploadFile = File(...),
    user: User = Depends(current_superuser),
    db: AsyncSession = Depends(get_db),
):
    try:
        product = await create_product(
            db=db,
            s3=s3_client,
            requester=user,
            p_type=p_type,
            size=size,
            color=color,
            description=description,
            image_file=image,
        )
        return product
    except Exception as e:
        raise handle_error(e, app_logger, "product_create")


@products_router.patch("/{product_id}", response_model=ProductOut)
async def product_update_meta(
    product_id: int,
    payload: ProductUpdateIn,
    user: User = Depends(current_superuser),
    db: AsyncSession = Depends(get_db),
):
    try:
        product = await update_product_meta(
            db=db,
            requester=user,
            product_id=product_id,
            p_type=payload.type,
            size=payload.size,
            color=payload.color,
            description=payload.description,
        )
        return product
    except Exception as e:
        raise handle_error(e, app_logger, "product_update_meta")


@products_router.patch("/{product_id}/image", response_model=ProductOut)
async def product_update_image(
    product_id: int,
    image: UploadFile = File(...),
    user: User = Depends(current_superuser),
    db: AsyncSession = Depends(get_db),
):
    try:
        product = await replace_product_image(
            db=db,
            s3=s3_client,
            requester=user,
            product_id=product_id,
            new_image_file=image,
        )
        return product
    except Exception as e:
        raise handle_error(e, app_logger, "product_update_image")


@products_router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def product_delete(
    product_id: int,
    user: User = Depends(current_superuser),
    db: AsyncSession = Depends(get_db),
):
    try:
        await delete_product(db=db, requester=user, product_id=product_id)
        return
    except Exception as e:
        raise handle_error(e, app_logger, "product_delete")

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.models import User
from app.helpers.review_helpers import (
    create_review_helper,
    get_review_helper,
    get_reviews_helper,
    update_review_helper,
    delete_review_helper,
    get_my_review_helper,
)
from app.schemas.review_schemas import ReviewCreate, ReviewUpdate, ReviewRead
from .dependecies import current_user

from app.error.handler import handle_error
from app.logging_config import app_logger

review_router = APIRouter(prefix="/reviews", tags=["reviews"])


@review_router.get("/", response_model=list[ReviewRead])
async def get_reviews(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    """Получить список отзывов (с пагинацией)."""
    try:
        return await get_reviews_helper(db=db, skip=skip, limit=limit)
    except Exception as e:
        raise handle_error(e, app_logger, "get_reviews")


@review_router.get("/me", response_model=ReviewRead | None)
async def get_my_review(
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    """Получить отзыв текущего пользователя (если существует)."""
    try:
        return await get_my_review_helper(db=db, user_id=user.id)
    except Exception as e:
        raise handle_error(e, app_logger, "get_my_review")


@review_router.get("/{review_id}", response_model=ReviewRead)
async def get_review(
    review_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Получить один отзыв по ID."""
    try:
        return await get_review_helper(db=db, review_id=review_id)
    except Exception as e:
        raise handle_error(e, app_logger, "get_review")


@review_router.post("/", response_model=ReviewRead)
async def create_review(
    review_in: ReviewCreate,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    """Создать новый отзыв (для авторизованного пользователя)."""
    try:
        return await create_review_helper(
            db=db,
            review_in=review_in,
            user_id=user.id,
        )
    except Exception as e:
        raise handle_error(e, app_logger, "create_review")


@review_router.patch("/{review_id}", response_model=ReviewRead)
async def update_review(
    review_id: int,
    review_in: ReviewUpdate,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    """Обновить отзыв (только свой или если суперюзер)."""
    try:
        # Сначала проверяем права
        review = await get_review_helper(db=db, review_id=review_id)
        if review.user_id != user.id and not user.is_superuser:
            raise HTTPException(
                status_code=403,
                detail={"error": "forbidden", "msg": "Not allowed to edit this review"},
            )
        # Затем обновляем
        return await update_review_helper(db=db, review_id=review_id, review_in=review_in)
    except Exception as e:
        raise handle_error(e, app_logger, "update_review")


@review_router.delete("/{review_id}")
async def delete_review(
    review_id: int,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    """Удалить отзыв (только свой или если суперюзер)."""
    try:
        review = await get_review_helper(db=db, review_id=review_id)
        if review.user_id != user.id and not user.is_superuser:
            raise HTTPException(
                status_code=403,
                detail={"error": "forbidden", "msg": "Not allowed to delete this review"},
            )
        return await delete_review_helper(db=db, review_id=review_id)
    except Exception as e:
        raise handle_error(e, app_logger, "delete_review")

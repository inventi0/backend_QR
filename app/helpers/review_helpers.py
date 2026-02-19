from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from fastapi import HTTPException
from app.models.models import Review, User
from app.schemas.review_schemas import ReviewCreate, ReviewUpdate
from app.helpers.moderation import check_bad_words

async def create_review_helper(
    db: AsyncSession,
    review_in: ReviewCreate,
    user_id: int,
) -> Review:
    # Проверка: пользователь уже оставил отзыв?
    existing = await db.execute(
        select(Review).where(Review.user_id == user_id)
    )
    if existing.scalars().first():
        raise HTTPException(
            status_code=400, 
            detail={"error": "already_exists", "msg": "You already have a review. Please edit it instead."}
        )
    
    is_flagged = await check_bad_words(db, review_in.content)
    
    review = Review(**review_in.dict(), user_id=user_id, is_flagged=is_flagged)
    db.add(review)
    await db.commit()
    await db.refresh(review)
    return review

async def get_review_helper(
    db: AsyncSession,
    review_id: int,
) -> Review:
    """Получить отзыв по ID (с пользователем)"""
    result = await db.execute(
        select(Review)
        .where(Review.id == review_id)
        .options(selectinload(Review.user))
    )
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return review


async def get_reviews_helper(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
) -> list[Review]:
    """Получить список отзывов"""
    result = await db.execute(
        select(Review)
        .where(Review.is_flagged == False)
        .options(selectinload(Review.user))
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()

async def get_all_reviews_admin_helper(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
) -> list[Review]:
    """Получить список ВСЕХ отзывов (для админки)"""
    result = await db.execute(
        select(Review)
        .options(selectinload(Review.user))
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


async def update_review_helper(
    db: AsyncSession,
    review_id: int,
    review_in: ReviewUpdate,
) -> Review:
    """Обновить отзыв"""
    review = await db.get(Review, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    for field, value in review_in.dict(exclude_unset=True).items():
        setattr(review, field, value)

    # Re-check moderation status on update
    review.is_flagged = await check_bad_words(db, review.content)

    db.add(review)
    await db.commit()
    await db.refresh(review)
    return review


async def delete_review_helper(
    db: AsyncSession,
    review_id: int,
) -> dict:
    """Удалить отзыв"""
    review = await db.get(Review, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    await db.delete(review)
    await db.commit()
    return {"status": "success", "message": f"Review {review_id} deleted"}


async def get_my_review_helper(
    db: AsyncSession,
    user_id: int,
) -> Review | None:
    """Получить отзыв текущего пользователя (если есть)"""
    result = await db.execute(
        select(Review)
        .where(Review.user_id == user_id)
        .options(selectinload(Review.user))
    )
    return result.scalars().first()

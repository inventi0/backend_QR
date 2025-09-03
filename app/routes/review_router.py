from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.models import User
from app.helpers.review_helpers import (
    create_review_helper,
    get_review_helper,
    get_reviews_helper,
    update_review_helper,
    delete_review_helper,
)
from app.schemas.review_schemas import ReviewCreate, ReviewUpdate, ReviewRead
from .dependecies import current_user

review_router = APIRouter(prefix="/reviews", tags=["reviews"])

@review_router.get("/", response_model=list[ReviewRead])
async def get_reviews(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    return await get_reviews_helper(db=db, skip=skip, limit=limit)


@review_router.get("/{review_id}", response_model=ReviewRead)
async def get_review(
    review_id: int,
    db: AsyncSession = Depends(get_db),
):
    return await get_review_helper(db=db, review_id=review_id)


@review_router.post("/", response_model=ReviewRead)
async def create_review(
    review_in: ReviewCreate,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    return await create_review_helper(
        db=db,
        review_in=review_in,
        user_id=user.id,
    )

@review_router.patch("/{review_id}", response_model=ReviewRead)
async def update_review(
    review_id: int,
    review_in: ReviewUpdate,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    review = await update_review_helper(db=db, review_id=review_id, review_in=review_in)
    if review.user_id != user.id and not user.is_superuser:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Not allowed to edit this review")
    return review


@review_router.delete("/{review_id}")
async def delete_review(
    review_id: int,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    review = await get_review_helper(db=db, review_id=review_id)
    if review.user_id != user.id and not user.is_superuser:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Not allowed to delete this review")
    return await delete_review_helper(db=db, review_id=review_id)

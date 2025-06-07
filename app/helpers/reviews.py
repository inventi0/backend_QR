from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Review


async def create_review(review_data: ReviewCreate, db: AsyncSession):
    review = Review(**review_data.dict())
    db.add(review)
    await db.commit()
    await db.refresh(review)
    return review


async def get_review_by_id(review_id: int, db: AsyncSession):
    result = await db.execute(select(Review).filter(Review.review_id == review_id))
    review = result.scalars().first()
    if not review:
        raise ValueError("Review not found")
    return review
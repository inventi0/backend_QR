from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import User


async def get_user_by_id(user_id: int, db: AsyncSession):
    result = await db.execute(
        select(User).filter(User.user_id == user_id)
    )
    user = result.scalars().first()
    if not user:
        raise ValueError("User not found")
    return user

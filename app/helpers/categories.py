from select import select

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Category


async def create_category(category_data: CategoryCreate, db: AsyncSession):
    category = Category(**category_data.dict())
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


async def get_category_by_id(category_id: int, db: AsyncSession):
    result = await db.execute(select(Category).filter(Category.category_id == category_id))
    category = result.scalars().first()
    if not category:
        raise ValueError("Category not found")
    return category
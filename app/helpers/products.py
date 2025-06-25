from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Product


async def create_product(product_data: ProductCreate, db: AsyncSession):
    product = Product(**product_data.dict())
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product


async def get_product_by_id(product_id: int, db: AsyncSession):
    result = await db.execute(
        select(Product).filter(Product.product_id == product_id)
    )
    product = result.scalars().first()
    if not product:
        raise ValueError("Product not found")
    return product

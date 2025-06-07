from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Cart


async def create_cart(cart_data: CartCreate, db: AsyncSession):
    cart = Cart(**cart_data.dict())
    db.add(cart)
    await db.commit()
    await db.refresh(cart)
    return cart


async def get_cart_by_user(user_id: int, db: AsyncSession):
    result = await db.execute(select(Cart).filter(Cart.user_id == user_id))
    cart = result.scalars().first()
    if not cart:
        raise ValueError("Cart not found")
    return cart
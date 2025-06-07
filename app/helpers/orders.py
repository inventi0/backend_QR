import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Order


async def create_order(order_data: OrderCreate, db: AsyncSession):
    order = Order(**order_data.dict(), timestamp=datetime.now())
    db.add(order)
    await db.commit()
    await db.refresh(order)
    return order


async def get_order_by_id(order_id: int, db: AsyncSession):
    result = await db.execute(select(Order).filter(Order.order_id == order_id))
    order = result.scalars().first()
    if not order:
        raise ValueError("Order not found")
    return order
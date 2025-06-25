import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Shipping


async def create_shipping(shipping_data: ShippingCreate, db: AsyncSession):
    shipping = Shipping(**shipping_data.dict(), shipping_date=datetime.datetime.now())
    db.add(shipping)
    await db.commit()
    await db.refresh(shipping)
    return shipping


async def get_shipping_by_order(order_id: int, db: AsyncSession):
    result = await db.execute(
        select(Shipping).filter(Shipping.order_id == order_id)
    )
    shipping = result.scalars().first()
    if not shipping:
        raise ValueError("Shipping not found")
    return shipping

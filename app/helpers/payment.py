import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Payment


async def create_payment(payment_data: PaymentCreate, db: AsyncSession):
    payment = Payment(**payment_data.dict(), payment_date=datetime.now())
    db.add(payment)
    await db.commit()
    await db.refresh(payment)
    return payment


async def get_payment_by_order(order_id: int, db: AsyncSession):
    result = await db.execute(select(Payment).filter(Payment.order_id == order_id))
    payment = result.scalars().first()
    if not payment:
        raise ValueError("Payment not found")
    return payment

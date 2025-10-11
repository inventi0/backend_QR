from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.models import Invoice

async def create_invoice(db: AsyncSession, *, order_id: str, amount: str, currency: str,
                         name: str | None, iban: str | None, purpose: str | None,
                         customer_chat_id: int) -> Invoice:
    inv = Invoice(order_id=order_id, amount=amount, currency=currency,
                  name=name, iban=iban, purpose=purpose, customer_chat_id=customer_chat_id)
    db.add(inv)
    await db.flush()
    await db.commit()
    await db.refresh(inv)
    return inv

async def set_provider_and_payment(db: AsyncSession, invoice_id: int, provider: str, payment_id: str):
    await db.execute(update(Invoice).where(Invoice.id == invoice_id).values(provider=provider, payment_id=payment_id))
    await db.commit()

async def set_status_paid(db: AsyncSession, invoice_id: int):
    await db.execute(update(Invoice).where(Invoice.id == invoice_id).values(status="paid"))
    await db.commit()

async def get_invoice(db: AsyncSession, invoice_id: int) -> Invoice | None:
    res = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    return res.scalars().first()

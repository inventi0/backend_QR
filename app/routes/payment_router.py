import os
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from yookassa import Payment, Configuration
from uuid import uuid4
from dotenv import load_dotenv
from app.routes.dependecies import current_user, current_superuser
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.models import Order, User

load_dotenv()

SHOP_ID = os.getenv("YOO_SHOP_ID")
SECRET_KEY = os.getenv("YOO_SECRET_KEY")

Configuration.account_id = SHOP_ID
Configuration.secret_key = SECRET_KEY

payment_router = APIRouter(prefix="/payment", tags=["payment"])


class PaymentRequest(BaseModel):
    order_id: int
    amount: float


@payment_router.post("/create")
async def create_payment(
        req: PaymentRequest,
        user: User = Depends(current_user),   # ← ОБЯЗАТЕЛЬНО!
        session: AsyncSession = Depends(get_db)
):
    # ⚡ 1. Гарантированно ищем заказ ТОЛЬКО ПОЛЬЗОВАТЕЛЯ
    query = (
        select(Order)
        .where(
            Order.id == req.order_id,
            Order.user_id == user.id   # ← ВАЖНО
        )
    )

    result = await session.execute(query)
    order = result.scalar_one_or_none()

    # Если SQLAlchemy отдало кеш — пытаемся принудительно получить из БД
    if not order:
        await session.commit()     # сбрасываем транзакцию, открываем новую
        await session.flush()
        order = await session.get(Order, req.order_id)

        # проверяем повторно
        if not order or order.user_id != user.id:
            raise HTTPException(404, "Order not found")

    # 2. Создаём платёж
    try:
        payment = Payment.create({
            "amount": {
                "value": f"{req.amount:.2f}",
                "currency": "RUB"
            },
            "payment_method_data": {
                "type": "bank_card"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": "http://localhost:5173/payment/success"
            },
            "capture": True,
            "description": f"Оплата заказа #{req.order_id}",
            "metadata": {
                "order_id": req.order_id,
                "user_id": user.id
            }
        }, uuid4())

        # 3. Сохраняем payment_id
        order.payment_id = payment.id
        await session.commit()

        return {
            "payment_id": payment.id,
            "redirect_url": payment.confirmation.confirmation_url,
        }

    except Exception as e:
        raise HTTPException(400, detail=str(e))



@payment_router.post("/webhook")
async def yookassa_webhook(
        request: Request,
        session: AsyncSession = Depends(get_db)
):
    data = await request.json()

    event = data.get("event")
    obj = data.get("object")

    if event == "payment.succeeded":
        order_id = obj["metadata"]["order_id"]

        query = select(Order).where(Order.id == order_id)
        result = await session.execute(query)
        order = result.scalar_one_or_none()

        if order:
            order.status = "paid"
            await session.commit()

    return {"status": "ok"}

from pydantic import BaseModel
from datetime import datetime


class PaymentBase(BaseModel):
    amount: float
    payment_status: bool
    payment_date: datetime
    order_id: int


class PaymentCreate(PaymentBase):
    pass


class PaymentRead(PaymentBase):
    payment_id: int

    class Config:
        orm_mode = True

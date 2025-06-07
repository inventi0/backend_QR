from pydantic import BaseModel
from typing import List
from datetime import datetime
from .order_details_schemas import OrderDetailsRead

class OrderBase(BaseModel):
    order_price: float
    order_status: str
    user_id: int
    order_details: str

class OrderCreate(OrderBase):
    pass

class OrderRead(OrderBase):
    order_id: int
    timestamp: datetime
    details: List[OrderDetailsRead] = []

    class Config:
        orm_mode = True

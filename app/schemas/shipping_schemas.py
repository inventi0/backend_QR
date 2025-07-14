from pydantic import BaseModel
from datetime import datetime


class ShippingBase(BaseModel):
    address: str
    shipping_method: str
    shipping_status: str
    shipping_date: datetime
    order_id: int


class ShippingCreate(ShippingBase):
    pass


class ShippingRead(ShippingBase):
    shipping_id: int

    class Config:
        orm_mode = True

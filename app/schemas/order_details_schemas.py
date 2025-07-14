from pydantic import BaseModel


class OrderDetailsBase(BaseModel):
    product_id: int
    quantity: int
    price: float
    order_id: int
    address: str
    postponed_shipping: bool = False


class OrderDetailsCreate(OrderDetailsBase):
    pass


class OrderDetailsRead(OrderDetailsBase):
    class Config:
        orm_mode = True

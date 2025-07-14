from pydantic import BaseModel
from typing import List
from .cart_item_schemas import CartItemRead


class CartBase(BaseModel):
    total_amount: float
    cart_items: str
    user_id: int


class CartCreate(CartBase):
    pass


class CartRead(CartBase):
    cart_id: int
    items: List[CartItemRead]

    class Config:
        orm_mode = True

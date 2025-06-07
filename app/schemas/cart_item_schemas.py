from pydantic import BaseModel

class CartItemBase(BaseModel):
    cart_id: int
    product_id: int
    quantity: int
    price: float

class CartItemCreate(CartItemBase):
    pass

class CartItemRead(CartItemBase):
    class Config:
        orm_mode = True

from typing import List, Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field, conint


class ProductMini(BaseModel):
    id: int
    type: str
    size: str
    color: str
    img_url: Optional[str] = None

    class Config:
        from_attributes = True
        orm_mode = True


class OrderItemCreateIn(BaseModel):
    product_id: int
    quantity: conint(ge=1) = 1


class OrderCreateIn(BaseModel):
    items: List[OrderItemCreateIn] = Field(..., min_items=1)


class OrderItemOut(BaseModel):
    id: int
    quantity: int
    product: ProductMini

    class Config:
        from_attributes = True
        orm_mode = True


class OrderOut(BaseModel):
    id: int
    created_at: datetime
    status: str
    user_id: int
    items: List[OrderItemOut]

    class Config:
        from_attributes = True
        orm_mode = True

class OrderItemAddIn(BaseModel):
    product_id: int
    quantity: conint(ge=1) = 1


class OrderUpdateIn(BaseModel):
    status: Literal["pending", "processing", "paid", "shipped", "completed", "cancelled", "refunded"]
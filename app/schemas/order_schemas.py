from typing import List, Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field, conint

from app.schemas.product_schemas import ProductMini


class OrderItemCreateIn(BaseModel):
    product_id: int
    quantity: conint(ge=1) = 1

class OrderCreateIn(BaseModel):
    items: List[OrderItemCreateIn] = Field(..., min_items=1)
    
    # Delivery info
    contact_info: str
    country: str
    city: str
    first_name: str
    last_name: str
    delivery_address: str
    zip_code: str

class OrderItemOut(BaseModel):
    id: int
    quantity: conint(ge=1)
    amount: conint(ge=0)
    product: ProductMini

    class Config:
        from_attributes = True
        orm_mode = True

class OrderOut(BaseModel):
    id: int
    created_at: datetime
    status: str
    user_id: int
    total_amount: conint(ge=0)
    
    # Delivery info
    contact_info: Optional[str]
    country: Optional[str]
    city: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    delivery_address: Optional[str]
    zip_code: Optional[str]
    
    items: List[OrderItemOut]

    class Config:
        from_attributes = True
        orm_mode = True

class OrderItemAddIn(BaseModel):
    product_id: int
    quantity: conint(ge=1) = 1

class OrderItemUpdateIn(BaseModel):
    quantity: conint(ge=1)

class OrderUpdateIn(BaseModel):
    status: Literal[
        "pending",
        "processing",
        "paid",
        "shipped",
        "completed",
        "cancelled",
        "refunded",
    ]
from pydantic import BaseModel
from typing import Optional
from .category_schemas import CategoryRead


class ProductBase(BaseModel):
    size: str
    price: float
    color: str
    category_id: int
    qr_code: Optional[str] = None


class ProductCreate(ProductBase):
    pass


class ProductRead(ProductBase):
    product_id: int
    category: CategoryRead

    class Config:
        orm_mode = True

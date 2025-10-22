from typing import Optional, Union
from pydantic import BaseModel, HttpUrl, Field, conint

class ProductCreateIn(BaseModel):
    type: str = Field(..., max_length=255)
    size: str = Field(..., max_length=255)
    color: str = Field(..., max_length=255)
    description: Optional[str] = None
    img_url: Optional[Union[HttpUrl, str]] = None
    # цена в копейках/центах/минимальных единицах (как у тебя в БД — Integer)
    price: conint(ge=0) = Field(..., description="Цена товара в минимальных денежных единицах")

class ProductUpdateIn(BaseModel):
    type: Optional[str] = Field(default=None, max_length=255)
    size: Optional[str] = Field(default=None, max_length=255)
    color: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = None
    img_url: Optional[Union[HttpUrl, str]] = None
    price: Optional[conint(ge=0)] = Field(default=None, description="Цена товара в минимальных денежных единицах")

class ProductMini(BaseModel):
    id: int
    type: str
    size: str
    color: str
    img_url: Optional[str] = None
    price: conint(ge=0)

    class Config:
        from_attributes = True
        orm_mode = True

class ProductOut(BaseModel):
    id: int
    type: str
    size: str
    color: str
    description: Optional[str] = None
    img_url: Optional[Union[HttpUrl, str]] = None
    qr_id: Optional[int] = None
    price: conint(ge=0)

    class Config:
        from_attributes = True
        orm_mode = True
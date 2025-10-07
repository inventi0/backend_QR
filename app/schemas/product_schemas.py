from typing import Optional
from pydantic import BaseModel, HttpUrl, Field

class ProductOut(BaseModel):
    id: int
    type: str
    size: str
    color: str
    description: Optional[str] = None
    img_url: Optional[HttpUrl | str] = None
    qr_id: Optional[int] = None

    class Config:
        from_attributes = True
        orm_mode = True

class ProductUpdateIn(BaseModel):
    type: Optional[str] = Field(default=None, max_length=255)
    size: Optional[str] = Field(default=None, max_length=255)
    color: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = None

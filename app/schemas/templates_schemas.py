from pydantic import BaseModel, Field, HttpUrl
from typing import Optional

class TemplateOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    file_url: HttpUrl | str
    thumb_url: Optional[HttpUrl | str] = None
    owner_user_id: Optional[int] = None

    class Config:
        from_attributes = True
        orm_mode = True

class TemplateUpdateIn(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = None
    thumb_url: Optional[str] = None

class TemplateCountOut(BaseModel):
    user_id: int
    count: int

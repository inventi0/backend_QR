from typing import Optional
from pydantic import BaseModel, Field
from app.schemas.user_schemas import UserOut

class ReviewBase(BaseModel):
    stars: int = Field(..., ge=1, le=5, description="Оценка от 1 до 5")
    content: str = Field(..., min_length=5, description="Текст отзыва")

class ReviewCreate(ReviewBase):
    pass

class ReviewUpdate(BaseModel):
    stars: Optional[int] = Field(None, ge=1, le=5)
    content: Optional[str] = Field(None, min_length=5)

class ReviewRead(ReviewBase):
    id: int
    user: UserOut

    class Config:
        orm_mode = True

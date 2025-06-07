from pydantic import BaseModel
from datetime import datetime

class ReviewBase(BaseModel):
    rating: int
    comment: str
    review_date: datetime
    product_id: int
    user_id: int

class ReviewCreate(ReviewBase):
    pass

class ReviewRead(ReviewBase):
    review_id: int

    class Config:
        orm_mode = True

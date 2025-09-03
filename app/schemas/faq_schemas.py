from pydantic import BaseModel, EmailStr
from typing import Optional


class FAQBase(BaseModel):
    name: str
    question: str
    answer: Optional[str] = None


class FAQCreate(BaseModel):
    name: str
    email: EmailStr
    question: str


class FAQAnswer(BaseModel):
    answer: str


class FAQRead(FAQBase):
    id: int

    class Config:
        orm_mode = True

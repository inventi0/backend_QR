from typing import Optional, List
from pydantic import EmailStr
from fastapi_users.schemas import BaseUser, BaseUserCreate

from app.schemas.cart_schemas import CartRead
from app.schemas.order_schemas import OrderRead
from app.schemas.review_schemas import ReviewRead


class UserRead(BaseUser[int]):
    id: int
    email: EmailStr
    username: str
    is_active: bool = True
    is_superuser: bool = False
    is_verified: bool = False

    class Config:
        orm_mode = True


class UserOut(BaseUser[int]):
    id: int
    email: EmailStr

    orders: Optional[List[OrderRead]] = []
    reviews: Optional[List[ReviewRead]] = []
    cart: Optional[CartRead] = None

    class Config:
        orm_mode = True


class UserCreate(BaseUserCreate):
    username: str
    email: EmailStr
    password: Optional[str] = None
    role_id: int
    is_active: Optional[bool] = True
    is_superuser: Optional[bool] = False
    is_verified: Optional[bool] = False

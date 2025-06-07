from pydantic import BaseModel, EmailStr
from typing import Optional
from fastapi_users.schemas import BaseUser, BaseUserCreate

from app.schemas.cart_schemas import CartRead
from app.schemas.order_schemas import OrderRead
from app.schemas.review_schemas import ReviewRead


class UserRead(BaseUser[int]):
    id: int
    email: str
    username: str
    is_active: bool = True
    is_superuser: bool = False
    is_verified: bool = False

    # orders: Optional[OrderRead]
    # reviews: Optional[ReviewRead]
    # cart: Optional[CartRead]

    class Config:
        orm_mode = True

class UserCreate(BaseUserCreate):
    username: str
    email: str
    password: Optional[str] = None
    role_id: int
    is_active: Optional[bool] = True
    is_superuser: Optional[bool] = False
    is_verified: Optional[bool] = False

class BaseUser(BaseModel):
    username: str
    email: str

class UserOut(BaseUser):
    id: int

    class Config:
        orm_mode = True

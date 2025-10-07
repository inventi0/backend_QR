from typing import Optional
from pydantic import EmailStr
from fastapi_users.schemas import BaseUser, BaseUserCreate


class UserRead(BaseUser[int]):
    id: int
    email: EmailStr
    username: str
    img_url: Optional[str] = None
    is_active: bool = True
    is_superuser: bool = False
    is_verified: bool = False

    class Config:
        orm_mode = True


class UserOut(BaseUser[int]):
    id: int
    email: EmailStr
    username: str
    img_url: Optional[str] = None

    class Config:
        orm_mode = True


class UserCreate(BaseUserCreate):
    email: EmailStr
    username: str
    password: str

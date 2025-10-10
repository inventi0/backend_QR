from typing import Optional
from pydantic import EmailStr
from fastapi_users.schemas import BaseUser, BaseUserCreate, BaseUserUpdate

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

class UserUpdate(BaseUserUpdate):
    username: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    img_url: Optional[str] = None
    role_id: Optional[int] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    is_verified: Optional[bool] = None
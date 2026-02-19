from typing import Optional
from pydantic import EmailStr, BaseModel
from fastapi_users.schemas import BaseUser, BaseUserCreate, BaseUserUpdate

class UserRead(BaseUser[int]):
    id: int
    email: EmailStr
    username: str
    img_url: Optional[str] = None
    is_active: bool = True
    is_superuser: bool = False
    is_verified: bool = False
    is_temporary_data: bool = False

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
    is_temporary_data: bool = False

class UserUpdate(BaseUserUpdate):
    username: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    img_url: Optional[str] = None
    role_id: Optional[int] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    is_verified: Optional[bool] = None

class TemplateSimpleOut(BaseModel):
    id: int
    name: str
    thumb_url: Optional[str] = None
    
    class Config:
        orm_mode = True

class AdminUserDetailedResponse(BaseModel):
    id: int
    email: str
    username: Optional[str] = None
    is_active: bool
    is_superuser: bool
    is_temporary_data: bool
    active_template_id: Optional[int] = None
    templates: list[TemplateSimpleOut] = []
    qr_link: Optional[str] = None

    class Config:
        orm_mode = True
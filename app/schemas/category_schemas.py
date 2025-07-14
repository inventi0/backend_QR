from pydantic import BaseModel


class CategoryBase(BaseModel):
    category: str
    description: str


class CategoryCreate(CategoryBase):
    pass


class CategoryRead(CategoryBase):
    category_id: int

    class Config:
        orm_mode = True

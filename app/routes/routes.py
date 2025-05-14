from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app import models, database #TODO: fix

# Создаем объект роутера
router = APIRouter()

# Функция для получения сессии базы данных
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Роут для создания нового пользователя
@router.post("/users/")
def create_user(user: models.User, db: Session = Depends(get_db)):
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

# Роут для получения всех пользователей
@router.get("/users/")
def get_users(db: Session = Depends(get_db)):
    users = db.query(models.User).all()
    return users

# Роут для создания нового продукта
@router.post("/products/")
def create_product(product: models.Product, db: Session = Depends(get_db)):
    db.add(product)
    db.commit()
    db.refresh(product)
    return product

# Роут для получения всех продуктов
@router.get("/products/")
def get_products(db: Session = Depends(get_db)):
    products = db.query(models.Product).all()
    return products

# Роут для создания заказа
@router.post("/orders/")
def create_order(order: models.Order, db: Session = Depends(get_db)):
    db.add(order)
    db.commit()
    db.refresh(order)
    return order

# Роут для получения всех заказов
@router.get("/orders/")
def get_orders(db: Session = Depends(get_db)):
    orders = db.query(models.Order).all()
    return orders

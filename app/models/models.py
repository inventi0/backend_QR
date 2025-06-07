from fastapi import Depends
from fastapi_users_db_sqlalchemy import SQLAlchemyBaseUserTable, SQLAlchemyUserDatabase
from sqlalchemy import Column, ForeignKey, Integer, String, Float, Boolean, DateTime, Text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import get_db, Base

class User(SQLAlchemyBaseUserTable[int], Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role_id = Column(Integer)
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)

    orders = relationship("Order", back_populates="user")
    reviews = relationship("Review", back_populates="user")
    cart = relationship("Cart", back_populates="user", uselist=False)

async def get_user_db(session: AsyncSession = Depends(get_db)):
    yield SQLAlchemyUserDatabase(session, User)

class Product(Base):
    __tablename__ = "products"
    product_id = Column(Integer, primary_key=True, nullable=False)
    size = Column(String(50), nullable=False)
    price = Column(Float, nullable=False)
    color = Column(String(50), nullable=False)

    # Заменили строковое поле category на внешний ключ category_id,
    # указывающий на поле category_id в таблице categories
    category_id = Column(Integer, ForeignKey("categories.category_id"), nullable=False)

    # Это объектная связь (relationship) — связывает Product с Category
    category = relationship("Category", back_populates="products")

    # Добавлен столбец для QR-кода, который может быть пустым
    qr_code = Column(String, unique=True, nullable=True)

    # Остальные связи оставили без изменений
    order_details = relationship("OrderDetails", back_populates="product")
    reviews = relationship("Review", back_populates="product")
    cart_items = relationship("CartItem", back_populates="product")  # Связь с CartItem добавлена


class Category(Base):
    __tablename__ = "categories"
    category_id = Column(Integer, primary_key=True, nullable=False)
    category = Column(String(50), nullable=False)
    description = Column(String, nullable=False)

    # Это обратная связь: список всех продуктов, относящихся к данной категории
    products = relationship("Product", back_populates="category")


class Review(Base):
    __tablename__ = "reviews"
    review_id = Column(Integer, primary_key=True, nullable=False)
    rating = Column(Integer, nullable=False)
    comment = Column(String, nullable=False)
    review_date = Column(DateTime, nullable=False)
    product_id = Column(Integer, ForeignKey("products.product_id"), nullable=False)  # Исправлено на Integer
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Исправлено на Integer

    # Связи с пользователем и продуктом
    product = relationship("Product", back_populates="reviews")
    user = relationship("User", back_populates="reviews")


class Order(Base):
    __tablename__ = "orders"
    order_id = Column(Integer, primary_key=True, nullable=False)
    timestamp = Column(DateTime, default=datetime.now)
    order_price = Column(Float, nullable=False)
    order_status = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    order_details = Column(String(50), nullable=False)

    # Связи с другими таблицами
    user = relationship("User", back_populates="orders")
    details = relationship("OrderDetails", back_populates="order")
    payment = relationship("Payment", back_populates="order", uselist=False)
    shipping = relationship("Shipping", back_populates="order")


class OrderDetails(Base):
    __tablename__ = "order_details"
    product_id = Column(Integer, ForeignKey("products.product_id"), primary_key=True, nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    order_id = Column(Integer, ForeignKey("orders.order_id"), nullable=False)
    address = Column(String(50), nullable=False)
    postponed_shipping = Column(Boolean, default=False)

    # Связи с продуктом и заказом
    product = relationship("Product", back_populates="order_details")
    order = relationship("Order", back_populates="details")


class Cart(Base):
    __tablename__ = "cart"
    cart_id = Column(Integer, primary_key=True, nullable=False)
    total_amount = Column(Float, nullable=False)
    cart_items = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Связи с пользователем и элементами корзины
    user = relationship("User", back_populates="cart")
    items = relationship("CartItem", back_populates="cart")  # Связь с CartItem


# Добавлены изменения для CartItem: новая таблица CartItems
class CartItem(Base):
    __tablename__ = "cart_items"
    cart_id = Column(Integer, ForeignKey("cart.cart_id"), primary_key=True, nullable=False)
    product_id = Column(Integer, ForeignKey("products.product_id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)

    # Связи с корзиной и продуктом
    product = relationship("Product", back_populates="cart_items")
    cart = relationship("Cart", back_populates="items")


class Payment(Base):
    __tablename__ = "payments"
    payment_id = Column(Integer, primary_key=True, nullable=False)
    amount = Column(Float, nullable=False)
    payment_status = Column(Boolean, nullable=False)
    payment_date = Column(DateTime, nullable=False)
    order_id = Column(Integer, ForeignKey("orders.order_id"), nullable=False)  # Исправлено на Integer

    # Связь с заказом
    order = relationship("Order", back_populates="payment")


class Shipping(Base):
    __tablename__ = "shipping"
    shipping_id = Column(Integer, primary_key=True, nullable=False)
    address = Column(String(50), nullable=False)
    shipping_method = Column(String(20), nullable=False)
    shipping_status = Column(String(20), nullable=False)
    shipping_date = Column(DateTime, nullable=False)
    order_id = Column(Integer, ForeignKey("orders.order_id"), nullable=False)  # Исправлено на Integer

    # Связь с заказом
    order = relationship("Order", back_populates="shipping")

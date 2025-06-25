from fastapi import Depends
from fastapi_users_db_sqlalchemy import SQLAlchemyBaseUserTable, SQLAlchemyUserDatabase
from sqlalchemy import Column, ForeignKey, Integer, String, Float, Boolean, DateTime
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

    orders = relationship(
        "Order",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )
    reviews = relationship(
        "Review",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )
    cart = relationship(
        "Cart",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )


async def get_user_db(session: AsyncSession = Depends(get_db)):
    yield SQLAlchemyUserDatabase(session, User)


class Product(Base):
    __tablename__ = "products"
    product_id = Column(Integer, primary_key=True, nullable=False)
    size = Column(String(50), nullable=False)
    price = Column(Float, nullable=False)
    color = Column(String(50), nullable=False)
    category_id = Column(
        Integer,
        ForeignKey("categories.category_id", ondelete="CASCADE"),
        nullable=False,
    )
    qr_code = Column(String, unique=True, nullable=True)

    category = relationship(
        "Category", back_populates="products", passive_deletes=True, lazy="selectin"
    )
    order_details = relationship(
        "OrderDetails",
        back_populates="product",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )
    reviews = relationship(
        "Review",
        back_populates="product",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )
    cart_items = relationship(
        "CartItem",
        back_populates="product",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )


class Category(Base):
    __tablename__ = "categories"
    category_id = Column(Integer, primary_key=True, nullable=False)
    category = Column(String(50), nullable=False)
    description = Column(String, nullable=False)

    products = relationship(
        "Product",
        back_populates="category",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )


class Review(Base):
    __tablename__ = "reviews"
    review_id = Column(Integer, primary_key=True, nullable=False)
    rating = Column(Integer, nullable=False)
    comment = Column(String, nullable=False)
    review_date = Column(DateTime, nullable=False)
    product_id = Column(
        Integer, ForeignKey("products.product_id", ondelete="CASCADE"), nullable=False
    )
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    product = relationship(
        "Product", back_populates="reviews", passive_deletes=True, lazy="selectin"
    )
    user = relationship(
        "User", back_populates="reviews", passive_deletes=True, lazy="selectin"
    )


class Order(Base):
    __tablename__ = "orders"
    order_id = Column(Integer, primary_key=True, nullable=False)
    timestamp = Column(DateTime, default=datetime.now)
    order_price = Column(Float, nullable=False)
    order_status = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    order_details = Column(String(50), nullable=False)

    user = relationship(
        "User", back_populates="orders", passive_deletes=True, lazy="selectin"
    )
    details = relationship(
        "OrderDetails",
        back_populates="order",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )
    payment = relationship(
        "Payment",
        back_populates="order",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )
    shipping = relationship(
        "Shipping",
        back_populates="order",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )


class OrderDetails(Base):
    __tablename__ = "order_details"
    product_id = Column(
        Integer, ForeignKey("products.product_id", ondelete="CASCADE"), primary_key=True, nullable=False
    )
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    order_id = Column(
        Integer, ForeignKey("orders.order_id", ondelete="CASCADE"), nullable=False
    )
    address = Column(String(50), nullable=False)
    postponed_shipping = Column(Boolean, default=False)

    product = relationship(
        "Product", back_populates="order_details", passive_deletes=True, lazy="selectin"
    )
    order = relationship(
        "Order", back_populates="details", passive_deletes=True, lazy="selectin"
    )


class Cart(Base):
    __tablename__ = "cart"
    cart_id = Column(Integer, primary_key=True, nullable=False)
    total_amount = Column(Float, nullable=False)
    cart_items = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    user = relationship(
        "User", back_populates="cart", passive_deletes=True, lazy="selectin"
    )
    items = relationship(
        "CartItem",
        back_populates="cart",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )


class CartItem(Base):
    __tablename__ = "cart_items"
    cart_id = Column(
        Integer, ForeignKey("cart.cart_id", ondelete="CASCADE"), primary_key=True, nullable=False
    )
    product_id = Column(
        Integer, ForeignKey("products.product_id", ondelete="CASCADE"), nullable=False
    )
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)

    product = relationship(
        "Product", back_populates="cart_items", passive_deletes=True, lazy="selectin"
    )
    cart = relationship(
        "Cart", back_populates="items", passive_deletes=True, lazy="selectin"
    )


class Payment(Base):
    __tablename__ = "payments"
    payment_id = Column(Integer, primary_key=True, nullable=False)
    amount = Column(Float, nullable=False)
    payment_status = Column(Boolean, nullable=False)
    payment_date = Column(DateTime, nullable=False)
    order_id = Column(
        Integer, ForeignKey("orders.order_id", ondelete="CASCADE"), nullable=False
    )

    order = relationship(
        "Order", back_populates="payment", passive_deletes=True, lazy="selectin"
    )


class Shipping(Base):
    __tablename__ = "shipping"
    shipping_id = Column(Integer, primary_key=True, nullable=False)
    address = Column(String(50), nullable=False)
    shipping_method = Column(String(20), nullable=False)
    shipping_status = Column(String(20), nullable=False)
    shipping_date = Column(DateTime, nullable=False)
    order_id = Column(
        Integer, ForeignKey("orders.order_id", ondelete="CASCADE"), nullable=False
    )

    order = relationship(
        "Order", back_populates="shipping", passive_deletes=True, lazy="selectin"
    )

from fastapi import Depends
from fastapi_users_db_sqlalchemy import SQLAlchemyBaseUserTable, SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, ForeignKey, Text, DateTime, Boolean
)
from sqlalchemy.orm import relationship
from app.database import get_db, Base

class User(SQLAlchemyBaseUserTable[int], Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role_id = Column(Integer)
    img_url = Column(String)
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
        lazy="selectin",
    )
    canvases = relationship(
        "Canvas",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    qr = relationship(
        "QRCode",
        back_populates="user",
        uselist=False,
        lazy="selectin",
        cascade="all, delete-orphan",
    )


async def get_user_db(session: AsyncSession = Depends(get_db)):
    yield SQLAlchemyUserDatabase(session, User)

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    type = Column(String, nullable=False)
    size = Column(String, nullable=False)
    color = Column(String, nullable=False)
    description = Column(Text)
    img_url = Column(String)

    qr_id = Column(Integer, ForeignKey("qrcodes.id"), nullable=True)
    qr = relationship("QRCode", back_populates="products", lazy="selectin")

    order_items = relationship("OrderItem", back_populates="product")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    status = Column(String, default="pending", nullable=False)

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    user = relationship("User", back_populates="orders", lazy="selectin")
    items = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True)
    quantity = Column(Integer, default=1, nullable=False)

    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)

    order = relationship("Order", back_populates="items", lazy="selectin")
    product = relationship("Product", back_populates="order_items", lazy="selectin")


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True)
    stars = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    user = relationship("User", back_populates="reviews", lazy="selectin")

class QRCode(Base):
    __tablename__ = "qrcodes"

    id = Column(Integer, primary_key=True)

    code = Column(String, unique=True, nullable=False)

    link = Column(String, nullable=True)

    current_canvas_id = Column(Integer, ForeignKey("canvases.id"), nullable=True)
    current_canvas = relationship(
        "Canvas",
        foreign_keys=[current_canvas_id],
        post_update=True,
        lazy="selectin",
    )

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    user = relationship("User", back_populates="qr", lazy="selectin")

    canvases = relationship(
        "Canvas",
        back_populates="qr",
        cascade="all, delete-orphan",
        lazy="selectin",
        foreign_keys="Canvas.qr_id",
    )

    products = relationship("Product", back_populates="qr", lazy="selectin")


class Canvas(Base):
    __tablename__ = "canvases"

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    image_url = Column(String)
    public_url = Column(String, nullable=True)

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)

    qr_id = Column(Integer, ForeignKey("qrcodes.id", ondelete="CASCADE"), nullable=True)
    qr = relationship("QRCode", back_populates="canvases", foreign_keys=[qr_id], lazy="selectin")

    user = relationship("User", back_populates="canvases", lazy="selectin")

class FAQ(Base):
    __tablename__ = "faqs"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text)

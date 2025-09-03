from fastapi import Depends
from fastapi_users_db_sqlalchemy import SQLAlchemyBaseUserTable, SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime, Boolean, Float
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

    faqs = relationship(
        "FAQ",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

async def get_user_db(session: AsyncSession = Depends(get_db)):
    yield SQLAlchemyUserDatabase(session, User)

class Product(Base):
    __tablename__ = 'products'

    id = Column(Integer, primary_key=True)
    type = Column(String, nullable=False)
    size = Column(String, nullable=False)
    color = Column(String, nullable=False)
    description = Column(Text)

    order_items = relationship('OrderItem', back_populates='product')
    canvases = relationship('Canvas', back_populates='product')


class Order(Base):
    __tablename__ = 'orders'

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="pending")

    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)

    user = relationship('User', back_populates='orders')
    items = relationship('OrderItem', back_populates='order', cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = 'order_items'

    id = Column(Integer, primary_key=True)
    quantity = Column(Integer, default=1)

    order_id = Column(Integer, ForeignKey('orders.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)

    order = relationship('Order', back_populates='items')
    product = relationship('Product', back_populates='order_items')


class Review(Base):
    __tablename__ = 'reviews'

    id = Column(Integer, primary_key=True)
    stars = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)

    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)

    user = relationship("User", back_populates="reviews", lazy="selectin")


class Canvas(Base):
    __tablename__ = 'canvases'

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    image_url = Column(String)

    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'))

    user = relationship('User', back_populates='canvases')
    product = relationship('Product', back_populates='canvases')
    qrcode = relationship('QRCode', back_populates='canvas', uselist=False, cascade="all, delete-orphan")

class QRCode(Base):
    __tablename__ = 'qrcodes'

    id = Column(Integer, primary_key=True)
    link = Column(String, nullable=False)

    canvas_id = Column(Integer, ForeignKey('canvases.id'), unique=True, nullable=False)

    canvas = relationship('Canvas', back_populates='qrcode')


class FAQ(Base):
    __tablename__ = 'faqs'

    id = Column(Integer, primary_key=True)
    question = Column(Text, nullable=False)
    answer = Column(Text)

    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)

    user = relationship('User', back_populates='faqs')

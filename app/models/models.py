from fastapi import Depends
from fastapi_users_db_sqlalchemy import SQLAlchemyBaseUserTable, SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, ForeignKey, Text, DateTime, Boolean, func
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
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

    templates = relationship(
        "Template",
        back_populates="owner",
        cascade="all, delete-orphan",
        lazy="selectin",
        foreign_keys="Template.owner_user_id",
    )

    editor = relationship(
        "Editor",
        back_populates="user",
        uselist=False,
        lazy="selectin",
        cascade="all, delete-orphan",
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

class Template(Base):
    """
    Шаблон = ссылка на файл, который открывает редактор.
    Можно хранить глобальную библиотеку (owner_user_id = NULL)
    и пользовательские шаблоны (owner_user_id = user.id).
    """
    __tablename__ = "templates"

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    name = Column(String, nullable=False)
    file_url = Column(String, nullable=False)
    thumb_url = Column(String, nullable=True)
    description = Column(Text, nullable=True)

    owner_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    owner = relationship("User", back_populates="templates", lazy="selectin")

class Editor(Base):
    """
    Редактор пользователя. Имеет стабильный public_id (slug/uuid),
    и хранит активный шаблон (current_template_id).
    """
    __tablename__ = "editors"

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    public_id = Column(String, unique=True, nullable=False)

    current_template_id = Column(Integer, ForeignKey("templates.id", ondelete="SET NULL"), nullable=True)
    current_template = relationship("Template", foreign_keys=[current_template_id], lazy="selectin")

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    user = relationship("User", back_populates="editor", lazy="selectin")

    qr = relationship("QRCode", back_populates="editor", uselist=False, lazy="selectin")

class QRCode(Base):
    """
    Один QR на пользователя. Ведёт на его редактор.
    Нет связи с шаблонами — только с Editor.
    """
    __tablename__ = "qrcodes"

    id = Column(Integer, primary_key=True)

    code = Column(String, unique=True, nullable=False)

    link = Column(String, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    user = relationship("User", back_populates="qr", lazy="selectin")

    editor_id = Column(Integer, ForeignKey("editors.id", ondelete="CASCADE"), unique=True, nullable=False)
    editor = relationship("Editor", back_populates="qr", lazy="selectin")

    products = relationship("Product", back_populates="qr", lazy="selectin")

class FAQ(Base):
    __tablename__ = "faqs"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text)

class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[str] = mapped_column(String(64), index=True)
    amount: Mapped[str] = mapped_column(String(32))
    currency: Mapped[str] = mapped_column(String(8))
    name: Mapped[str] = mapped_column(String(128), nullable=True)
    iban: Mapped[str] = mapped_column(String(128), nullable=True)
    purpose: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    customer_chat_id: Mapped[int] = mapped_column(Integer, index=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=True)
    payment_id: Mapped[str] = mapped_column(String(128), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

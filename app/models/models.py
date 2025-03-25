from sqlalchemy import Column, ForeignKey, Integer, String, Float, Boolean, DateTime, TIMESTAMP, Text, CHAR
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    user_id = Column(Integer, primary_key=True, nullable=False)
    email = Column(String(50), nullable=False)
    order_history = Column(Text, nullable=False)
    review_history = Column(Text, nullable=False)
    password = Column(String, nullable=False)

    orders = relationship("Order", back_populates="user")
    reviews = relationship("Review", back_populates="user")
    cart = relationship("Cart", back_populates="user", uselist=False)

class Product(Base):
    __tablename__ = "products"
    product_id = Column(Integer, primary_key=True, nullable=False)
    size = Column(String(50), nullable=False)
    price = Column(Float, nullable=False)
    color = Column(String(50), nullable=False)
    category = Column(String, nullable=False)

    category = relationship("Category", back_populates="products")
    order_details = relationship("OrderDetails", back_populates="product")
    reviews = relationship("Review", back_populates="product")
    cart_items = relationship("CartItem", back_populates="product")

class Category(Base):
    __tablename__ = "categories"
    category_id = Column(Integer, primary_key=True, nullable=False)
    category = Column(String(50), nullable=False)
    description = Column(String, nullable=False)

    products = relationship("Product", back_populates="category")


class Review(Base):
    __tablename__ = "reviews"
    review_id = Column(Integer, primary_key=True, nullable=False)
    rating = Column(Integer, nullable=False)
    comment = Column(String, nullable=False)
    review_date = Column(DateTime, nullable=False)
    product_id = Column(String(50), ForeignKey("products.product_id"), nullable=False)
    user_id = Column(String(50), ForeignKey("users.user_id"), nullable=False)

    product = relationship("Product", back_populates="reviews")
    user = relationship("User", back_populates="reviews")

class Order(Base):
    __tablename__ = "orders"
    order_id = Column(Integer, primary_key=True, nullable=False)
    timestamp = Column(DateTime, default=datetime.now)
    order_price = Column(Float, nullable=False)
    order_status = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    order_details = Column(String(50), nullable=False)

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

    product = relationship("Product", back_populates="order_details")
    order = relationship("Order", back_populates="details")

class Cart(Base):
    __tablename__ = "cart"
    cart_id = Column(Integer, primary_key=True, nullable=False)
    total_amount = Column(Float, nullable=False)
    cart_items = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)

    user = relationship("User", back_populates="cart")
    items = relationship("CartItem", back_populates="cart")

class CartItems(Base):
    __tablename__ = "cart_items"
    cart_id = Column(Integer, ForeignKey("cart.cart_id"), primary_key=True, nullable=False)
    product_id = Column(Integer, ForeignKey("products.product_id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)

    product = relationship("Product", back_populates="cart_items")
    cart = relationship("Cart", back_populates="items")

class Payment(Base):
    __tablename__ = "payments"
    payment_id = Column(Integer, primary_key=True, nullable=False)
    amount = Column(Float, nullable=False)
    payment_status = Column(Boolean, nullable=False)
    payment_date = Column(DateTime, nullable=False)
    order_id = Column(String(50), ForeignKey("orders.order_id"), nullable=False)

    order = relationship("Order", back_populates="payment")

class Shipping(Base):
    __tablename__ = "shipping"
    shipping_id = Column(Integer, primary_key=True, nullable=False)
    address = Column(String(50), nullable=False)
    shipping_method = Column(String(20), nullable=False)
    shipping_status = Column(String(20), nullable=False)
    shipping_date = Column(DateTime, nullable=False)
    order_id = Column(Integer, ForeignKey("orders.order_id"), nullable=False)

    order = relationship("Order", back_populates="shipping")

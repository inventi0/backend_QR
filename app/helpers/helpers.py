from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError

from app.models.models import User, Product, Category, Review, Order, Cart, Payment, Shipping
from app.schemas import UserCreate, ProductCreate, CategoryCreate, ReviewCreate, OrderCreate, CartCreate, PaymentCreate, ShippingCreate


async def create_user(user_data: UserCreate, db: AsyncSession):
    user = User(**user_data.dict())
    try:
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user
    except IntegrityError:
        await db.rollback()
        raise ValueError("User with this email already exists")


async def get_user_by_id(user_id: int, db: AsyncSession):
    result = await db.execute(select(User).filter(User.user_id == user_id))
    user = result.scalars().first()
    if not user:
        raise ValueError("User not found")
    return user


async def create_product(product_data: ProductCreate, db: AsyncSession):
    product = Product(**product_data.dict())
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product


async def get_product_by_id(product_id: int, db: AsyncSession):
    result = await db.execute(select(Product).filter(Product.product_id == product_id))
    product = result.scalars().first()
    if not product:
        raise ValueError("Product not found")
    return product


async def create_category(category_data: CategoryCreate, db: AsyncSession):
    category = Category(**category_data.dict())
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


async def get_category_by_id(category_id: int, db: AsyncSession):
    result = await db.execute(select(Category).filter(Category.category_id == category_id))
    category = result.scalars().first()
    if not category:
        raise ValueError("Category not found")
    return category


async def create_review(review_data: ReviewCreate, db: AsyncSession):
    review = Review(**review_data.dict())
    db.add(review)
    await db.commit()
    await db.refresh(review)
    return review


async def get_review_by_id(review_id: int, db: AsyncSession):
    result = await db.execute(select(Review).filter(Review.review_id == review_id))
    review = result.scalars().first()
    if not review:
        raise ValueError("Review not found")
    return review


async def create_order(order_data: OrderCreate, db: AsyncSession):
    order = Order(**order_data.dict(), timestamp=datetime.now())
    db.add(order)
    await db.commit()
    await db.refresh(order)
    return order


async def get_order_by_id(order_id: int, db: AsyncSession):
    result = await db.execute(select(Order).filter(Order.order_id == order_id))
    order = result.scalars().first()
    if not order:
        raise ValueError("Order not found")
    return order


async def create_cart(cart_data: CartCreate, db: AsyncSession):
    cart = Cart(**cart_data.dict())
    db.add(cart)
    await db.commit()
    await db.refresh(cart)
    return cart


async def get_cart_by_user(user_id: int, db: AsyncSession):
    result = await db.execute(select(Cart).filter(Cart.user_id == user_id))
    cart = result.scalars().first()
    if not cart:
        raise ValueError("Cart not found")
    return cart


async def create_payment(payment_data: PaymentCreate, db: AsyncSession):
    payment = Payment(**payment_data.dict(), payment_date=datetime.now())
    db.add(payment)
    await db.commit()
    await db.refresh(payment)
    return payment


async def get_payment_by_order(order_id: int, db: AsyncSession):
    result = await db.execute(select(Payment).filter(Payment.order_id == order_id))
    payment = result.scalars().first()
    if not payment:
        raise ValueError("Payment not found")
    return payment


async def create_shipping(shipping_data: ShippingCreate, db: AsyncSession):
    shipping = Shipping(**shipping_data.dict(), shipping_date=datetime.now())
    db.add(shipping)
    await db.commit()
    await db.refresh(shipping)
    return shipping


async def get_shipping_by_order(order_id: int, db: AsyncSession):
    result = await db.execute(select(Shipping).filter(Shipping.order_id == order_id))
    shipping = result.scalars().first()
    if not shipping:
        raise ValueError("Shipping not found")
    return shipping

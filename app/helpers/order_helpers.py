from typing import List, Sequence, Tuple
from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.models import Order, OrderItem, Product, User


async def _order_with_items_query(order_id: int):
    return (
        select(Order)
        .where(Order.id == order_id)
        .options(
            selectinload(Order.items).selectinload(OrderItem.product)
        )
    )


async def get_order_secure(
    db: AsyncSession, requester: User, order_id: int
) -> Order:
    """Вернёт заказ, если пользователь владелец или суперюзер, иначе 403."""
    order = (await db.execute(await _order_with_items_query(order_id))).scalars().first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if (order.user_id != requester.id) and (not requester.is_superuser):
        raise HTTPException(status_code=403, detail="Forbidden")
    return order


async def list_orders_for_user(
    db: AsyncSession, requester: User, *, limit: int = 50, offset: int = 0
) -> Sequence[Order]:
    q = (
        select(Order)
        .where(Order.user_id == requester.id)
        .order_by(Order.created_at.desc())
        .limit(limit)
        .offset(offset)
        .options(selectinload(Order.items).selectinload(OrderItem.product))
    )
    return (await db.execute(q)).scalars().all()


async def list_all_orders(
    db: AsyncSession, *, limit: int = 50, offset: int = 0
) -> Sequence[Order]:
    q = (
        select(Order)
        .order_by(Order.created_at.desc())
        .limit(limit)
        .offset(offset)
        .options(selectinload(Order.items).selectinload(OrderItem.product))
    )
    return (await db.execute(q)).scalars().all()


async def create_order(
    db: AsyncSession, requester: User, items: List[Tuple[int, int]]
) -> Order:
    """
    items: список (product_id, quantity). Создаёт заказ пользователя и OrderItem'ы.
    Если один и тот же product_id встречается несколько раз — суммируем quantity.
    """
    if not items:
        raise HTTPException(status_code=400, detail="Items required")

    merged: dict[int, int] = {}
    for pid, qty in items:
        if qty < 1:
            raise HTTPException(status_code=400, detail="Quantity must be >= 1")
        merged[pid] = merged.get(pid, 0) + qty

    product_ids = list(merged.keys())
    existing = (
        await db.execute(select(Product.id).where(Product.id.in_(product_ids)))
    ).scalars().all()
    missing = set(product_ids) - set(existing)
    if missing:
        raise HTTPException(
            status_code=404,
            detail=f"Products not found: {sorted(missing)}",
        )

    order = Order(user_id=requester.id, status="pending")
    db.add(order)
    await db.flush()

    for pid, qty in merged.items():
        db.add(OrderItem(order_id=order.id, product_id=pid, quantity=qty))

    await db.commit()
    order = (
        await db.execute(await _order_with_items_query(order.id))
    ).scalars().first()
    return order


async def admin_add_item_to_order(
    db: AsyncSession, requester: User, order_id: int, *, product_id: int, quantity: int
) -> Order:
    """Суперюзер: добавить позицию; если уже есть — увеличить quantity."""
    if not requester.is_superuser:
        raise HTTPException(status_code=403, detail="Forbidden")

    order = (await db.execute(await _order_with_items_query(order_id))).scalars().first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    product = await db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if quantity < 1:
        raise HTTPException(status_code=400, detail="Quantity must be >= 1")

    existing_item = None
    for it in order.items:
        if it.product_id == product_id:
            existing_item = it
            break

    if existing_item:
        existing_item.quantity += quantity
    else:
        db.add(OrderItem(order_id=order.id, product_id=product_id, quantity=quantity))

    await db.commit()
    order = (await db.execute(await _order_with_items_query(order_id))).scalars().first()
    return order


async def admin_remove_item_from_order(
    db: AsyncSession, requester: User, order_id: int, order_item_id: int
) -> Order:
    """Суперюзер: удалить одну позицию заказа (по order_item_id)."""
    if not requester.is_superuser:
        raise HTTPException(status_code=403, detail="Forbidden")

    order = (await db.execute(await _order_with_items_query(order_id))).scalars().first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    target = None
    for it in order.items:
        if it.id == order_item_id:
            target = it
            break
    if not target:
        raise HTTPException(status_code=404, detail="Order item not found")

    await db.delete(target)
    await db.commit()

    order = (await db.execute(await _order_with_items_query(order_id))).scalars().first()
    return order


async def admin_delete_order(
    db: AsyncSession, requester: User, order_id: int
) -> None:
    """Суперюзер: удалить заказ целиком."""
    if not requester.is_superuser:
        raise HTTPException(status_code=403, detail="Forbidden")

    order = await db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    await db.delete(order)
    await db.commit()

ALLOWED_ORDER_STATUSES = {"pending", "processing", "paid", "shipped", "completed", "cancelled", "refunded"}
async def admin_update_order_status(
    db: AsyncSession,
    requester: User,
    order_id: int,
    *,
    status: str,
) -> Order:
    """Суперюзер: сменить статус заказа."""
    if not requester.is_superuser:
        raise HTTPException(status_code=403, detail="Forbidden")

    if status not in ALLOWED_ORDER_STATUSES:
        raise HTTPException(status_code=400, detail=f"Unsupported status '{status}'")

    order = (await db.execute(await _order_with_items_query(order_id))).scalars().first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order.status = status
    await db.commit()

    order = (await db.execute(await _order_with_items_query(order_id))).scalars().first()
    return order
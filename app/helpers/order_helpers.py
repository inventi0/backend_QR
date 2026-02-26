from typing import List, Sequence, Tuple, Optional
from fastapi import HTTPException
from sqlalchemy import select, func, asc, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from app.models.models import Order, OrderItem, Product, User

async def _order_with_items_query(order_id: int):
    return (
        select(Order)
        .where(Order.id == order_id)
        .options(
            selectinload(Order.items).selectinload(OrderItem.product)
        )
    )

async def recompute_order_total(db: AsyncSession, order: Order) -> None:
    """Пересчитать total_amount как сумму amounts всех позиций."""
    order.total_amount = sum((it.amount or 0) for it in order.items)
    await db.flush()  # без commit: используем там, где изменяем позиции

def set_item_quantity_preserving_unit_price(item: OrderItem, new_qty: int) -> None:
    """
    Обновляет количество в позиции, сохраняет историческую цену за единицу.
    Если позиция новая и amount ещё None — используйте явную установку amount = qty * product.price.
    """
    if new_qty < 1:
        raise HTTPException(status_code=400, detail="Quantity must be >= 1")

    if item.amount is None:
        # fallback: если не зафиксирована цена — считаем от текущей цены товара
        unit_price = item.product.price or 0
    else:
        # историческая цена за единицу
        if item.quantity <= 0:
            unit_price = item.product.price or 0
        else:
            unit_price = item.amount // item.quantity

    item.quantity = new_qty
    item.amount = unit_price * new_qty

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
    db: AsyncSession,
    limit: int = 50,
    offset: int = 0,
    email: Optional[str] = None,
    statuses: Optional[str] = None,
    sort: Optional[str] = None,
) -> List[Order]:
    stmt = (
        select(Order)
        .options(
            joinedload(Order.user),
            joinedload(Order.items),
        )
    )

    # фильтр по email
    if email:
        email_like = f"%{email.strip().lower()}%"
        # join с User
        stmt = stmt.join(User, User.id == Order.user_id)
        stmt = stmt.where(User.email.ilike(email_like))

    if statuses:
        values = [s.strip() for s in statuses.split(",") if s.strip()]
        if values:
            stmt = stmt.where(Order.status.in_(values))

    if sort == "total_asc":
        stmt = stmt.order_by(asc(Order.total_amount if hasattr(Order, "total_amount") else Order.total_price))
    elif sort == "total_desc":
        stmt = stmt.order_by(desc(Order.total_amount if hasattr(Order, "total_amount") else Order.total_price))
    elif sort == "created_asc":
        stmt = stmt.order_by(asc(Order.created_at))  # поле подгони, если называется иначе
    elif sort == "created_desc":
        stmt = stmt.order_by(desc(Order.created_at))
    else:
        stmt = stmt.order_by(desc(Order.id))

    stmt = stmt.limit(limit).offset(offset)
    result = await db.execute(stmt)
    rows = result.scalars().unique().all()
    return rows

async def create_order(
    db: AsyncSession, requester: User, items: List[Tuple[int, int]],
    contact_info: Optional[str] = None, country: Optional[str] = None,
    city: Optional[str] = None, first_name: Optional[str] = None,
    last_name: Optional[str] = None, delivery_address: Optional[str] = None,
    zip_code: Optional[str] = None
) -> Order:
    """
    items: список (product_id, quantity). Создаёт заказ пользователя и позиции.
    Если один и тот же product_id встречается несколько раз — суммируем quantity.
    Для каждой позиции фиксируем amount = quantity * product.price.
    """
    if not items:
        raise HTTPException(status_code=400, detail="Items required")

    merged: dict[int, int] = {}
    for pid, qty in items:
        if qty < 1:
            raise HTTPException(status_code=400, detail="Quantity must be >= 1")
        merged[pid] = merged.get(pid, 0) + qty

    product_ids = list(merged.keys())
    products = (
        await db.execute(select(Product).where(Product.id.in_(product_ids)))
    ).scalars().all()
    if len(products) != len(product_ids):
        existing_ids = {p.id for p in products}
        missing = sorted(set(product_ids) - existing_ids)
        raise HTTPException(status_code=404, detail=f"Products not found: {missing}")

    # map id -> Product
    product_map = {p.id: p for p in products}

    order = Order(
        user_id=requester.id, status="pending", total_amount=0,
        contact_info=contact_info, country=country, city=city,
        first_name=first_name, last_name=last_name, 
        delivery_address=delivery_address, zip_code=zip_code
    )
    db.add(order)
    await db.flush()  # получаем order.id

    total = 0
    for pid, qty in merged.items():
        prod = product_map[pid]
        item_amount = qty * (prod.price or 0)
        db.add(OrderItem(order_id=order.id, product_id=pid, quantity=qty, amount=item_amount))
        total += item_amount

    order.total_amount = total
    await db.commit()

    order = (await db.execute(await _order_with_items_query(order.id))).scalars().first()
    return order

async def admin_add_item_to_order(
    db: AsyncSession, requester: User, order_id: int, *, product_id: int, quantity: int
) -> Order:
    """Суперюзер: добавить позицию; если уже есть — увеличить quantity, сохраняя историческую цену за ед."""
    if not requester.is_superuser:
        raise HTTPException(status_code=403, detail="Forbidden")
    if quantity < 1:
        raise HTTPException(status_code=400, detail="Quantity must be >= 1")

    order = (await db.execute(await _order_with_items_query(order_id))).scalars().first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    product = await db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    existing_item = next((it for it in order.items if it.product_id == product_id), None)

    if existing_item:
        # Сохраняем историческую цену за единицу
        new_qty = existing_item.quantity + quantity
        set_item_quantity_preserving_unit_price(existing_item, new_qty)
    else:
        # Новая позиция: фиксируем цену "сейчас"
        amount = quantity * (product.price or 0)
        db.add(OrderItem(order_id=order.id, product_id=product_id, quantity=quantity, amount=amount))

    await db.flush()
    await recompute_order_total(db, order)
    await db.commit()

    order = (await db.execute(await _order_with_items_query(order_id))).scalars().first()
    return order

async def admin_update_order_item_quantity(
    db: AsyncSession, requester: User, order_id: int, order_item_id: int, *, quantity: int
) -> Order:
    """Суперюзер: изменить количество в позиции, сохранив историческую цену за единицу."""
    if not requester.is_superuser:
        raise HTTPException(status_code=403, detail="Forbidden")
    if quantity < 1:
        raise HTTPException(status_code=400, detail="Quantity must be >= 1")

    order = (await db.execute(await _order_with_items_query(order_id))).scalars().first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    target = next((it for it in order.items if it.id == order_item_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Order item not found")

    set_item_quantity_preserving_unit_price(target, quantity)
    await db.flush()
    await recompute_order_total(db, order)
    await db.commit()

    order = (await db.execute(await _order_with_items_query(order_id))).scalars().first()
    return order

async def admin_remove_item_from_order(
    db: AsyncSession, requester: User, order_id: int, order_item_id: int
) -> Order:
    """Суперюзер: удалить одну позицию заказа (по order_item_id) и пересчитать total_amount."""
    if not requester.is_superuser:
        raise HTTPException(status_code=403, detail="Forbidden")

    order = (await db.execute(await _order_with_items_query(order_id))).scalars().first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    target = next((it for it in order.items if it.id == order_item_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Order item not found")

    await db.delete(target)
    await db.flush()
    await recompute_order_total(db, order)
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

async def admin_update_order_delivery(
    db: AsyncSession, requester: User, order_id: int, delivery_data: dict
) -> Order:
    """Суперюзер: изменить данные доставки заказа."""
    if not requester.is_superuser:
        raise HTTPException(status_code=403, detail="Forbidden")

    order = (await db.execute(await _order_with_items_query(order_id))).scalars().first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    for key, value in delivery_data.items():
        if hasattr(order, key):
            setattr(order, key, value)
            
    await db.commit()

    order = (await db.execute(await _order_with_items_query(order_id))).scalars().first()
    return order
import os
from typing import List, Sequence, Tuple, Optional
from fastapi import HTTPException
from sqlalchemy import select, func, asc, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from app.models.models import Order, OrderItem, Product, User
from app.delivery.yandex import YandexDeliveryClient
from app.logging_config import app_logger

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
    zip_code: Optional[str] = None,
    use_yandex_delivery: bool = False
) -> Order:
    """
    items: список (product_id, quantity). Создаёт заказ пользователя и позиции.
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

    product_map = {p.id: p for p in products}

    order = Order(
        user_id=requester.id, status="pending", total_amount=0,
        contact_info=contact_info, country=country, city=city,
        first_name=first_name, last_name=last_name, 
        delivery_address=delivery_address, zip_code=zip_code
    )
    db.add(order)
    await db.flush()

    total = 0
    yandex_items = []
    for pid, qty in merged.items():
        prod = product_map[pid]
        item_amount = qty * (prod.price or 0)
        db.add(OrderItem(order_id=order.id, product_id=pid, quantity=qty, amount=item_amount))
        total += item_amount
        
        # Подготовка данных для Яндекса (футболка по умолчанию)
        yandex_items.append({
            "weight": 0.5 * qty,
            "dimensions": {"length": 30, "width": 20, "height": 2 * qty},
            "name": f"Product {prod.id} ({prod.type})"
        })

    order.total_amount = total

    # Логика Яндекс Доставки (всегда включена по умолчанию)
    if True: 
        try:
            from app.delivery.yandex import YandexDeliveryClient, YandexDeliveryError
            client = YandexDeliveryClient()
            # Для теста используем фиксированный source_station_id
            source_station_id = os.getenv("YANDEX_DELIVERY_SOURCE_STATION_ID", "fbed3aa1-2cc6-4370-ab4d-59c5cc9bb924")
            
            yandex_items = []
            total_weight_g = 0
            max_dx, max_dy, total_dz = 0, 0, 0
            
            for pid, qty in merged.items():
                prod = product_map[pid]
                # Предположим усредненные параметры, если их нет в БД
                # Вес в граммах (0.5 кг -> 500 г)
                weight_g = 500 * qty
                total_weight_g += weight_g
                
                # Размеры в см (dx=длина, dy=высота, dz=ширина)
                dx, dy, dz = 30, 20, 2 * qty
                max_dx = max(max_dx, dx)
                max_dy = max(max_dy, dy)
                total_dz += dz
                
                yandex_items.append({
                    "count": qty,
                    "name": f"{prod.type} {prod.color} {prod.size}",
                    "article": f"sku-{prod.id}",
                    "physical_dims": {
                        "dx": dx,
                        "dy": dy,
                        "dz": dz,
                        "weight_gross": int(weight_g)
                    },
                    "billing_details": {
                        "unit_price": int((prod.price or 0) * 100), # в копейках
                        "assessed_unit_price": int((prod.price or 0) * 100),
                        "nds": 0
                    }
                })
            
            yandex_places = [{
                "physical_dims": {
                    "dx": int(max_dx),
                    "dy": int(max_dy),
                    "dz": int(total_dz),
                    "weight_gross": int(total_weight_g)
                }
            }]
            
            # Нормализация телефона: убираем всё кроме цифр и +
            raw_phone = contact_info if (contact_info and contact_info.startswith("+")) else "+79991234567"
            clean_phone = "+" + "".join(c for c in raw_phone if c.isdigit())

            destination = {
                "address": delivery_address,
                "city": city or "Москва",
                "contact": {
                    "first_name": first_name or requester.username,
                    "last_name": last_name or "",
                    "phone": clean_phone
                }
            }
            
            offer_resp = await client.create_offer(
                source_station_id=source_station_id,
                destination=destination,
                items=yandex_items,
                places=yandex_places,
                last_mile_policy="time_interval" # Доставка до двери
            )
            
            offers = offer_resp.get("offers", [])
            if not offers:
                app_logger.warning(f"No Yandex delivery offers for order {order.id}")
                order.yandex_error = "Яндекс не предложил вариантов доставки для указанного адреса."
                order.status = "cancelled"  # Нет офферов — сразу в отказ
            else:
                # Берём первый подходящий оффер
                selected_offer = offers[0]
                offer_id = selected_offer["offer_id"]
                price_kop = int(selected_offer["price"]["total"])
                price_rub = price_kop // 100
                
                confirm_resp = await client.confirm_offer(offer_id)
                
                order.yandex_offer_id = offer_id
                order.yandex_request_id = confirm_resp.get("request_id")
                order.yandex_status = "created"
                order.delivery_cost = price_rub
                order.total_amount += price_rub
                order.yandex_error = None
                
        except YandexDeliveryError as e:
            app_logger.error(f"Yandex Delivery API error for order {order.id}: {e.code} - {str(e)}")
            order.yandex_error = f"Ошибка Яндекса ({e.code}): {str(e)}"
            order.status = "cancelled"  # Ошибка Яндекса — сразу в отказ
        except Exception as e:
            app_logger.error(f"Unexpected error creating Yandex delivery for order {order.id}: {str(e)}")
            order.yandex_error = f"Системная ошибка: {str(e)}"
            order.status = "cancelled"  # Неизвестная ошибка — тоже в отказ

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


async def sync_order_delivery_status(
    db: AsyncSession, requester: User, order_id: int
) -> Order:
    """Синхронизировать статус доставки с Яндексом."""
    order = await get_order_secure(db, requester, order_id)
    
    if not order.yandex_request_id:
        return order

    try:
        from app.delivery.yandex import YandexDeliveryClient
        client = YandexDeliveryClient()
        info = await client.get_request_info(order.yandex_request_id)
        
        # Обновляем статус
        new_status = info.get("status")
        if new_status:
            order.yandex_status = new_status
            
        await db.commit()
    except Exception as e:
        from app.logging_config import app_logger
        app_logger.error(f"Failed to sync Yandex status for order {order_id}: {str(e)}")
        
    return order
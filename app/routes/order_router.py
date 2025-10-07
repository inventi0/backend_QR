from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.models import User
from app.routes.dependecies import current_user, current_superuser
from app.schemas.order_schemas import (
    OrderCreateIn, OrderOut, OrderItemAddIn, OrderUpdateIn
)
from app.helpers.order_helpers import (
    create_order,
    get_order_secure,
    list_orders_for_user,
    list_all_orders,
    admin_add_item_to_order,
    admin_remove_item_from_order,
    admin_delete_order, admin_update_order_status,
)

orders_router = APIRouter(prefix="/orders", tags=["orders"])


@orders_router.post("", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
async def orders_create(
    payload: OrderCreateIn,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    items = [(it.product_id, it.quantity) for it in payload.items]
    order = await create_order(db, user, items)
    return order

@orders_router.get("/me", response_model=List[OrderOut])
async def orders_list_mine(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = await list_orders_for_user(db, user, limit=limit, offset=offset)
    return rows


@orders_router.get("/{order_id}", response_model=OrderOut)
async def orders_get_one(
    order_id: int,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    order = await get_order_secure(db, user, order_id)
    return order


@orders_router.get("/", response_model=List[OrderOut])
async def orders_list_all(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: User = Depends(current_superuser),
    db: AsyncSession = Depends(get_db),
):
    rows = await list_all_orders(db, limit=limit, offset=offset)
    return rows

@orders_router.post("/{order_id}/items", response_model=OrderOut)
async def orders_add_item(
    order_id: int,
    payload: OrderItemAddIn,
    user: User = Depends(current_superuser),
    db: AsyncSession = Depends(get_db),
):
    order = await admin_add_item_to_order(
        db, user, order_id, product_id=payload.product_id, quantity=payload.quantity
    )
    return order


@orders_router.delete("/{order_id}/items/{order_item_id}", response_model=OrderOut)
async def orders_remove_item(
    order_id: int,
    order_item_id: int,
    user: User = Depends(current_superuser),
    db: AsyncSession = Depends(get_db),
):
    order = await admin_remove_item_from_order(db, user, order_id, order_item_id)
    return order

@orders_router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def orders_delete(
    order_id: int,
    user: User = Depends(current_superuser),
    db: AsyncSession = Depends(get_db),
):
    await admin_delete_order(db, user, order_id)
    return

@orders_router.patch("/{order_id}/meta", response_model=OrderOut)
async def orders_update_meta(
    order_id: int,
    payload: OrderUpdateIn,
    user: User = Depends(current_superuser),
    db: AsyncSession = Depends(get_db),
):
    """
    Суперюзер: изменить информацию о заказе (сейчас — статус).
    """
    order = await admin_update_order_status(
        db, user, order_id, status=payload.status
    )
    return order
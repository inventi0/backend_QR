from typing import List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.models import User
from app.routes.dependecies import current_user, current_superuser
from app.schemas.order_schemas import (
    OrderCreateIn,
    OrderOut,
    OrderItemAddIn,
    OrderItemUpdateIn,
    OrderUpdateIn,
)
from app.helpers.order_helpers import (
    create_order,
    get_order_secure,
    list_orders_for_user,
    list_all_orders,
    admin_add_item_to_order,
    admin_remove_item_from_order,
    admin_delete_order,
    admin_update_order_status,
    admin_update_order_item_quantity,
)

from app.error.handler import handle_error
from app.logging_config import app_logger

orders_router = APIRouter(prefix="/orders", tags=["orders"])


@orders_router.post("", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
async def orders_create(
    payload: OrderCreateIn,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        items = [(it.product_id, it.quantity) for it in payload.items]
        order = await create_order(db, user, items)
        return order
    except Exception as e:
        raise handle_error(e, app_logger, "orders_create")


@orders_router.get("/me", response_model=List[OrderOut])
async def orders_list_mine(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        rows = await list_orders_for_user(db, user, limit=limit, offset=offset)
        return rows
    except Exception as e:
        raise handle_error(e, app_logger, "orders_list_mine")


@orders_router.get("/{order_id}", response_model=OrderOut)
async def orders_get_one(
    order_id: int,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        order = await get_order_secure(db, user, order_id)
        return order
    except Exception as e:
        raise handle_error(e, app_logger, "orders_get_one")


@orders_router.get("/", response_model=List[OrderOut])
async def orders_list_all(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    email: str | None = Query(None, description="фильтр по email пользователя"),
    statuses: str | None = Query(None, description="список статусов через запятую"),
    sort: str | None = Query(None, description="total_asc|total_desc|created_asc|created_desc"),
    user: User = Depends(current_superuser),
    db: AsyncSession = Depends(get_db),
):
    try:
        rows = await list_all_orders(
            db,
            limit=limit,
            offset=offset,
            email=email,
            statuses=statuses,
            sort=sort,
        )
        return rows
    except Exception as e:
        raise handle_error(e, app_logger, "orders_list_all")



@orders_router.post("/{order_id}/items", response_model=OrderOut)
async def orders_add_item(
    order_id: int,
    payload: OrderItemAddIn,
    user: User = Depends(current_superuser),
    db: AsyncSession = Depends(get_db),
):
    try:
        order = await admin_add_item_to_order(
            db, user, order_id, product_id=payload.product_id, quantity=payload.quantity
        )
        return order
    except Exception as e:
        raise handle_error(e, app_logger, "orders_add_item")


@orders_router.patch("/{order_id}/items/{order_item_id}", response_model=OrderOut)
async def orders_update_item_quantity(
    order_id: int,
    order_item_id: int,
    payload: OrderItemUpdateIn,  # { quantity: int >=1 }
    user: User = Depends(current_superuser),
    db: AsyncSession = Depends(get_db),
):
    try:
        order = await admin_update_order_item_quantity(
            db, user, order_id, order_item_id, quantity=payload.quantity
        )
        return order
    except Exception as e:
        raise handle_error(e, app_logger, "orders_update_item_quantity")


@orders_router.delete("/{order_id}/items/{order_item_id}", response_model=OrderOut)
async def orders_remove_item(
    order_id: int,
    order_item_id: int,
    user: User = Depends(current_superuser),
    db: AsyncSession = Depends(get_db),
):
    try:
        order = await admin_remove_item_from_order(db, user, order_id, order_item_id)
        return order
    except Exception as e:
        raise handle_error(e, app_logger, "orders_remove_item")


@orders_router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def orders_delete(
    order_id: int,
    user: User = Depends(current_superuser),
    db: AsyncSession = Depends(get_db),
):
    try:
        await admin_delete_order(db, user, order_id)
        return
    except Exception as e:
        raise handle_error(e, app_logger, "orders_delete")


@orders_router.patch("/{order_id}/meta", response_model=OrderOut)
async def orders_update_meta(
    order_id: int,
    payload: OrderUpdateIn,
    user: User = Depends(current_superuser),
    db: AsyncSession = Depends(get_db),
):
    """Суперюзер: изменить метаданные заказа (сейчас — статус)."""
    try:
        order = await admin_update_order_status(
            db, user, order_id, status=payload.status
        )
        return order
    except Exception as e:
        raise handle_error(e, app_logger, "orders_update_meta")

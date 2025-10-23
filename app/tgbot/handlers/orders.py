# app/tgbot/handlers/orders.py
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from app.tgbot.services.backend import fetch_orders
from app.tgbot.settings import BotSettings

router = Router()
_settings = BotSettings()

# Базовая навигация (если захочешь оставить без кнопок на каждую строку)
def orders_kb(page: int, has_prev: bool, has_next: bool) -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = []
    nav_row: list[InlineKeyboardButton] = []
    if has_prev:
        nav_row.append(InlineKeyboardButton(text="« Назад", callback_data=f"orders:page:{page-1}"))
    if has_next:
        nav_row.append(InlineKeyboardButton(text="Вперёд »", callback_data=f"orders:page:{page+1}"))
    if nav_row:
        buttons.append(nav_row)
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Текст одной строки заказа
def format_order_row(o: dict) -> str:
    # ожидаем что у заказа есть id, created_at, customer, amount, status
    cust = o.get("customer") or {}
    customer_name = cust.get("name") or cust.get("email") or "—"
    status = (o.get("status") or "NEW").upper()
    amount = o.get("amount", "—")
    oid = o.get("id", "—")
    return f"• <b>#{oid}</b> · {status} · {amount}₽ · {customer_name}"

# Версия строки без клиента (если нужно компактнее)
def order_row_compact(o: dict) -> str:
    status = (o.get("status") or "NEW").upper()
    amount = o.get("amount", "—")
    oid = o.get("id", "—")
    return f"• <b>#{oid}</b> · {status} · {amount}₽"

# Клавиатура: под каждой строкой — кнопка «Статус #ID», внизу — навигация
def orders_list_markup(items: list[dict], page: int, has_prev: bool, has_next: bool) -> InlineKeyboardMarkup:
    kb: list[list[InlineKeyboardButton]] = []

    for it in items:
        try:
            oid = int(it.get("id"))
        except (TypeError, ValueError):
            # если id нет/кривой — пропускаем кнопку для этой строки
            continue
        kb.append([
            InlineKeyboardButton(
                text=f"Статус #{oid}",
                callback_data=f"orders:open:{oid}:{page}"  # этот коллбэк обрабатывается в handlers/status.py
            )
        ])

    # Навигация по страницам
    nav_row: list[InlineKeyboardButton] = []
    if has_prev:
        nav_row.append(InlineKeyboardButton(text="« Назад", callback_data=f"orders:page:{page-1}"))
    if has_next:
        nav_row.append(InlineKeyboardButton(text="Вперёд »", callback_data=f"orders:page:{page+1}"))
    if nav_row:
        kb.append(nav_row)

    return InlineKeyboardMarkup(inline_keyboard=kb)

@router.message(Command("orders"))
async def list_orders_cmd(m: Message):
    page = 1
    data = await fetch_orders(page=page)
    items = data.get("items", []) or []
    total = int(data.get("total", len(items)) or 0)
    page_size = int(data.get("page_size", _settings.page_size) or _settings.page_size)
    has_prev = page > 1
    has_next = page * page_size < total

    if not items:
        await m.answer("Пока нет доступных заказов.")
        return

    # Выводим список заказов + под каждой строкой — кнопка «Статус»
    header = "<b>Доступные заказы</b>\n\n"
    body = "\n".join(format_order_row(o) for o in items)
    await m.answer(
        header + body,
        reply_markup=orders_list_markup(items, page, has_prev, has_next)
    )

@router.callback_query(F.data.startswith("orders:page:"))
async def list_orders_page(cq: CallbackQuery):
    try:
        page = int(cq.data.split(":")[-1])
    except Exception:
        page = 1

    data = await fetch_orders(page=page)
    items = data.get("items", []) or []
    total = int(data.get("total", len(items)) or 0)
    page_size = int(data.get("page_size", _settings.page_size) or _settings.page_size)
    has_prev = page > 1
    has_next = page * page_size < total

    if not items:
        await cq.message.edit_text("Пока нет доступных заказов.")
        await cq.answer()
        return

    header = "<b>Доступные заказы</b>\n\n"
    body = "\n".join(format_order_row(o) for o in items)
    await cq.message.edit_text(
        header + body,
        reply_markup=orders_list_markup(items, page, has_prev, has_next)
    )
    await cq.answer()

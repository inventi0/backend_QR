# app/tgbot/handlers/orders.py
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from app.tgbot.services.backend import fetch_orders
from app.tgbot.settings import BotSettings

router = Router()
_settings = BotSettings()

def orders_kb(page: int, has_prev: bool, has_next: bool) -> InlineKeyboardMarkup:
    buttons = []
    row = []
    if has_prev:
        row.append(InlineKeyboardButton(text="« Назад", callback_data=f"orders:page:{page-1}"))
    if has_next:
        row.append(InlineKeyboardButton(text="Вперёд »", callback_data=f"orders:page:{page+1}"))
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def format_order_row(o: dict) -> str:
    # ожидаем что у заказа есть id, created_at, customer, amount, status
    cust = o.get("customer") or {}
    customer_name = cust.get("name") or cust.get("email") or "—"
    return f"• <b>#{o.get('id')}</b> · {o.get('status','NEW')} · {o.get('amount','—')}₽ · {customer_name}"

@router.message(Command("orders"))
async def list_orders_cmd(m: Message):
    page = 1
    data = await fetch_orders(page=page)
    items = data.get("items", [])
    total = int(data.get("total", len(items)))
    page_size = int(data.get("page_size", _settings.page_size))
    has_prev = page > 1
    has_next = page * page_size < total

    if not items:
        await m.answer("Пока нет доступных заказов.")
        return

    text = "<b>Доступные заказы</b>\n\n" + "\n".join(map(format_order_row, items))
    await m.answer(text, reply_markup=orders_kb(page, has_prev, has_next))

@router.callback_query(F.data.startswith("orders:page:"))
async def list_orders_page(cq: CallbackQuery):
    page = int(cq.data.split(":")[-1])
    data = await fetch_orders(page=page)
    items = data.get("items", [])
    total = int(data.get("total", len(items)))
    page_size = int(data.get("page_size", _settings.page_size))
    has_prev = page > 1
    has_next = page * page_size < total

    if not items:
        await cq.message.edit_text("Пока нет доступных заказов.")
        await cq.answer()
        return

    text = "<b>Доступные заказы</b>\n\n" + "\n".join(map(format_order_row, items))
    await cq.message.edit_text(text, reply_markup=orders_kb(page, has_prev, has_next))
    await cq.answer()

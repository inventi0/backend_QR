from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram import F

from app.tgbot.services.backend import fetch_order_status, fetch_order_timeline

router = Router()

def status_kb(order_id: int, from_page: int | None = None) -> InlineKeyboardMarkup:
    rows = []
    rows.append([InlineKeyboardButton(text="🔄 Обновить", callback_data=f"status:refresh:{order_id}:{from_page or 1}")])
    if from_page:
        rows.append([InlineKeyboardButton(text="⬅️ Назад к списку", callback_data=f"orders:page:{from_page}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def fmt_timeline(items: list[dict]) -> str:
    if not items:
        return "—"
    # ожидаем {ts, status, comment?}
    lines = []
    for it in items[:10]:  # ограничим вывод
        ts = it.get("ts") or it.get("timestamp") or it.get("created_at") or "—"
        st = it.get("status", "—")
        cm = it.get("comment")
        if cm:
            lines.append(f"• {ts}: <b>{st}</b> — {cm}")
        else:
            lines.append(f"• {ts}: <b>{st}</b>")
    return "\n".join(lines)

def fmt_status_card(data: dict) -> str:
    cust = data.get("customer") or {}
    cn = cust.get("name") or cust.get("email") or "—"
    return (
        f"<b>Заказ #{data.get('id')}</b>\n"
        f"Статус: <b>{data.get('status','UNKNOWN')}</b>\n"
        f"Сумма: {data.get('amount','—')}₽\n"
        f"Клиент: {cn}\n"
        f"Создан: {data.get('created_at','—')}\n"
        f"Обновлён: {data.get('updated_at','—')}\n"
    )

@router.message(Command("status"))
async def status_cmd(m: Message):
    # парсим id после команды
    args = (m.text or "").strip().split()
    if len(args) < 2 or not args[1].isdigit():
        await m.answer("Использование: <code>/status &lt;id&gt;</code>")
        return
    order_id = int(args[1])

    data = await fetch_order_status(order_id)
    timeline = data.get("history")
    if timeline is None:
        timeline = await fetch_order_timeline(order_id)

    text = fmt_status_card(data) + "\n<b>История:</b>\n" + fmt_timeline(timeline)
    await m.answer(text, reply_markup=status_kb(order_id))

# Коллбэк из списка заказов — открыть карточку статуса
@router.callback_query(F.data.startswith("orders:open:"))
async def open_from_list(cq: CallbackQuery):
    # формат: orders:open:{order_id}:{from_page}
    _, _, order_id, from_page = (cq.data.split(":") + ["", ""])[:4]
    oid = int(order_id)
    page = int(from_page) if from_page and from_page.isdigit() else 1

    data = await fetch_order_status(oid)
    timeline = data.get("history")
    if timeline is None:
        timeline = await fetch_order_timeline(oid)

    text = fmt_status_card(data) + "\n<b>История:</b>\n" + fmt_timeline(timeline)
    await cq.message.edit_text(text, reply_markup=status_kb(oid, page))
    await cq.answer()

# Обновить карточку
@router.callback_query(F.data.startswith("status:refresh:"))
async def refresh_status(cq: CallbackQuery):
    # формат: status:refresh:{order_id}:{from_page}
    _, _, order_id, from_page = (cq.data.split(":") + ["", ""])[:4]
    oid = int(order_id)
    page = int(from_page) if from_page and from_page.isdigit() else None

    data = await fetch_order_status(oid)
    timeline = data.get("history")
    if timeline is None:
        timeline = await fetch_order_timeline(oid)

    text = fmt_status_card(data) + "\n<b>История:</b>\n" + fmt_timeline(timeline)
    await cq.message.edit_text(text, reply_markup=status_kb(oid, page))
    await cq.answer("Обновлено")

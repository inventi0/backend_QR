# app/tgbot/handlers/catalog.py
from __future__ import annotations
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from app.tgbot.services.backend import fetch_products, fetch_product_detail
from app.tgbot.settings import BotSettings
import base64

router = Router()
_settings = BotSettings()

# --- utils: безопасно пронести запрос q в callback
def _enc(s: str | None) -> str:
    if not s: return "_"
    return base64.urlsafe_b64encode(s.encode("utf-8")).decode("ascii")

def _dec(s: str | None) -> str | None:
    if not s or s == "_": return None
    try:
        return base64.urlsafe_b64decode(s.encode("ascii")).decode("utf-8")
    except Exception:
        return None

# --- форматирование
def fmt_product_row(p: dict) -> str:
    name = p.get("name") or p.get("title") or f"Товар #{p.get('id','')}"
    price = p.get("price", "—")
    stock = p.get("stock") if p.get("stock") is not None else p.get("quantity")
    stock_s = f"{stock} шт." if stock is not None else "наличие: —"
    pid = p.get("id", "—")
    return f"• <b>{name}</b> (#{pid}) — {price}₽ · {stock_s}"

def fmt_product_card(p: dict) -> str:
    name = p.get("name") or p.get("title") or f"Товар #{p.get('id','')}"
    price = p.get("price", "—")
    stock = p.get("stock") if p.get("stock") is not None else p.get("quantity")
    sku = p.get("sku") or p.get("code") or "—"
    desc = p.get("description") or "—"
    pid = p.get("id", "—")
    return (
        f"<b>{name}</b>\n"
        f"ID: <code>{pid}</code>\n"
        f"SKU: <code>{sku}</code>\n"
        f"Цена: {price}₽\n"
        f"Наличие: {stock if stock is not None else '—'}\n\n"
        f"{desc[:800]}"
    )

def catalog_kb(items: list[dict], page: int, has_prev: bool, has_next: bool, q_enc: str) -> InlineKeyboardMarkup:
    kb: list[list[InlineKeyboardButton]] = []
    # под каждой строкой — «Подробнее»
    for it in items:
        pid = it.get("id")
        if pid is None: continue
        kb.append([InlineKeyboardButton(text=f"Подробнее #{pid}", callback_data=f"catalog:open:{pid}:{page}:{q_enc}")])

    # внизу — навигация
    nav: list[InlineKeyboardButton] = []
    if has_prev:
        nav.append(InlineKeyboardButton(text="« Назад", callback_data=f"catalog:page:{page-1}:{q_enc}"))
    if has_next:
        nav.append(InlineKeyboardButton(text="Вперёд »", callback_data=f"catalog:page:{page+1}:{q_enc}"))
    if nav:
        kb.append(nav)
    return InlineKeyboardMarkup(inline_keyboard=kb)

def product_card_kb(pid: int, from_page: int | None, q_enc: str) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        [InlineKeyboardButton(text="🔄 Обновить", callback_data=f"catalog:refresh:{pid}:{from_page or 1}:{q_enc}")]
    ]
    if from_page:
        rows.append([InlineKeyboardButton(text="⬅️ Назад к списку", callback_data=f"catalog:page:{from_page}:{q_enc}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

# --- /catalog [поисковая фраза]
@router.message(Command("catalog"))
async def catalog_cmd(m: Message):
    args = (m.text or "").strip().split(maxsplit=1)
    q = args[1] if len(args) > 1 else None
    page = 1

    data = await fetch_products(page=page, q=q)
    items = data.get("items", []) or []
    total = int(data.get("total", len(items)) or 0)
    page_size = int(data.get("page_size", _settings.page_size) or _settings.page_size)
    has_prev = page > 1
    has_next = page * page_size < total
    q_enc = _enc(q)

    if not items:
        await m.answer("Товары не найдены." if q else "Каталог пуст.")
        return

    header = "<b>Каталог</b>"
    if q:
        header += f"\nПоиск: <i>{q}</i>"
    body = "\n\n".join(fmt_product_row(p) for p in items)
    await m.answer(f"{header}\n\n{body}", reply_markup=catalog_kb(items, page, has_prev, has_next, q_enc))

# --- пагинация каталога
@router.callback_query(F.data.startswith("catalog:page:"))
async def catalog_page(cq: CallbackQuery):
    _, _, page_str, q_enc = (cq.data.split(":") + ["", ""])[:4]
    try:
        page = int(page_str)
    except Exception:
        page = 1
    q = _dec(q_enc)

    data = await fetch_products(page=page, q=q)
    items = data.get("items", []) or []
    total = int(data.get("total", len(items)) or 0)
    page_size = int(data.get("page_size", _settings.page_size) or _settings.page_size)
    has_prev = page > 1
    has_next = page * page_size < total

    if not items:
        await cq.message.edit_text("Товары не найдены.")
        await cq.answer()
        return

    header = "<b>Каталог</b>"
    if q:
        header += f"\nПоиск: <i>{q}</i>"
    body = "\n\n".join(fmt_product_row(p) for p in items)

    await cq.message.edit_text(f"{header}\n\n{body}", reply_markup=catalog_kb(items, page, has_prev, has_next, q_enc))
    await cq.answer()

# --- карточка товара
@router.callback_query(F.data.startswith("catalog:open:"))
async def catalog_open(cq: CallbackQuery):
    # формат: catalog:open:{product_id}:{from_page}:{q_enc}
    _, _, pid_str, from_page_str, q_enc = (cq.data.split(":") + ["", "", ""])[:5]
    pid = int(pid_str)
    from_page = int(from_page_str) if from_page_str.isdigit() else None
    q = _dec(q_enc)

    p = await fetch_product_detail(pid)
    text = fmt_product_card(p)
    kb = product_card_kb(pid, from_page, q_enc)

    # если есть картинка — попробуем заменить медиа
    image_url = p.get("image_url") or p.get("image")
    if image_url:
        try:
            await cq.message.edit_media(
                media=InputMediaPhoto(media=image_url, caption=text, parse_mode="HTML"),
                reply_markup=kb
            )
            await cq.answer()
            return
        except Exception:
            pass  # не страшно — отправим текстом

    await cq.message.edit_text(text, reply_markup=kb)
    await cq.answer()

# --- обновить карточку
@router.callback_query(F.data.startswith("catalog:refresh:"))
async def catalog_refresh(cq: CallbackQuery):
    # формат: catalog:refresh:{product_id}:{from_page}:{q_enc}
    _, _, pid_str, from_page_str, q_enc = (cq.data.split(":") + ["", "", ""])[:5]
    pid = int(pid_str)
    from_page = int(from_page_str) if from_page_str.isdigit() else None

    p = await fetch_product_detail(pid)
    text = fmt_product_card(p)
    kb = product_card_kb(pid, from_page, q_enc)

    image_url = p.get("image_url") or p.get("image")
    if image_url:
        try:
            await cq.message.edit_media(
                media=InputMediaPhoto(media=image_url, caption=text, parse_mode="HTML"),
                reply_markup=kb
            )
            await cq.answer("Обновлено")
            return
        except Exception:
            pass

    await cq.message.edit_text(text, reply_markup=kb)
    await cq.answer("Обновлено")

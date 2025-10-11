from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from sqlalchemy.ext.asyncio import AsyncSession
import json, hmac, hashlib, base64, urllib.parse, uuid

from app.tgbot.settings import BotSettings
from app.tgbot.services.qr import make_simple_payment_text, gen_qr_png_bytes
from app.tgbot.services.payments import create_yookassa_payment_link, YooKassaNotConfigured
from app.tgbot.services.invoices import create_invoice, set_provider_and_payment, set_status_paid, get_invoice

settings = BotSettings()
router = Router()

def b64url_encode(b: bytes) -> str: return base64.urlsafe_b64encode(b).decode().rstrip("=")
def b64url_decode(s: str) -> bytes: return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))
def sign_payload(payload_json: str) -> str:
    if not settings.start_secret: return ""
    mac = hmac.new(settings.start_secret.encode(), payload_json.encode(), hashlib.sha256).digest()
    return b64url_encode(mac)
def verify_payload(payload_b64: str, signature_b64: str) -> dict | None:
    try:
        payload_json = b64url_decode(payload_b64).decode()
        if settings.start_secret:
            expected = sign_payload(payload_json)
            if not hmac.compare_digest(expected, signature_b64): return None
        return json.loads(payload_json)
    except Exception:
        return None
def is_admin(user_id: int) -> bool: return user_id in settings.admin_ids

async def _send_invoice_bundle(message: Message, *, invoice_id: int, order_id: str,
                               amount: str, currency: str, purpose: str,
                               name: str, iban: str):
    # ссылка оплаты если была — отправлена раньше
    payload_text = make_simple_payment_text(name, iban, amount, currency, purpose, order_id)
    png = gen_qr_png_bytes(payload_text)
    await message.bot.send_photo(
        message.chat.id,
        photo=BufferedInputFile(png, filename=f"invoice_{invoice_id}.png"),
        caption=(
          f"Счёт #{invoice_id}\nЗаказ: {order_id}\nСумма: {amount} {currency}\n"
          f"Реквизит: {iban}\nНазначение: {purpose}\nСканируйте QR для оплаты."
        ),
    )

async def create_and_send_invoice_for_user(message: Message, db: AsyncSession, *,
    customer_chat_id: int, order_id: str, amount: str, currency: str, purpose: str,
    name: str | None, iban_or_acc: str | None) -> int:

    inv = await create_invoice(
        db, order_id=order_id, amount=amount, currency=currency,
        name=name or settings.merchant_name, iban=iban_or_acc or settings.merchant_acc,
        purpose=purpose, customer_chat_id=customer_chat_id
    )

    # YooKassa (если есть)
    if settings.yk_shop_id and settings.yk_secret_key and currency.upper() == "RUB":
        try:
            pid, url = await create_yookassa_payment_link(
                shop_id=settings.yk_shop_id, secret_key=settings.yk_secret_key,
                order_id=str(inv.id), amount=amount,
                description=purpose or f"Оплата заказа {order_id}",
                return_url=settings.pay_return_url
            )
            await set_provider_and_payment(db, inv.id, "yookassa", pid)
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Оплатить", url=url)]])
            await message.bot.send_message(customer_chat_id,
                f"Счёт #{inv.id}\nЗаказ: {order_id}\nСумма: {amount} {currency}\nНазначение: {purpose or '-'}",
                reply_markup=kb
            )
        except Exception:
            pass

    await _send_invoice_bundle(
        message, invoice_id=inv.id, order_id=order_id, amount=amount, currency=currency,
        purpose=purpose, name=name or settings.merchant_name, iban=iban_or_acc or settings.merchant_acc
    )
    return inv.id

@router.message(Command("start"))
async def cmd_start(message: Message, db: AsyncSession):
    parts = (message.text or "").split(" ", 1)
    if len(parts) == 1:
        await message.answer("Привет! /demo_me, /make_link, /create_invoice, /confirm_payment")
        return
    start_param = parts[1].strip()
    if "_" in start_param:
        payload_b64, sig_b64 = start_param.split("_", 1)
        data = verify_payload(payload_b64, sig_b64)
        if not data:
            await message.answer("Старт-параметр не прошёл проверку подписи.")
            return
    else:
        if not (settings.debug_mode and is_admin(message.from_user.id)):
            await message.answer("Некорректный старт-параметр.")
            return
        data = json.loads(b64url_decode(start_param).decode())

    order_id = str(data.get("order_id") or "")
    amount = str(data.get("amount") or "")
    currency = (data.get("currency") or settings.default_currency).upper()
    purpose = str(data.get("purpose") or f"Оплата заказа {order_id}")
    if not (order_id and amount and currency):
        await message.answer("Не хватает данных заказа.")
        return

    inv_id = await create_and_send_invoice_for_user(
        message, db, customer_chat_id=message.from_user.id,
        order_id=order_id, amount=amount, currency=currency, purpose=purpose,
        name=settings.merchant_name, iban_or_acc=settings.merchant_acc
    )
    await message.answer(f"✅ Счёт #{inv_id} создан.")

@router.message(Command("demo_me"))
async def cmd_demo_me(message: Message, db: AsyncSession):
    if not is_admin(message.from_user.id):
        await message.answer("Только админ.")
        return
    args = message.text.split(" ", 1)
    if len(args) < 2:
        order_id = f"DEMO-{uuid.uuid4().hex[:6].upper()}"; amount="150.00"; currency="RUB"; purpose=f"Демо оплата {order_id}"
    else:
        try:
            order_id, amount, currency, purpose = args[1].split("|", 3)
            order_id, amount, currency, purpose = order_id.strip(), amount.strip(), currency.strip().upper(), purpose.strip()
        except Exception:
            await message.answer("Формат:\n/demo_me order|amount|currency|purpose"); return
    inv_id = await create_and_send_invoice_for_user(
        message, db, customer_chat_id=message.from_user.id,
        order_id=order_id, amount=amount, currency=currency, purpose=purpose,
        name=settings.merchant_name, iban_or_acc=settings.merchant_acc
    )
    await message.answer(f"✅ Демо-счёт #{inv_id} отправлен.")

@router.message(Command("make_link"))
async def cmd_make_link(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("Только админ."); return
    if not settings.bot_username:
        await message.answer("BOT_USERNAME не задан."); return
    args = message.text.split(" ", 1)
    if len(args) < 2:
        await message.answer("Формат:\n/make_link order|amount|currency|purpose"); return
    try:
        order_id, amount, currency, purpose = args[1].split("|", 3)
        data = {"order_id": order_id.strip(), "amount": amount.strip(),
                "currency": currency.strip().upper(), "purpose": purpose.strip()}
    except Exception:
        await message.answer("Некорректный формат."); return
    payload_json = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    payload_b64 = b64url_encode(payload_json.encode())
    sig_b64 = sign_payload(payload_json) if settings.start_secret else ""
    start_param = f"{payload_b64}_{sig_b64}" if sig_b64 else payload_b64
    deeplink = f"https://t.me/{settings.bot_username}?start={urllib.parse.quote(start_param)}"
    await message.answer(f"Диплинк:\n{deeplink}")

@router.message(Command("create_invoice"))
async def create_invoice_cmd(message: Message, db: AsyncSession):
    if not is_admin(message.from_user.id):
        await message.answer("Только админ."); return
    args = message.text.split(" ", 1)
    if len(args) < 2:
        await message.answer("Формат:\n/create_invoice order|amount|currency|name|iban|purpose|customer_chat_id"); return
    try:
        order_id, amount, currency, name, iban, purpose, chat_id = args[1].split("|", 6)
        order_id, amount, currency = order_id.strip(), amount.strip(), currency.strip().upper()
        name, iban, purpose = name.strip(), iban.strip().replace(" ", ""), purpose.strip()
        chat_id = int(chat_id.strip())
    except Exception:
        await message.answer("Некорректные параметры."); return
    inv_id = await create_and_send_invoice_for_user(
        message, db, customer_chat_id=chat_id,
        order_id=order_id, amount=amount, currency=currency, purpose=purpose,
        name=name, iban_or_acc=iban
    )
    await message.answer(f"✅ Инвойс #{inv_id} отправлен пользователю {chat_id}.")

@router.message(Command("confirm_payment"))
async def confirm_payment(message: Message, db: AsyncSession):
    if not is_admin(message.from_user.id):
        await message.answer("Только админ."); return
    args = message.text.split(" ", 1)
    if len(args) < 2 or not args[1].strip().isdigit():
        await message.answer("Использование: /confirm_payment <invoice_id>"); return
    inv_id = int(args[1].strip())
    inv = await get_invoice(db, inv_id)
    if not inv:
        await message.answer("Инвойс не найден."); return
    if inv.status == "paid":
        await message.answer("Этот инвойс уже оплачен."); return
    await set_status_paid(db, inv_id)
    await message.answer(f"✅ Инвойс #{inv_id} помечен как оплачен.")
    try:
        await message.bot.send_message(inv.customer_chat_id, f"Оплата заказа {inv.order_id} подтверждена. Спасибо!")
    except Exception:
        pass

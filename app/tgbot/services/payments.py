import base64, json, aiohttp

class YooKassaNotConfigured(Exception): ...
async def create_yookassa_payment_link(*, shop_id: str | None, secret_key: str | None,
                                       order_id: str, amount: str, description: str,
                                       return_url: str) -> tuple[str, str]:
    if not (shop_id and secret_key):
        raise YooKassaNotConfigured("YK_SHOP_ID/YK_SECRET_KEY не заданы")
    basic = base64.b64encode(f"{shop_id}:{secret_key}".encode()).decode()
    headers = {"Authorization": f"Basic {basic}", "Content-Type": "application/json", "Idempotence-Key": f"order-{order_id}"}
    payload = {
        "amount": {"value": f"{float(amount):.2f}", "currency": "RUB"},
        "capture": True,
        "description": (description or f"Оплата заказа {order_id}")[:128],
        "confirmation": {"type": "redirect", "return_url": return_url},
        "metadata": {"order_id": str(order_id)},
    }
    async with aiohttp.ClientSession() as s:
        async with s.post("https://api.yookassa.ru/v3/payments", headers=headers, data=json.dumps(payload), timeout=20) as r:
            if r.status >= 300:
                raise RuntimeError(f"YooKassa error {r.status}: {await r.text()}")
            data = await r.json()
    pid = data.get("id")
    url = (data.get("confirmation") or {}).get("confirmation_url")
    if not (pid and url):
        raise RuntimeError(f"Некорректный ответ YooKassa: {data}")
    return pid, url

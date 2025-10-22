# app/tgbot/services/backend.py
from typing import Any, Dict, Optional
import httpx
from app.tgbot.settings import BotSettings

_settings = BotSettings()

def _auth_headers() -> Dict[str, str]:
    # Сервисный заголовок, если используешь отдельный сервис-токен на бекенде
    headers = {"Accept": "application/json"}
    if _settings.backend_service_token:
        headers["Authorization"] = f"Bearer {_settings.backend_service_token}"
    return headers

async def api_get(path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    url = _settings.backend_base_url.rstrip("/") + path
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(url, params=params, headers=_auth_headers())
    r.raise_for_status()
    return r.json()

# Специализированные вызовы

async def fetch_orders(page: int = 1, page_size: int | None = None, status: str | None = None) -> Dict[str, Any]:
    ps = page_size or _settings.page_size
    params = {"page": page, "page_size": ps}
    if status: params["status"] = status
    return await api_get("/orders", params=params)

async def fetch_order_status(order_id: int) -> Dict[str, Any]:
    return await api_get(f"/orders/{order_id}")

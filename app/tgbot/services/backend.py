# app/tgbot/services/backend.py
from typing import Any, Dict, Optional
import httpx
from httpx import HTTPStatusError
from app.tgbot.settings import BotSettings


_settings = BotSettings()
_access_token: str | None = None  # кеш токена после логина

def _auth_headers() -> Dict[str, str]:
    headers = {"Accept": "application/json"}
    # приоритет: явный сервис-токен из .env
    token = _settings.backend_service_token or _access_token
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers

async def _login_get_token() -> str:
    """
    Пытаемся залогиниться двумя способами:
      1) JSON: {"email": "...", "password": "..."}
      2) Form: username/password (OAuth2 style)
    Ищем токен по ключам: access_token / token / data.access_token
    """
    if not (_settings.login_email and _settings.login_password):
        raise RuntimeError("No BACKEND_LOGIN_EMAIL/BACKEND_LOGIN_PASSWORD set for bot login")

    url = _settings.backend_base_url.rstrip("/") + _settings.auth_login_path
    async with httpx.AsyncClient(timeout=15) as client:
        # Попытка №1: JSON
        try:
            r = await client.post(url, json={"email": _settings.login_email, "password": _settings.login_password})
            if r.status_code < 400:
                data = r.json()
                token = (
                        data.get("access_token")
                        or data.get("token")
                        or (data.get("data", {}) or {}).get("access_token")
                )
                if token:
                    return token
        except Exception:
            pass

        # Попытка №2: form (username/password)
        r = await client.post(
            url,
            data={"username": _settings.login_email, "password": _settings.login_password},
            headers={"Accept": "application/json"},
        )
        r.raise_for_status()
        data = r.json()
        token = (
                data.get("access_token")
                or data.get("token")
                or (data.get("data", {}) or {}).get("access_token")
        )
        if not token:
            raise RuntimeError("Login succeeded but no access_token in response")
        return token

async def _ensure_token():
    global _access_token
    if _settings.backend_service_token:
        return  # уже задан постоянный токен
    if not _access_token:
        _access_token = await _login_get_token()

async def _request_with_reauth(method: str, path: str, *, params=None, json=None) -> Dict[str, Any]:
    await _ensure_token()
    url = _settings.backend_base_url.rstrip("/") + path
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.request(method, url, params=params, json=json, headers=_auth_headers())
    if r.status_code == 401 and not _settings.backend_service_token:
        # пробуем перелогиниться 1 раз
        global _access_token
        _access_token = await _login_get_token()
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.request(method, url, params=params, json=json, headers=_auth_headers())
    r.raise_for_status()
    return r.json()

async def api_get(path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return await _request_with_reauth("GET", path, params=params)

async def api_post(path: str, json: Optional[Dict[str, Any]] = None, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return await _request_with_reauth("POST", path, params=params, json=json)

# Специализированные вызовы

async def fetch_orders(page: int = 1, page_size: int | None = None, status: str | None = None) -> Dict[str, Any]:
    ps = page_size or _settings.page_size
    path = _settings.orders_path
    method = _settings.orders_method.upper()
    if method == "POST":
        body: Dict[str, Any] = {"page": page, "page_size": ps}
        if status: body["status"] = status
        return await api_post(path, json=body)
    params: Dict[str, Any] = {"page": page, "page_size": ps}
    if status: params["status"] = status
    return await api_get(path, params=params)

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



def _auth_headers() -> Dict[str, str]:
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

async def api_post(path: str, json: Optional[Dict[str, Any]] = None, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    url = _settings.backend_base_url.rstrip("/") + path
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(url, json=json, params=params, headers=_auth_headers())
    r.raise_for_status()
    return r.json()

async def fetch_orders(page: int = 1, page_size: int | None = None, status: str | None = None) -> Dict[str, Any]:
    ps = page_size or _settings.page_size
    path = _settings.orders_path
    method = _settings.orders_method.upper()

    if method == "POST":
        body: Dict[str, Any] = {"page": page, "page_size": ps}
        if status: body["status"] = status
        return await api_post(path, json=body)

    # по умолчанию GET
    params: Dict[str, Any] = {"page": page, "page_size": ps}
    if status: params["status"] = status
    try:
        return await api_get(path, params=params)
    except HTTPStatusError as e:
        if e.response.status_code == 405:
            # фоллбэк на POST, если GET запрещён
            body: Dict[str, Any] = {"page": page, "page_size": ps}
            if status: body["status"] = status
            return await api_post(path, json=body)
        raise

async def fetch_order_status(order_id: int) -> dict:
    # Ожидаемый ответ: { id, status, amount, customer:{...}, created_at, updated_at, history?:[...] }
    return await api_get(f"/orders/{order_id}")

async def fetch_order_timeline(order_id: int) -> list[dict]:
    """
    Если таймлайн не приходит в fetch_order_status, можно держать отдельный эндпоинт.
    Возвращает список событий [{ts, status, comment?}, ...]
    """
    try:
        data = await api_get(f"/orders/{order_id}/history")
        if isinstance(data, dict) and "items" in data:
            return data["items"]
        if isinstance(data, list):
            return data
    except Exception:
        pass
    return []

async def fetch_products(
        page: int = 1,
        page_size: int | None = None,
        q: str | None = None,
        availability: bool | None = None,
        min_price: int | None = None,
        max_price: int | None = None,
) -> Dict[str, Any]:
    ps = page_size or _settings.page_size
    params: Dict[str, Any] = {"page": page, "page_size": ps}
    if q: params["q"] = q
    if availability is not None: params["availability"] = str(availability).lower()  # true/false
    if min_price is not None: params["min_price"] = min_price
    if max_price is not None: params["max_price"] = max_price
    return await api_get("/products", params=params)

async def fetch_product_detail(product_id: int) -> Dict[str, Any]:
    return await api_get(f"/products/{product_id}")

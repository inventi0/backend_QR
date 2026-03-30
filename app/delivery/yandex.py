import os
import httpx
from typing import Optional, List, Any, Dict
from app.logging_config import app_logger

class YandexDeliveryError(Exception):
    def __init__(self, message: str, code: Optional[str] = None, response_text: Optional[str] = None):
        super().__init__(message)
        self.code = code
        self.response_text = response_text

class YandexDeliveryClient:
    def __init__(
        self, 
        token: Optional[str] = None, 
        cabinet_id: Optional[str] = None, 
        base_url: Optional[str] = None
    ):
        self.token = token or os.getenv("YANDEX_DELIVERY_TOKEN")
        self.cabinet_id = cabinet_id or os.getenv("YANDEX_DELIVERY_CABINET_ID")
        self.base_url = (base_url or os.getenv("YANDEX_DELIVERY_BASE_URL", "https://b2b-authproxy.taxi.yandex.net")).rstrip('/')
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    async def _handle_response(self, response: httpx.Response) -> dict:
        try:
            data = response.json()
        except Exception:
            data = {}

        if response.status_code >= 400:
            raw_text = response.text
            # Если ответ — это HTML (SmartCaptcha / WAF блокировка)
            if raw_text.strip().startswith(("<!DOCTYPE", "<html")):
                friendly = (
                    f"[Яндекс временно заблокировал IP сервера (SmartCaptcha 403). "
                    "Попробуйте через 30-60 минут.]"
                )
                app_logger.error(f"Yandex SmartCaptcha block {response.status_code} on {response.url}")
                raise YandexDeliveryError(message=friendly, code="smartcaptcha_block", response_text=raw_text)

            code = data.get("code") or data.get("error", {}).get("code") or str(response.status_code)
            message = data.get("message") or data.get("error", {}).get("message") or raw_text
            app_logger.error(
                f"Yandex API Error {response.status_code} | code={code} | "
                f"message={message} | raw={raw_text[:2000]}"
            )
            raise YandexDeliveryError(
                message=f"{message}",
                code=code,
                response_text=raw_text
            )
        
        return data

    async def _post(self, endpoint: str, data: dict) -> dict:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url.rstrip('/')}{endpoint}",
                    json=data,
                    headers=self.headers,
                    timeout=30.0
                )
                return await self._handle_response(response)
            except httpx.RequestError as exc:
                app_logger.error(f"Network error while requesting Yandex: {str(exc)}")
                raise

    async def _get(self, endpoint: str, params: Optional[dict] = None) -> dict:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url.rstrip('/')}{endpoint}",
                    params=params,
                    headers=self.headers,
                    timeout=30.0
                )
                return await self._handle_response(response)
            except httpx.RequestError as exc:
                app_logger.error(f"Network error while requesting Yandex: {str(exc)}")
                raise

    async def calculate_price(self, source: dict, destination: dict, items: List[dict]) -> dict:
        """
        Расчет стоимости доставки.
        """
        data = {
            "source": source,
            "destination": destination,
            "items": items
        }
        return await self._post("/api/b2b/platform/pricing-calculator", data)

    async def create_offer(
        self, 
        source_station_id: str, 
        destination: dict, 
        items: List[dict], 
        places: Optional[List[dict]] = None,
        last_mile_policy: str = "time_interval",
        interval_from: Optional[str] = None,
        interval_to: Optional[str] = None,
    ) -> dict:
        """
        Создание заявки (получение офферов) в B2B платформе.
        Документация: platform_station.platform_id + interval_utc обязательны.
        """
        from datetime import datetime, timezone, timedelta
        # Интервал забора: завтра, с 10:00 до 18:00 UTC
        now_utc = datetime.now(timezone.utc)
        tomorrow = now_utc + timedelta(days=1)
        default_from = tomorrow.replace(hour=7, minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%S.000000Z")
        default_to   = tomorrow.replace(hour=15, minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%S.000000Z")

        # Интервал доставки: послезавтра, с 10:00 до 22:00 UTC
        delivery_day = now_utc + timedelta(days=2)
        delivery_from = delivery_day.replace(hour=7, minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%S.000000Z")
        delivery_to   = delivery_day.replace(hour=19, minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%S.000000Z")

        full_address = (
            f"{destination.get('city', 'Москва')}, {destination.get('address')}"
            if destination.get('address')
            else destination.get('city', 'Москва')
        )

        data = {
            "source": {
                "platform_station": {
                    "platform_id": source_station_id
                },
                "interval_utc": {
                    "from": interval_from or default_from,
                    "to":   interval_to   or default_to
                }
            },
            "destination": {
                "self_delivery_address": {
                    "fullAddress": full_address,
                    "contact": destination.get("contact", {})
                }
            },
            "items": items,
            "places": places or [],
            "last_mile_policy": last_mile_policy,
            "billing_info": {
                "payment_method": "already_paid"
            },
            "info": {
                "operator_comment": "Test order created via API"
            }
        }
        app_logger.info(f"Yandex create_offer payload: {data}")
        return await self._post("/api/b2b/platform/offers/create", data)

    async def confirm_offer(self, offer_id: str) -> dict:
        """
        Подтверждение оффера.
        """
        data = {"offer_id": offer_id}
        return await self._post("/api/b2b/platform/offers/confirm", data)

    async def get_request_info(self, request_id: str) -> dict:
        """
        Получение информации о заявке.
        """
        params = {"request_id": request_id}
        return await self._get("/api/b2b/platform/request/info", params)

    async def get_request_history(self, request_id: str) -> dict:
        """
        История статусов заявки.
        """
        params = {"request_id": request_id}
        return await self._get("/api/b2b/platform/request/history", params)

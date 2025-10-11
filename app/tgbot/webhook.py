from fastapi import APIRouter, Request, Response, Header
from aiogram.types import Update

def make_webhook_router(dp, bot, secret_token: str | None):
    router = APIRouter(prefix="/tg", tags=["telegram"])

    @router.post("/webhook")
    async def telegram_webhook(
        request: Request,
        x_telegram_bot_api_secret_token: str | None = Header(default=None)
    ):
        if secret_token and x_telegram_bot_api_secret_token != secret_token:
            return Response(status_code=403)

        update = Update.model_validate(await request.json())
        await dp.feed_update(bot, update)
        return Response(status_code=200)

    return router

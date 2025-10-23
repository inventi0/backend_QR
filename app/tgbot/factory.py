# app/tgbot/factory.py
from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from .handlers import status  # NEW
from .handlers import catalog
from .settings import BotSettings
from .middlewares import DBSessionMiddleware
from .handlers import billing
from .handlers import orders  # <— добавили

def build_bot_and_dispatcher(settings: BotSettings):
    bot = Bot(settings.token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.message.middleware(DBSessionMiddleware())
    dp.callback_query.middleware(DBSessionMiddleware())

    router = Router()
    router.include_router(billing.router)
    router.include_router(orders.router)   # <— подключили
    router.include_router(status.router)
    router.include_router(catalog.router)

    dp.include_router(router)
    return bot, dp

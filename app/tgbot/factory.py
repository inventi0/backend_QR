from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from .settings import BotSettings
from .middlewares import DBSessionMiddleware
from .handlers import billing

def build_bot_and_dispatcher(settings: BotSettings):
    bot = Bot(settings.token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.message.middleware(DBSessionMiddleware())
    dp.callback_query.middleware(DBSessionMiddleware())

    router = Router()
    router.include_router(billing.router)

    dp.include_router(router)
    return bot, dp

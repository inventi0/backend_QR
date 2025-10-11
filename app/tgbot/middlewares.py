from aiogram import BaseMiddleware
from typing import Callable, Awaitable, Any, Dict
# поправь путь на ваш
from ..database import async_session

class DBSessionMiddleware(BaseMiddleware):
    async def __call__(self, handler: Callable[[Any, Dict[str, Any]], Awaitable[Any]],
                       event: Any, data: Dict[str, Any]) -> Any:
        async with async_session() as session:
            data["db"] = session
            return await handler(event, data)

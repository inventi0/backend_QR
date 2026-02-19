import re
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.models import BadWord

async def check_bad_words(db: AsyncSession, text: str) -> bool:
    """
    Проверяет текст на наличие плохих слов из базы данных.
    Возвращает True, если найдено запрещенное слово.
    """
    if not text:
        return False
        
    result = await db.execute(select(BadWord.word))
    bad_words = result.scalars().all()
    
    if not bad_words:
        return False
        
    text_lower = text.lower()
    for word in bad_words:
        # Ищем слово как самостоятельное или часть другого слова
        pattern = r"\b" + re.escape(word) + r"s?\b"
        if re.search(pattern, text_lower) or word in text_lower:
            return True
            
    return False

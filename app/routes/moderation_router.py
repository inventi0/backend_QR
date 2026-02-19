from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_db
from app.models.models import User, BadWord
from app.routes.dependecies import current_superuser
from pydantic import BaseModel

from app.error.handler import handle_error
from app.logging_config import app_logger

moderation_router = APIRouter(prefix="/moderation", tags=["moderation"])

class BadWordCreate(BaseModel):
    word: str

class BadWordRead(BaseModel):
    id: int
    word: str

    class Config:
        orm_mode = True


@moderation_router.get("/bad-words", response_model=list[BadWordRead])
async def get_bad_words(
    user: User = Depends(current_superuser),
    db: AsyncSession = Depends(get_db),
):
    """Получить список запрещённых слов (для админа)."""
    try:
        result = await db.execute(select(BadWord))
        return result.scalars().all()
    except Exception as e:
        raise handle_error(e, app_logger, "get_bad_words")


@moderation_router.post("/bad-words", response_model=BadWordRead)
async def create_bad_word(
    data: BadWordCreate,
    user: User = Depends(current_superuser),
    db: AsyncSession = Depends(get_db),
):
    """Добавить новое запрещённое слово (для админа)."""
    try:
        # Проверим, нет ли уже такого слова
        word_lower = data.word.strip().lower()
        if not word_lower:
            raise HTTPException(status_code=400, detail="Word cannot be empty")
            
        existing = await db.execute(select(BadWord).where(BadWord.word == word_lower))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Word already exists in bad words list")
            
        bad_word = BadWord(word=word_lower)
        db.add(bad_word)
        await db.commit()
        await db.refresh(bad_word)
        return bad_word
    except Exception as e:
        raise handle_error(e, app_logger, "create_bad_word")


@moderation_router.delete("/bad-words/{word_id}")
async def delete_bad_word(
    word_id: int,
    user: User = Depends(current_superuser),
    db: AsyncSession = Depends(get_db),
):
    """Удалить запрещённое слово (для админа)."""
    try:
        bad_word = await db.get(BadWord, word_id)
        if not bad_word:
            raise HTTPException(status_code=404, detail="Bad word not found")
            
        await db.delete(bad_word)
        await db.commit()
        return {"status": "success", "message": "Bad word deleted"}
    except Exception as e:
        raise handle_error(e, app_logger, "delete_bad_word")

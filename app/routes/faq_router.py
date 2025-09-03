from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.faq_schemas import FAQCreate, FAQRead, FAQAnswer
from app.helpers.faq_helpers import create_faq_helper, get_all_faqs_helper, answer_faq_helper
from app.models.models import User
from .dependecies import current_superuser

faq_router = APIRouter(prefix="/faq", tags=["faq"])


@faq_router.post("/create", response_model=FAQRead)
async def create_faq(
    data: FAQCreate,
    db: AsyncSession = Depends(get_db),
):
    """Задать вопрос (без авторизации)."""
    faq = await create_faq_helper(db=db, name=data.name, question=data.question)
    return faq


@faq_router.get("/all", response_model=list[FAQRead])
async def get_all_faqs(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_superuser),
):
    """Получить все вопросы (только для суперюзера)."""
    return await get_all_faqs_helper(db)


@faq_router.put("/{faq_id}/answer", response_model=FAQRead)
async def answer_faq(
    faq_id: int,
    data: FAQAnswer,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_superuser),
):
    """Ответить на вопрос (только для суперюзера)."""
    faq = await answer_faq_helper(db, faq_id=faq_id, answer=data.answer)
    if not faq:
        raise HTTPException(status_code=404, detail="FAQ not found")
    return faq

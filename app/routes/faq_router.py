from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.faq_schemas import FAQCreate, FAQRead, FAQAnswer
from app.helpers.faq_helpers import create_faq_helper, get_all_faqs_helper, answer_faq_helper
from app.models.models import User
from .dependecies import current_superuser

from app.error.handler import handle_error
from app.logging_config import app_logger

faq_router = APIRouter(prefix="/faq", tags=["faq"])


@faq_router.post("/create", response_model=FAQRead)
async def create_faq(
    data: FAQCreate,
    db: AsyncSession = Depends(get_db),
):
    """Задать вопрос (без авторизации)."""
    try:
        faq = await create_faq_helper(db=db, name=data.name, email=data.email, question=data.question)
        return faq
    except Exception as e:
        raise handle_error(e, app_logger, "create_faq")



@faq_router.get("/all", response_model=list[FAQRead])
async def get_all_faqs(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_superuser),
):
    """Получить все вопросы (только для суперюзера)."""
    try:
        return await get_all_faqs_helper(db)
    except Exception as e:
        raise handle_error(e, app_logger, "get_all_faqs")


@faq_router.put("/{faq_id}/answer", response_model=FAQRead)
async def answer_faq(
    faq_id: int,
    data: FAQAnswer,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_superuser),
):
    """Ответить на вопрос (только для суперюзера)."""
    try:
        faq = await answer_faq_helper(db, faq_id=faq_id, answer=data.answer)
        if not faq:
            raise HTTPException(
                status_code=404,
                detail={"error": "not_found", "msg": "FAQ not found"}
            )
            
        from app.helpers.email_helpers import send_faq_answer_email
        if faq.email and faq.answer:
            background_tasks.add_task(send_faq_answer_email, faq.email, faq.question, faq.answer)
            
        return faq
    except Exception as e:
        raise handle_error(e, app_logger, "answer_faq")

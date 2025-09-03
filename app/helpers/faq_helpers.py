from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.models import FAQ


async def create_faq_helper(db: AsyncSession, name: str, question: str) -> FAQ:
    faq = FAQ(name=name, question=question)
    db.add(faq)
    await db.commit()
    await db.refresh(faq)
    return faq


async def get_all_faqs_helper(db: AsyncSession) -> Sequence[FAQ]:
    result = await db.execute(select(FAQ))
    return result.scalars().all()


async def answer_faq_helper(db: AsyncSession, faq_id: int, answer: str) -> FAQ | None:
    result = await db.execute(select(FAQ).where(FAQ.id == faq_id))
    faq = result.scalars().first()
    if not faq:
        return None

    faq.answer = answer
    await db.commit()
    await db.refresh(faq)
    return faq

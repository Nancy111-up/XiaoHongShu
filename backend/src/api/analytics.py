from fastapi import APIRouter
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.db.models import Draft, Opportunity


def build_router(sessions: async_sessionmaker[AsyncSession]) -> APIRouter:
    router = APIRouter(tags=["analytics"])

    @router.get("/analytics")
    async def analytics() -> dict[str, int]:
        async with sessions() as session:
            opportunities = await session.scalar(select(func.count()).select_from(Opportunity))
            drafts = await session.scalar(select(func.count()).select_from(Draft))
        return {"opportunities": opportunities or 0, "drafts": drafts or 0}

    return router

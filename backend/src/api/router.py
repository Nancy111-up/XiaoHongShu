from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.api.analytics import build_router as build_analytics_router
from src.api.brand import build_router as build_brand_router
from src.api.content import build_router as build_content_router
from src.api.opportunities import build_router as build_opportunities_router
from src.api.refresh import build_router as build_refresh_router
from src.content.service import ContentService


def build_api_router(
    sessions: async_sessionmaker[AsyncSession], content_service: ContentService | None = None
) -> APIRouter:
    router = APIRouter(prefix="/api")
    router.include_router(build_refresh_router(sessions))
    router.include_router(build_opportunities_router(sessions))
    router.include_router(build_brand_router(sessions))
    router.include_router(build_content_router(sessions, content_service))
    router.include_router(build_analytics_router(sessions))
    return router

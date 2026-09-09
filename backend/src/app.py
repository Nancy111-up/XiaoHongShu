from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.api.refresh import RunRefresh
from src.api.router import build_api_router
from src.content.generator import build_content_service
from src.content.service import ContentService
from src.db.session import session_factory
from src.refresh.runner import build_refresh_runner
from src.refresh.status import RefreshRepository, recover_stale_jobs


def create_app(
    sessions: async_sessionmaker[AsyncSession] = session_factory,
    content_service: ContentService | None = None,
    run_refresh: RunRefresh | None = None,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        await recover_stale_jobs(RefreshRepository(sessions), datetime.now(UTC))
        yield

    app = FastAPI(title="体育品牌运营 Agent", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    refresh = run_refresh or build_refresh_runner(sessions).start
    content = content_service if content_service is not None else build_content_service(sessions)
    app.include_router(build_api_router(sessions, content, refresh))

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "sports-brand-agent"}

    return app

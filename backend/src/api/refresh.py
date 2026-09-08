from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.refresh.status import RefreshRepository

RunRefresh = Callable[[str], Awaitable[None] | None]


def build_router(
    sessions: async_sessionmaker[AsyncSession], run_refresh: RunRefresh
) -> APIRouter:
    router = APIRouter(tags=["refresh"])
    repository = RefreshRepository(sessions)

    @router.post("/refresh-jobs", status_code=202)
    async def create_refresh_job(background_tasks: BackgroundTasks) -> object:
        created = await repository.admit(status="queued", updated_at=datetime.now(UTC))
        if created is None:
            active = await repository.active_job()
            if active is None:
                created = await repository.admit(status="queued", updated_at=datetime.now(UTC))
        if created is None:
            active = await repository.active_job()
            assert active is not None
            return JSONResponse(
                status_code=409,
                content={"code": "REFRESH_ALREADY_RUNNING", "running_job_id": active.id},
            )
        background_tasks.add_task(run_refresh, created.id)
        return {"id": created.id, "status": created.status}

    @router.get("/refresh-jobs/{job_id}")
    async def get_refresh_job(job_id: str) -> object:
        job = await repository.get(job_id)
        if job is None:
            return JSONResponse(status_code=404, content={"code": "REFRESH_JOB_NOT_FOUND"})
        return {"id": job.id, "status": job.status, "updatedAt": job.updated_at}

    return router

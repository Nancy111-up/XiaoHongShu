from __future__ import annotations

from datetime import datetime, timedelta
from typing import Protocol, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.db.models import RefreshJob

WORKING_STATUSES = frozenset(
    {
        "queued",
        "collecting_search",
        "collecting_detail",
        "normalizing",
        "clustering",
        "enriching",
        "scoring_trend",
        "scoring_opportunity",
        "generating_preview",
    }
)
TERMINAL_STATUSES = frozenset({"completed", "partial_success", "failed", "interrupted"})
VALID_STATUSES = WORKING_STATUSES | TERMINAL_STATUSES
ACTIVE_STATUSES = WORKING_STATUSES


class RefreshJobStore(Protocol):
    async def create(
        self, *, status: str, updated_at: datetime, mode: str = "manual"
    ) -> RefreshJob: ...

    async def active_job(self) -> RefreshJob | None: ...

    async def get(self, job_id: str) -> RefreshJob | None: ...

    async def transition(self, job_id: str, status: str, now: datetime) -> RefreshJob: ...

    async def stale_active(self, cutoff: datetime) -> list[RefreshJob]: ...


class RefreshRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def create(
        self, *, status: str, updated_at: datetime, mode: str = "manual"
    ) -> RefreshJob:
        _validate_status(status)
        job = RefreshJob(mode=mode, status=status, started_at=updated_at, updated_at=updated_at)
        async with self._session_factory() as session, session.begin():
            session.add(job)
        return job

    async def active_job(self) -> RefreshJob | None:
        async with self._session_factory() as session:
            return cast(
                RefreshJob | None,
                await session.scalar(
                    select(RefreshJob)
                    .where(RefreshJob.status.in_(WORKING_STATUSES))
                    .order_by(RefreshJob.updated_at.desc())
                    .limit(1)
                ),
            )

    async def get(self, job_id: str) -> RefreshJob | None:
        async with self._session_factory() as session:
            return await session.get(RefreshJob, job_id)

    async def transition(self, job_id: str, status: str, now: datetime) -> RefreshJob:
        _validate_status(status)
        async with self._session_factory() as session, session.begin():
            job = await session.get(RefreshJob, job_id)
            if job is None:
                raise LookupError(f"refresh job {job_id} does not exist")
            job.status = status
            job.updated_at = now
            if status in TERMINAL_STATUSES:
                job.finished_at = now
            return job

    async def stale_active(self, cutoff: datetime) -> list[RefreshJob]:
        async with self._session_factory() as session:
            return list(
                await session.scalars(
                    select(RefreshJob).where(
                        RefreshJob.status.in_(WORKING_STATUSES),
                        RefreshJob.updated_at < cutoff,
                    )
                )
            )


async def recover_stale_jobs(
    repository: RefreshJobStore,
    now: datetime,
    stale_after: timedelta = timedelta(minutes=30),
) -> list[str]:
    recovered: list[str] = []
    for job in await repository.stale_active(now - stale_after):
        await repository.transition(job.id, "interrupted", now)
        recovered.append(job.id)
    return recovered


def _validate_status(status: str) -> None:
    if status not in VALID_STATUSES:
        raise ValueError(f"unknown refresh status: {status}")

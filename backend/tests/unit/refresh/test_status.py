from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from src.refresh.service import RefreshAlreadyRunning, RefreshService
from src.refresh.status import ACTIVE_STATUSES, recover_stale_jobs


class InMemoryRefreshRepository:
    def __init__(self) -> None:
        self.jobs = {}

    async def create(self, *, status: str, updated_at: datetime, mode: str = "manual"):
        from src.db.models import RefreshJob

        job = RefreshJob(mode=mode, status=status, updated_at=updated_at)
        self.jobs[job.id] = job
        return job

    async def active_job(self):
        return next((job for job in self.jobs.values() if job.status in ACTIVE_STATUSES), None)

    async def get(self, job_id: str):
        return self.jobs[job_id]

    async def transition(self, job_id: str, status: str, now: datetime):
        job = self.jobs[job_id]
        job.status = status
        job.updated_at = now
        return job

    async def stale_active(self, cutoff: datetime):
        return [
            job
            for job in self.jobs.values()
            if job.status in ACTIVE_STATUSES and job.updated_at < cutoff
        ]


@pytest.mark.asyncio
async def test_second_refresh_is_rejected() -> None:
    repository = InMemoryRefreshRepository()
    service = RefreshService(repository, now=lambda: datetime(2026, 9, 7, tzinfo=UTC))

    running = await service.start("manual")

    with pytest.raises(RefreshAlreadyRunning) as error:
        await service.start("manual")
    assert error.value.running_job_id == running.id


@pytest.mark.asyncio
async def test_stale_active_job_becomes_interrupted() -> None:
    now = datetime(2026, 9, 7, 12, tzinfo=UTC)
    repository = InMemoryRefreshRepository()
    job = await repository.create(
        status="normalizing", updated_at=now - timedelta(minutes=31)
    )

    recovered = await recover_stale_jobs(repository, now)

    assert recovered == [job.id]
    assert (await repository.get(job.id)).status == "interrupted"

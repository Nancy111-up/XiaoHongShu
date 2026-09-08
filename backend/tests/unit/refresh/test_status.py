from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from src.db.base import Base
from src.db.session import create_session_factory
from src.refresh.service import RefreshAlreadyRunning, RefreshService
from src.refresh.status import ACTIVE_STATUSES, RefreshRepository, recover_stale_jobs


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


@pytest.mark.asyncio
async def test_repository_fail_persists_safe_summary_and_terminal_state(tmp_path) -> None:
    factory = create_session_factory(
        f"sqlite+aiosqlite:///{(tmp_path / 'refresh-status.db').as_posix()}"
    )
    now = datetime(2026, 9, 8, 12, tzinfo=UTC)
    async with factory() as session, session.bind.begin() as connection:  # type: ignore[union-attr]
        await connection.run_sync(Base.metadata.create_all)
    repository = RefreshRepository(factory)
    job = await repository.create(status="queued", updated_at=now)

    failed = await repository.fail(job.id, "需要重新登录采集账号", now)

    assert failed.status == "failed"
    assert failed.error_summary == "需要重新登录采集账号"
    assert failed.finished_at == now
    assert (await repository.get(job.id)).error_summary == "需要重新登录采集账号"


@pytest.mark.asyncio
async def test_repository_records_safe_summary_without_changing_partial_status(tmp_path) -> None:
    factory = create_session_factory(
        f"sqlite+aiosqlite:///{(tmp_path / 'refresh-status.db').as_posix()}"
    )
    now = datetime(2026, 9, 8, 12, tzinfo=UTC)
    async with factory() as session, session.bind.begin() as connection:  # type: ignore[union-attr]
        await connection.run_sync(Base.metadata.create_all)
    repository = RefreshRepository(factory)
    job = await repository.create(status="partial_success", updated_at=now)

    updated = await repository.record_error_summary(job.id, "详情采集失败，已保留搜索结果。", now)

    assert updated.status == "partial_success"
    assert updated.error_summary == "详情采集失败，已保留搜索结果。"
    assert (await repository.get(job.id)).error_summary == "详情采集失败，已保留搜索结果。"

from datetime import UTC, datetime

import pytest

from src.db.models import RefreshJob
from src.refresh.runner import RefreshRunner


class FakeRepository:
    def __init__(self, job: RefreshJob) -> None:
        self.job = job
        self.transitions: list[tuple[str, str, datetime]] = []

    async def get(self, job_id: str) -> RefreshJob | None:
        return self.job if job_id == self.job.id else None

    async def transition(self, job_id: str, status: str, now: datetime) -> RefreshJob:
        self.transitions.append((job_id, status, now))
        self.job.status = status
        return self.job


class FakeKeywords:
    async def load(self) -> list[str]:
        return ["夜跑", "运动恢复"]


class RecordingCoordinator:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[tuple[RefreshJob, list[str], object, datetime]] = []

    async def run(self, job, keywords, raw_root, now):  # type: ignore[no-untyped-def]
        self.calls.append((job, keywords, raw_root, now))
        if self.error is not None:
            raise self.error
        return job


@pytest.mark.asyncio
async def test_runner_uses_brand_keywords_and_job_scoped_raw_path(tmp_path) -> None:
    now = datetime(2026, 9, 8, tzinfo=UTC)
    job = RefreshJob(id="job-1", mode="manual", status="queued", started_at=now)
    coordinator = RecordingCoordinator()
    runner = RefreshRunner(
        FakeRepository(job),  # type: ignore[arg-type]
        coordinator,
        FakeKeywords(),
        tmp_path / "raw",
        now=lambda: now,
    )

    await runner.start(job.id)

    assert coordinator.calls == [(job, ["夜跑", "运动恢复"], tmp_path / "raw" / job.id, now)]


@pytest.mark.asyncio
async def test_runner_marks_job_failed_when_coordination_raises(tmp_path) -> None:
    now = datetime(2026, 9, 8, tzinfo=UTC)
    job = RefreshJob(id="job-1", mode="manual", status="queued", started_at=now)
    repository = FakeRepository(job)
    runner = RefreshRunner(
        repository,  # type: ignore[arg-type]
        RecordingCoordinator(RuntimeError("crawler unavailable")),
        FakeKeywords(),
        tmp_path / "raw",
        now=lambda: now,
    )

    await runner.start(job.id)

    assert repository.transitions == [(job.id, "failed", now)]

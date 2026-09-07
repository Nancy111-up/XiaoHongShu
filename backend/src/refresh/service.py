from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from src.db.models import RefreshJob
from src.refresh.status import RefreshJobStore


class RefreshAlreadyRunning(Exception):  # noqa: N818 - public contract name
    code = "REFRESH_ALREADY_RUNNING"

    def __init__(self, running_job_id: str) -> None:
        super().__init__(f"refresh job {running_job_id} is already running")
        self.running_job_id = running_job_id


class RefreshService:
    def __init__(
        self, repository: RefreshJobStore, now: Callable[[], datetime] = lambda: datetime.now(UTC)
    ) -> None:
        self._repository = repository
        self._now = now

    async def start(self, mode: str) -> RefreshJob:
        running = await self._repository.active_job()
        if running is not None:
            raise RefreshAlreadyRunning(running.id)
        return await self._repository.create(status="queued", updated_at=self._now(), mode=mode)

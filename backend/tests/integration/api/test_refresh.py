from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Barrier

import pytest
from fastapi.testclient import TestClient

from src.app import create_app
from src.db.base import Base
from src.db.models import RefreshJob
from src.db.session import create_session_factory
from src.refresh.status import RefreshRepository


def create_app_for_test(tmp_path, run_refresh, factory=None):  # type: ignore[no-untyped-def]
    factory = factory or create_session_factory(
        f"sqlite+aiosqlite:///{(tmp_path / 'refresh.db').as_posix()}"
    )

    async def initialize() -> None:
        async with factory() as session, session.bind.begin() as connection:  # type: ignore[union-attr]
            await connection.run_sync(Base.metadata.create_all)

    import asyncio

    asyncio.run(initialize())
    return create_app(factory, run_refresh=run_refresh)


def test_creating_refresh_dispatches_only_persisted_job(tmp_path) -> None:
    factory = create_session_factory(
        f"sqlite+aiosqlite:///{(tmp_path / 'refresh.db').as_posix()}"
    )
    dispatched: list[tuple[str, str] | None] = []

    async def run_refresh(job_id: str) -> None:
        job = await RefreshRepository(factory).get(job_id)
        dispatched.append(None if job is None else (job.id, job.status))

    app = create_app_for_test(tmp_path, run_refresh=run_refresh, factory=factory)

    response = TestClient(app).post("/api/refresh-jobs")

    assert response.status_code == 202
    assert dispatched == [(response.json()["id"], "queued")]


def test_overlapping_refreshes_admit_one_job_and_dispatch_once(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dispatched: list[str] = []
    creation_barrier = Barrier(2)
    original_create = RefreshRepository.create

    async def synchronized_create(self, **kwargs):  # type: ignore[no-untyped-def]
        creation_barrier.wait(timeout=5)
        return await original_create(self, **kwargs)

    monkeypatch.setattr(RefreshRepository, "create", synchronized_create)
    app = create_app_for_test(tmp_path, run_refresh=lambda job_id: dispatched.append(job_id))

    def post_refresh():  # type: ignore[no-untyped-def]
        with TestClient(app) as client:
            return client.post("/api/refresh-jobs")

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(lambda _: post_refresh(), range(2)))

    successful = next(response for response in responses if response.status_code == 202)
    conflict = next(response for response in responses if response.status_code == 409)
    assert conflict.json() == {
        "code": "REFRESH_ALREADY_RUNNING",
        "running_job_id": successful.json()["id"],
    }
    assert dispatched == [successful.json()["id"]]


def test_second_refresh_returns_exact_conflict(tmp_path) -> None:
    factory = create_session_factory(f"sqlite+aiosqlite:///{(tmp_path / 'refresh.db').as_posix()}")

    async def seed() -> None:
        async with factory() as session:
            async with session.bind.begin() as connection:  # type: ignore[union-attr]
                await connection.run_sync(Base.metadata.create_all)
            session.add(
                RefreshJob(
                    id="job-running-1",
                    mode="manual",
                    status="collecting_search",
                    started_at=datetime.now(UTC),
                )
            )
            await session.commit()

    import asyncio

    asyncio.run(seed())
    response = TestClient(create_app(factory)).post("/api/refresh-jobs")
    assert response.status_code == 409
    assert response.json() == {"code": "REFRESH_ALREADY_RUNNING", "running_job_id": "job-running-1"}

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from src.app import create_app
from src.db.base import Base
from src.db.models import RefreshJob
from src.db.session import create_session_factory


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

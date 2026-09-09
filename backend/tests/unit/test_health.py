import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from fastapi.testclient import TestClient

from src.app import create_app
from src.db.base import Base
from src.db.models import RefreshJob
from src.db.session import create_session_factory


def test_health_reports_service_ready() -> None:
    response = TestClient(create_app()).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "sports-brand-agent"}


def test_default_app_wires_content_service(monkeypatch) -> None:
    class FakeContentService:
        async def reject_opportunity(self, opportunity_id, payload):
            return SimpleNamespace(id="feedback-1", reason=payload.reason)

    monkeypatch.setattr("src.app.build_content_service", lambda sessions: FakeContentService())

    response = TestClient(create_app()).post(
        "/api/opportunities/opportunity-1/reject", json={"reason": "other"}
    )

    assert response.status_code == 200
    assert response.json() == {"id": "feedback-1", "reason": "other"}


def test_startup_recovers_stale_refresh_and_releases_active_slot(tmp_path) -> None:
    factory = create_session_factory(f"sqlite+aiosqlite:///{(tmp_path / 'startup.db').as_posix()}")
    stale_at = datetime.now(UTC) - timedelta(hours=1)

    async def seed() -> None:
        async with factory() as session:
            async with session.bind.begin() as connection:  # type: ignore[union-attr]
                await connection.run_sync(Base.metadata.create_all)
            session.add(
                RefreshJob(
                    id="abandoned", mode="manual", status="collecting_search", updated_at=stale_at
                )
            )
            await session.commit()

    asyncio.run(seed())
    with TestClient(create_app(factory)) as client:
        assert client.get("/health").status_code == 200

    async def read() -> tuple[str, str | None]:
        async with factory() as session:
            job = await session.get(RefreshJob, "abandoned")
            assert job is not None
            return job.status, job.active_slot

    assert asyncio.run(read()) == ("interrupted", None)

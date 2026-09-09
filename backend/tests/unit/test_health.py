from types import SimpleNamespace

from fastapi.testclient import TestClient

from src.app import create_app


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

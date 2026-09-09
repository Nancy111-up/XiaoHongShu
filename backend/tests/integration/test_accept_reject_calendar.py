from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from src.api.content import build_router
from src.content.repository import ContentRepository
from src.content.schemas import CopyPreview, FullDraftContent, RejectInput
from src.content.service import ContentService
from src.db.base import Base
from src.db.models import BrandProfile, CalendarItem, Opportunity, RefreshJob, Topic, TopicSnapshot
from src.db.session import create_session_factory


class FakeGenerator:
    async def generate_preview(self, opportunity: Opportunity) -> CopyPreview:
        return CopyPreview(
            titles=["标题一", "标题二", "标题三"],
            body="跑" * 100,
            angle="夜跑补给",
            format="图文",
            tags=["夜跑"],
            cover_direction="城市夜色",
            product_connection="自然穿着",
            cost="low",
        )

    async def generate_full_copy(self, opportunity: Opportunity) -> FullDraftContent:
        return FullDraftContent(
            titles=["标题一", "标题二", "标题三"],
            body="完整正文",
            tags=["夜跑"],
            cta="分享路线",
            cover_text="今晚开跑",
            image_count=3,
            image_advice=["人物", "路线", "装备"],
            product_connection="自然穿着",
            risk_check={"status": "passed"},
            prompt_version="full_copy_v1",
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "when",
    [
        "2026-09-15T01:30:00Z",
        "2026-09-15T09:30:00+08:00",
        "2026-09-14T20:30:00-05:00",
    ],
)
async def test_accept_reject_and_schedule_workflow(tmp_path, when: str) -> None:
    factory = create_session_factory(f"sqlite+aiosqlite:///{(tmp_path / 'workflow.db').as_posix()}")
    now = datetime(2026, 9, 7, tzinfo=UTC)
    async with factory() as session:
        async with session.bind.begin() as connection:  # type: ignore[union-attr]
            await connection.run_sync(Base.metadata.create_all)
        session.add_all(
            [
                RefreshJob(id="job", mode="manual", status="completed", started_at=now),
                Topic(
                    topic_id="topic",
                    canonical_name="夜跑",
                    first_seen_at=now,
                    last_seen_at=now,
                    status="Growing",
                ),
                TopicSnapshot(
                    id="snapshot",
                    topic_id="topic",
                    job_id="job",
                    captured_at=now,
                    note_count=3,
                    unique_author_count=3,
                    comment_sample_count=10,
                    raw_metrics_json="{}",
                    normalized_metrics_json="{}",
                    current_heat=80,
                    trend_score=70,
                    lifecycle="Growing",
                    confidence="High",
                ),
                BrandProfile(version=4, profile_json="{}"),
                Opportunity(
                    id="opportunity",
                    topic_id="topic",
                    topic_snapshot_id="snapshot",
                    job_id="job",
                    brand_profile_version=4,
                    title="夜跑机会",
                    score=82,
                    decision="High Opportunity",
                    eligibility="eligible",
                    risk="low",
                    confidence="High",
                    score_breakdown_json="{}",
                    reasons_json="{}",
                ),
                Opportunity(
                    id="filtered",
                    topic_id="topic",
                    topic_snapshot_id="snapshot",
                    job_id="job",
                    brand_profile_version=4,
                    title="风险机会",
                    score=None,
                    decision="Filtered",
                    eligibility="filtered",
                    risk="high",
                    confidence="High",
                    score_breakdown_json="{}",
                    reasons_json="{}",
                ),
            ]
        )
        await session.commit()

    service = ContentService(ContentRepository(factory), FakeGenerator())
    preview = await service.generate_preview("opportunity")
    draft = await service.accept_opportunity("opportunity")
    rejection = await service.reject_opportunity("opportunity", RejectInput(reason="tone_mismatch"))
    app = FastAPI()
    app.include_router(build_router(factory, service), prefix="/api")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        scheduled = await client.post(f"/api/drafts/{draft.id}/schedule", params={"when": when})
        assert scheduled.status_code == 200
        calendar = await client.get("/api/calendar")
        assert calendar.status_code == 200

    # The POST refresh and later GET both cross a real SQLite persistence boundary.
    # All three input offsets represent 09:30 in Shanghai and must return that instant.
    for item in [scheduled.json(), calendar.json()["items"][0]]:
        assert item["draftId"] == draft.id
        assert item["scheduledFor"] == "2026-09-15T01:30:00+00:00"
        shanghai = datetime.fromisoformat(item["scheduledFor"]).astimezone(
            timezone(timedelta(hours=8))
        )
        assert shanghai.strftime("%Y-%m-%d %H:%M") == "2026-09-15 09:30"
    async with factory() as session:
        stored = await session.get(CalendarItem, scheduled.json()["id"])
        assert stored is not None
        assert stored.scheduled_for == datetime(2026, 9, 15, 1, 30)

    assert len(preview.titles) == 3
    assert draft.source_opportunity_id == "opportunity"
    assert draft.topic_id == "topic" and draft.brand_profile_version == 4
    assert draft.prompt_version == "full_copy_v1"
    assert len(json.loads(draft.titles_json)) == 3
    assert json.loads(draft.image_plan_json)["image_count"] == 3
    assert json.loads(draft.risk_check_json)["status"] == "passed"
    assert rejection.reason == "tone_mismatch"

    with pytest.raises(ValueError, match="filtered"):
        await service.accept_opportunity("filtered")


def test_reject_reason_only_accepts_contract_enums() -> None:
    with pytest.raises(ValidationError):
        RejectInput(reason="change_the_model")

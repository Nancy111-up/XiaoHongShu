from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from src.content.repository import ContentRepository
from src.content.schemas import CopyPreview, FullDraftContent, RejectInput
from src.content.service import ContentService
from src.db.base import Base
from src.db.models import BrandProfile, Opportunity, RefreshJob, Topic, TopicSnapshot
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
async def test_accept_reject_and_schedule_workflow(tmp_path) -> None:
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
    scheduled = await service.schedule_draft(draft.id, now + timedelta(days=1))

    assert len(preview.titles) == 3
    assert draft.source_opportunity_id == "opportunity"
    assert draft.topic_id == "topic" and draft.brand_profile_version == 4
    assert draft.prompt_version == "full_copy_v1"
    assert len(json.loads(draft.titles_json)) == 3
    assert json.loads(draft.image_plan_json)["image_count"] == 3
    assert json.loads(draft.risk_check_json)["status"] == "passed"
    assert rejection.reason == "tone_mismatch"
    assert scheduled.draft_id == draft.id

    with pytest.raises(ValueError, match="filtered"):
        await service.accept_opportunity("filtered")


def test_reject_reason_only_accepts_contract_enums() -> None:
    with pytest.raises(ValidationError):
        RejectInput(reason="change_the_model")

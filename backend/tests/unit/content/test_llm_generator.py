import json
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from src.content.generator import LLMContentGenerator
from src.db.base import Base
from src.db.models import (
    BrandProfile,
    Comment,
    Note,
    Opportunity,
    RefreshJob,
    Topic,
    TopicSnapshot,
    TopicSnapshotNote,
)
from src.db.session import create_session_factory
from src.llm.schemas import FullCopy


class FakeLLM:
    async def generate_full_copy(self, **context):
        assert context["job_id"] == "job-1"
        assert context["topic_id"] == "topic-1"
        return FullCopy(
            title="夜跑装备这样选",
            body="从真实趋势证据出发，说明夜跑装备的选择方法。",
            hashtags=["夜跑", "跑步装备"],
            evidence_note_ids=[],
            evidence_comment_ids=[],
        )


@pytest.mark.asyncio
async def test_full_copy_maps_to_persistable_draft_contract() -> None:
    opportunity = SimpleNamespace(
        job_id="job-1",
        topic_id="topic-1",
        title="夜跑装备",
        reasons_json='{"why_now":"热度正在上升"}',
        copy_preview_json='{"call_to_action":"分享你的夜跑路线"}',
    )

    draft = await LLMContentGenerator(FakeLLM()).generate_full_copy(opportunity)

    assert draft.titles == [
        "夜跑装备这样选",
        "夜跑装备｜夜跑装备这样选",
        "夜跑装备这样选｜实用指南",
    ]
    assert draft.tags == ["夜跑", "跑步装备"]
    assert draft.cta == "分享你的夜跑路线"
    assert draft.prompt_version == "full_copy_v1"


@pytest.mark.asyncio
async def test_full_copy_uses_exact_brand_version_and_topic_evidence(tmp_path) -> None:
    factory = create_session_factory(f"sqlite+aiosqlite:///{(tmp_path / 'grounded.db').as_posix()}")
    now = datetime(2026, 9, 9, tzinfo=UTC)
    captured: dict[str, object] = {}

    class GroundedLLM:
        async def generate_full_copy(self, **context):
            captured.update(context)
            return FullCopy(
                title="可信夜跑建议",
                body="只引用已加载证据",
                hashtags=["夜跑"],
                evidence_note_ids=["note-1"],
                evidence_comment_ids=["comment-1"],
            )

    async with factory() as session:
        async with session.bind.begin() as connection:  # type: ignore[union-attr]
            await connection.run_sync(Base.metadata.create_all)
        session.add_all(
            [
                BrandProfile(version=1, profile_json=json.dumps({"tone": ["旧语气"]})),
                BrandProfile(
                    version=2,
                    profile_json=json.dumps(
                        {
                            "tone": ["专业清新"],
                            "forbidden": ["绝对化承诺"],
                            "products": [{"name": "轻量跑鞋", "selling_point": "透气"}],
                        },
                        ensure_ascii=False,
                    ),
                ),
                RefreshJob(id="job-1", mode="manual", status="completed", updated_at=now),
                Topic(
                    topic_id="topic-1",
                    canonical_name="夜跑",
                    first_seen_at=now,
                    last_seen_at=now,
                    status="Growing",
                ),
                Note(
                    note_id="note-1",
                    title="夜跑体验",
                    body="真实笔记正文",
                    first_seen_at=now,
                    last_seen_at=now,
                    raw_payload_json="{}",
                    url="https://www.xiaohongshu.com/explore/note-1",
                ),
            ]
        )
        await session.flush()
        snapshot = TopicSnapshot(
            topic_id="topic-1",
            job_id="job-1",
            captured_at=now,
            note_count=1,
            unique_author_count=1,
            comment_sample_count=1,
            raw_metrics_json="{}",
            normalized_metrics_json="{}",
            current_heat=80,
            confidence="High",
        )
        session.add(snapshot)
        await session.flush()
        session.add_all(
            [
                TopicSnapshotNote(
                    topic_snapshot_id=snapshot.id, note_id="note-1", is_representative=True
                ),
                Comment(
                    comment_id="comment-1",
                    note_id="note-1",
                    job_id="job-1",
                    content="想知道尺码",
                    captured_at=now,
                ),
            ]
        )
        opportunity = Opportunity(
            id="opp-1",
            topic_id="topic-1",
            topic_snapshot_id=snapshot.id,
            job_id="job-1",
            brand_profile_version=2,
            title="夜跑装备",
            decision="Recommend",
            eligibility="eligible",
            risk="low",
            confidence="High",
            score_breakdown_json="{}",
            reasons_json="{}",
        )
        session.add(opportunity)
        await session.commit()

    async with factory() as session:
        opportunity = await session.get(Opportunity, "opp-1")
        assert opportunity is not None
    await LLMContentGenerator(GroundedLLM(), factory).generate_full_copy(opportunity)  # type: ignore[arg-type]

    assert captured["brand_profile"] == {
        "tone": ["专业清新"],
        "forbidden": ["绝对化承诺"],
        "products": [{"name": "轻量跑鞋", "selling_point": "透气"}],
    }
    assert captured["note_ids"] == ["note-1"]
    assert captured["comment_ids"] == ["comment-1"]
    assert captured["notes"] == [
        {
            "note_id": "note-1",
            "title": "夜跑体验",
            "body": "真实笔记正文",
            "url": "https://www.xiaohongshu.com/explore/note-1",
        }
    ]
    assert captured["comments"] == [
        {"comment_id": "comment-1", "note_id": "note-1", "content": "想知道尺码"}
    ]

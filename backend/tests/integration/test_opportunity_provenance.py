from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from src.db.base import Base
from src.db.models import (
    BrandProfile,
    LLMRun,
    Note,
    NoteSnapshot,
    Opportunity,
    OpportunityLLMRun,
    RefreshJob,
    Topic,
    TopicSnapshot,
    TopicSnapshotNote,
)
from src.db.session import create_session_factory
from src.opportunities.repository import OpportunityRepository
from src.opportunities.schemas import OpportunityAnalysisInput
from src.opportunities.service import OpportunityService


@pytest.mark.asyncio
async def test_opportunity_traces_to_source_note_llm_run_and_brand_version(tmp_path) -> None:
    factory = create_session_factory(
        f"sqlite+aiosqlite:///{(tmp_path / 'provenance.db').as_posix()}"
    )
    now = datetime(2026, 9, 7, tzinfo=UTC)
    async with factory() as session:
        async with session.bind.begin() as connection:  # type: ignore[union-attr]
            await connection.run_sync(Base.metadata.create_all)
        session.add_all(
            [
                RefreshJob(
                    id="job",
                    mode="manual",
                    status="completed",
                    started_at=now,
                    finished_at=now,
                    successful_keywords="[]",
                    failed_keywords="[]",
                ),
                Note(
                    note_id="note",
                    title="跑步",
                    url="https://example.test/note",
                    first_seen_at=now,
                    last_seen_at=now,
                    raw_payload_json="{}",
                ),
                NoteSnapshot(
                    id="ns",
                    job_id="job",
                    note_id="note",
                    captured_at=now,
                    likes=10,
                    collects=2,
                    comments=1,
                    shares=None,
                    data_completeness=1,
                ),
                Topic(
                    topic_id="topic",
                    canonical_name="城市跑步",
                    first_seen_at=now,
                    last_seen_at=now,
                    status="Growing",
                ),
                TopicSnapshot(
                    id="ts",
                    topic_id="topic",
                    job_id="job",
                    captured_at=now,
                    note_count=1,
                    unique_author_count=1,
                    comment_sample_count=0,
                    raw_metrics_json="{}",
                    normalized_metrics_json="{}",
                    current_heat=70,
                    trend_score=60,
                    lifecycle="Growing",
                    confidence="Medium",
                ),
                TopicSnapshotNote(topic_snapshot_id="ts", note_id="note", is_representative=True),
                BrandProfile(version=1, profile_json="{}"),
                LLMRun(
                    id="run",
                    task_type="score_brand_relevance",
                    job_id="job",
                    topic_id="topic",
                    model="model",
                    prompt_version="v1",
                    schema_version="v1",
                    temperature=0,
                    input_hash="hash",
                    input_json="{}",
                    status="completed",
                ),
            ]
        )
        await session.commit()

    service = OpportunityService(OpportunityRepository(factory))
    created = await service.analyze_topic(
        OpportunityAnalysisInput(
            topic_id="topic",
            topic_snapshot_id="ts",
            job_id="job",
            brand_profile_version=1,
            title="城市夜跑装备机会",
            risk="low",
            confidence="Medium",
            lifecycle="Growing",
            current_heat=70,
            trend_score=60,
            brand_relevance=80,
            audience_relevance=75,
            content_opportunity=70,
            product_fit=65,
            llm_run_ids=["run"],
            reasons={"why_now": "热度增长"},
        )
    )

    async with factory() as session:
        stored = await session.get(Opportunity, created.id)
        link = await session.scalar(
            select(OpportunityLLMRun).where(OpportunityLLMRun.opportunity_id == created.id)
        )
        source = await session.scalar(
            select(Note)
            .join(TopicSnapshotNote, TopicSnapshotNote.note_id == Note.note_id)
            .where(TopicSnapshotNote.topic_snapshot_id == stored.topic_snapshot_id)
        )
    assert stored.brand_profile_version == 1
    assert link.llm_run_id == "run"
    assert source.url == "https://example.test/note"

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest
from sqlalchemy import select

from src.app import create_app
from src.db.base import Base
from src.db.models import (
    BrandProfile,
    Comment,
    LLMRun,
    Note,
    NoteSnapshot,
    Opportunity,
    OpportunityLLMRun,
    Topic,
    TopicSnapshot,
    TopicSnapshotNote,
)
from src.db.session import create_session_factory
from src.llm.repository import LLMRunRepository
from src.llm.service import LLMService
from src.notes.repository import NoteRepository
from src.refresh.runner import BrandKeywordProvider, RefreshRunner, RepresentativeResolver
from src.refresh.service import TwoPassRefreshCoordinator
from src.refresh.status import RefreshRepository
from tests.integration.test_two_pass_refresh import FakeAdapter

NOW = datetime(2026, 9, 8, tzinfo=UTC)
PROMPTS = Path(__file__).resolve().parents[2] / "prompts"


class EvidenceClient:
    """Replace only the external model; collection/persistence/services stay real."""

    def __init__(self, *, invented: bool = False, unavailable: bool = False) -> None:
        self.invented = invented
        self.unavailable = unavailable

    async def complete(self, **kwargs: object) -> str:
        if self.unavailable:
            raise RuntimeError("Authorization: Bearer private-fixture-secret")
        payload = json.loads(str(kwargs["input"]))
        schema = kwargs["json_schema"]
        name = schema["title"]
        if name == "TopicClusters":
            ids = [note["note_id"] for note in payload[:3]]
            if self.invented:
                ids.append("not-collected")
            return json.dumps({"clusters": [{"name": "夜跑装备", "note_ids": ids}]})
        evidence = {"evidence_note_ids": payload["note_ids"], "evidence_comment_ids": []}
        if name == "ScoredEvidence":
            return json.dumps({"score": 82, "reason": "来源笔记讨论夜跑装备", **evidence})
        if name == "ContentGap":
            return json.dumps(
                {
                    "score": 75,
                    "risk": "low",
                    "gap": "缺少装备比较",
                    "angle": "夜跑装备选择",
                    **evidence,
                }
            )
        if name == "OpportunityExplanation":
            return json.dumps(
                dict.fromkeys(
                    (
                        "audience_need",
                        "content_gap",
                        "why_now",
                        "why_brand",
                        "why_audience",
                        "why_this_angle",
                        "product_connection",
                    ),
                    "基于来源笔记的装备需求",
                )
                | evidence
            )
        if name == "CopyPreview":
            return json.dumps(
                {
                    "title": "夜跑装备怎么选",
                    "hook": "从使用场景出发",
                    "outline": ["场景", "选择"],
                    "call_to_action": "分享体验",
                    **evidence,
                }
            )
        raise AssertionError(f"Unexpected schema: {name}")


async def setup_refresh(tmp_path, client=None, *, detail_fails=False):
    from src.opportunities.pipeline import OpportunityPipeline

    factory = create_session_factory(f"sqlite+aiosqlite:///{(tmp_path / 'flow.db').as_posix()}")
    async with factory() as session:
        async with session.bind.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        session.add(
            BrandProfile(
                version=1,
                profile_json=json.dumps({"positioning": "夜跑", "audiences": [], "products": []}),
            )
        )
        await session.commit()
    statuses = RefreshRepository(factory)
    llm = (
        LLMService(client, LLMRunRepository(factory), PROMPTS, "fixture-model") if client else None
    )
    pipeline = OpportunityPipeline(factory, llm)
    coordinator = TwoPassRefreshCoordinator(
        FakeAdapter(NOW, detail_fails=detail_fails),
        NoteRepository(factory),
        statuses,
        RepresentativeResolver(),
        finalize=False,
    )
    runner = RefreshRunner(
        statuses,
        coordinator,
        BrandKeywordProvider(factory),
        tmp_path / "raw",
        now=lambda: NOW,
        pipeline=pipeline,
    )
    return factory, statuses, runner, pipeline


@pytest.mark.asyncio
async def test_refresh_persists_source_links_scores_and_llm_provenance(tmp_path) -> None:
    factory, statuses, runner, pipeline = await setup_refresh(tmp_path, EvidenceClient())
    job = await statuses.create(status="queued", updated_at=NOW)

    await runner.start(job.id)

    assert (await statuses.get(job.id)).status == "completed"
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app(factory)), base_url="http://test"
    ) as client:
        response = await client.get("/api/opportunities")
    item = response.json()["items"][0]
    assert item["sources"] and len(item["sources"]) == 3
    assert all(
        source["url"].startswith("https://www.xiaohongshu.com/explore/")
        for source in item["sources"]
    )
    assert 0 <= item["currentHeat"] <= 100
    assert item["trendScore"] is None and item["trendStage"] == "Observing"
    assert item["scores"]["content_opportunity"] == 75
    assert item["preview"]["title"] == "夜跑装备怎么选"
    async with factory() as session:
        opportunity = await session.get(Opportunity, item["id"])
        runs = list(
            await session.scalars(
                select(LLMRun)
                .join(OpportunityLLMRun, OpportunityLLMRun.llm_run_id == LLMRun.id)
                .where(OpportunityLLMRun.opportunity_id == opportunity.id)
            )
        )
        snapshot = await session.get(TopicSnapshot, opportunity.topic_snapshot_id)
        sources = list(
            await session.scalars(
                select(NoteSnapshot)
                .join(TopicSnapshotNote, TopicSnapshotNote.note_id == NoteSnapshot.note_id)
                .where(
                    TopicSnapshotNote.topic_snapshot_id == snapshot.id,
                    NoteSnapshot.job_id == job.id,
                )
            )
        )
    assert len(sources) == 3
    assert opportunity.brand_profile_version == 1
    assert len(runs) == 7 and all(run.job_id == job.id for run in runs)
    assert all(
        run.topic_id == opportunity.topic_id for run in runs if run.task_type != "cluster_topics"
    )
    assert json.loads(snapshot.raw_metrics_json)["engagement"] > 0
    assert json.loads(snapshot.normalized_metrics_json)["engagement"] is not None
    # Rebuilding the same job must not duplicate opportunities or evidence snapshots.
    assert [row.id for row in await pipeline.build(job.id)] == [item["id"]]


@pytest.mark.asyncio
async def test_second_refresh_reuses_topic_and_computes_trend_from_history(tmp_path) -> None:
    factory, statuses, runner, _ = await setup_refresh(tmp_path, EvidenceClient())
    for day in range(2):
        job = await statuses.create(status="queued", updated_at=NOW + timedelta(days=day))
        await runner.start(job.id)
    async with factory() as session:
        snapshots = list(
            await session.scalars(select(TopicSnapshot).order_by(TopicSnapshot.captured_at))
        )
    assert len(snapshots) == 2
    assert snapshots[0].topic_id == snapshots[1].topic_id
    assert snapshots[0].trend_score is None
    assert snapshots[1].trend_score is not None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "client", [None, EvidenceClient(unavailable=True), EvidenceClient(invented=True)]
)
async def test_unavailable_ai_retains_notes_without_fabricating_opportunities(
    tmp_path, client
) -> None:
    factory, statuses, runner, _ = await setup_refresh(tmp_path, client)
    job = await statuses.create(status="queued", updated_at=NOW)
    await runner.start(job.id)

    stored = await statuses.get(job.id)
    assert stored.status == "partial_success"
    assert "AI" in stored.error_summary and "private-fixture-secret" not in stored.error_summary
    assert stored.active_slot is None
    async with factory() as session:
        assert await session.scalar(select(Note)) is not None
        assert await session.scalar(select(Opportunity)) is None
        if client is not None:
            failed_run = await session.scalar(select(LLMRun).where(LLMRun.status == "failed"))
            assert failed_run is not None
            assert "private-fixture-secret" not in (failed_run.error or "")


@pytest.mark.asyncio
async def test_detail_failure_remains_partial_after_successful_analysis(tmp_path) -> None:
    factory, statuses, runner, _ = await setup_refresh(
        tmp_path, EvidenceClient(), detail_fails=True
    )
    job = await statuses.create(status="queued", updated_at=NOW)
    await runner.start(job.id)
    stored = await statuses.get(job.id)
    assert stored.status == "partial_success" and "详情采集失败" in stored.error_summary
    async with factory() as session:
        assert await session.scalar(select(Opportunity)) is not None


class TwoTopicEvidenceClient(EvidenceClient):
    async def complete(self, **kwargs: object) -> str:
        payload = json.loads(str(kwargs["input"]))
        name = kwargs["json_schema"]["title"]
        if name == "TopicClusters":
            return json.dumps(
                {
                    "clusters": [
                        {"name": group, "note_ids": [f"{group}-{index}" for index in range(3)]}
                        for group in ("running", "football")
                    ]
                }
            )
        if name == "TopicResolution":
            return json.dumps(
                {
                    "canonical_topic_id": payload["candidate"],
                    "canonical_name": payload["candidate"],
                    "confidence": 0.95,
                }
            )
        if name == "CommentAnalysis":
            return json.dumps(
                {
                    "analyzed_comment_count": len(payload),
                    "categories": {
                        "question": [comment["comment_id"] for comment in payload],
                        "pain_point": [],
                        "request": [],
                        "purchase_intent": [],
                        "experience": [],
                        "other": [],
                    },
                }
            )
        return await super().complete(**kwargs)


@pytest.mark.asyncio
async def test_two_topics_link_only_their_own_identity_comment_and_evidence_runs(tmp_path) -> None:
    factory, statuses, _, pipeline = await setup_refresh(tmp_path, TwoTopicEvidenceClient())
    job = await statuses.create(status="enriching", updated_at=NOW)
    async with factory() as session:
        for group in ("running", "football"):
            # Existing topics without note overlap force semantic identity resolution for both.
            session.add(
                Topic(
                    topic_id=group,
                    canonical_name=group,
                    first_seen_at=NOW,
                    last_seen_at=NOW,
                    status="Observing",
                )
            )
            for index in range(3):
                note_id = f"{group}-{index}"
                session.add(
                    Note(
                        note_id=note_id,
                        title=note_id,
                        body=f"{group} evidence",
                        author_id=f"author-{note_id}",
                        first_seen_at=NOW,
                        last_seen_at=NOW,
                        published_at=NOW,
                        raw_payload_json="{}",
                        url=f"https://www.xiaohongshu.com/explore/{note_id}",
                    )
                )
                session.add(
                    NoteSnapshot(
                        job_id=job.id,
                        note_id=note_id,
                        captured_at=NOW,
                        likes=10,
                        collects=2,
                        comments=5,
                        data_completeness=1,
                    )
                )
            for index in range(10):
                session.add(
                    Comment(
                        comment_id=f"{group}-comment-{index}",
                        job_id=job.id,
                        note_id=f"{group}-{index % 3}",
                        content=f"{group} question",
                        captured_at=NOW,
                    )
                )
        await session.commit()

    opportunities = await pipeline.build(job.id)

    assert {opportunity.topic_id for opportunity in opportunities} == {"running", "football"}
    linked_run_ids = []
    async with factory() as session:
        cluster_run = await session.scalar(
            select(LLMRun).where(LLMRun.job_id == job.id, LLMRun.task_type == "cluster_topics")
        )
        for opportunity in opportunities:
            group = opportunity.topic_id
            runs = list(
                await session.scalars(
                    select(LLMRun)
                    .join(OpportunityLLMRun, OpportunityLLMRun.llm_run_id == LLMRun.id)
                    .where(OpportunityLLMRun.opportunity_id == opportunity.id)
                )
            )
            assert len(runs) == 9  # One shared cluster, own identity/comments, six semantic tasks.
            assert {run.task_type for run in runs} >= {
                "cluster_topics",
                "resolve_topic_identity",
                "analyze_comments",
            }
            for run in runs:
                if run.task_type == "cluster_topics":
                    assert run.id == cluster_run.id
                    continue
                assert run.topic_id == group
                payload = json.loads(run.input_json)
                if run.task_type == "analyze_comments":
                    assert {comment["comment_id"] for comment in payload} == {
                        f"{group}-comment-{index}" for index in range(10)
                    }
                else:
                    assert set(payload["note_ids"]) == {f"{group}-{index}" for index in range(3)}
            linked_run_ids.append({run.id for run in runs})
        assert linked_run_ids[0] & linked_run_ids[1] == {cluster_run.id}

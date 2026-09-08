from __future__ import annotations

import json
import math
from datetime import UTC, datetime, timedelta
from statistics import median
from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.db.models import (
    BrandProfile,
    Comment,
    LLMRun,
    Note,
    NoteSearchSnapshot,
    NoteSnapshot,
    Opportunity,
    RefreshJob,
    Topic,
    TopicSnapshot,
    TopicSnapshotNote,
)
from src.llm.service import LLMAnalysisUnavailableError, LLMService
from src.opportunities.gates import EligibilityContext, evaluate_eligibility
from src.opportunities.repository import OpportunityRepository
from src.opportunities.schemas import OpportunityAnalysisInput
from src.opportunities.service import OpportunityService
from src.scoring.confidence import classify_confidence
from src.scoring.heat import current_heat, weighted_engagement
from src.scoring.trend import position_momentum, trend_score
from src.topics.identity import SemanticAnswer, resolve_topic
from src.topics.lifecycle import Lifecycle, SnapshotSignal, classify_lifecycle
from src.topics.schemas import CandidateCluster, TopicCandidate


class OpportunityPipeline:
    """Build opportunities exclusively from persisted evidence belonging to this refresh."""

    def __init__(
        self, sessions: async_sessionmaker[AsyncSession], llm: LLMService | None = None
    ) -> None:
        self._sessions = sessions
        self._llm = llm
        self._service = OpportunityService(OpportunityRepository(sessions))

    async def build(self, job_id: str) -> list[Opportunity]:
        async with self._sessions() as session:
            job = await session.get(RefreshJob, job_id)
            if job is None:
                raise LookupError("Refresh job does not exist")
            existing = list(
                await session.scalars(select(Opportunity).where(Opportunity.job_id == job_id))
            )
            if existing:
                return existing
            evidence = list(
                await session.execute(
                    select(Note, NoteSnapshot)
                    .join(NoteSnapshot, NoteSnapshot.note_id == Note.note_id)
                    .where(NoteSnapshot.job_id == job_id)
                    .order_by(Note.note_id)
                )
            )
            brand = await session.scalar(
                select(BrandProfile).order_by(BrandProfile.version.desc()).limit(1)
            )
        if not evidence:
            return []
        if self._llm is None or brand is None:
            raise LLMAnalysisUnavailableError("AI configuration and brand profile are required")
        notes = {note.note_id: (note, snapshot) for note, snapshot in evidence}
        snapshots = await self._snapshots(job, notes)
        results: list[Opportunity] = []
        for snapshot in snapshots:
            async with self._sessions() as session:
                topic = await session.get(Topic, snapshot.topic_id)
                assert topic is not None
                assert snapshot.current_heat is not None and snapshot.lifecycle is not None
                note_ids = list(
                    await session.scalars(
                        select(TopicSnapshotNote.note_id).where(
                            TopicSnapshotNote.topic_snapshot_id == snapshot.id
                        )
                    )
                )
                comments = list(
                    await session.scalars(
                        select(Comment).where(
                            Comment.job_id == job_id, Comment.note_id.in_(note_ids)
                        )
                    )
                )
            context = {
                "job_id": job_id,
                "topic_id": snapshot.topic_id,
                "topic": topic.canonical_name,
                "brand_profile": json.loads(brand.profile_json),
                "note_ids": note_ids,
                "notes": [_note_payload(notes[n][0]) for n in note_ids],
                "comment_ids": [comment.comment_id for comment in comments],
                "comments": [{"comment_id": c.comment_id, "content": c.content} for c in comments],
                "current_heat": snapshot.current_heat,
                "trend_score": snapshot.trend_score,
                "lifecycle": snapshot.lifecycle,
            }
            brand_score = await self._llm.score_brand_relevance(**context)
            product_score = await self._llm.score_product_fit(**context)
            gap = await self._llm.analyze_content_gap(**context)
            gate = evaluate_eligibility(
                EligibilityContext(
                    risk=gap.risk,
                    lifecycle=snapshot.lifecycle or "Observing",
                    brand_relevance=brand_score.score,
                    product_fit=product_score.score,
                )
            )
            if gate.status == "filtered":
                continue
            audience_score = await self._llm.score_audience_relevance(**context)
            explanation = await self._llm.generate_opportunity_explanation(**context)
            preview = await self._llm.generate_copy_preview(**context, angle=gap.angle)
            async with self._sessions() as session:
                run_ids = list(
                    await session.scalars(
                        select(LLMRun.id).where(
                            LLMRun.job_id == job_id,
                            LLMRun.status == "completed",
                            (LLMRun.topic_id == snapshot.topic_id) | LLMRun.topic_id.is_(None),
                        )
                    )
                )
            reasons = {
                key: str(value)
                for key, value in explanation.model_dump().items()
                if not key.startswith("evidence_")
            }
            reasons.update(
                brand_relevance=brand_score.reason,
                audience_relevance=audience_score.reason,
                product_fit=product_score.reason,
                content_opportunity=gap.gap,
            )
            result = await self._service.analyze_topic(
                OpportunityAnalysisInput(
                    topic_id=snapshot.topic_id,
                    topic_snapshot_id=snapshot.id,
                    job_id=job_id,
                    brand_profile_version=brand.version,
                    title=topic.canonical_name,
                    risk=gap.risk,
                    confidence=snapshot.confidence,
                    lifecycle=snapshot.lifecycle,
                    current_heat=snapshot.current_heat,
                    trend_score=snapshot.trend_score,
                    brand_relevance=brand_score.score,
                    audience_relevance=audience_score.score,
                    product_fit=product_score.score,
                    content_opportunity=gap.score,
                    reasons=reasons,
                    recommended_angle=gap.angle,
                    product_connection=explanation.product_connection,
                    copy_preview=preview.model_dump(),
                    llm_run_ids=run_ids,
                )
            )
            async with self._sessions() as session:
                opportunity = await session.get(Opportunity, result.id)
                assert opportunity is not None
                results.append(opportunity)
        return results

    async def _snapshots(
        self, job: RefreshJob, notes: dict[str, tuple[Note, NoteSnapshot]]
    ) -> list[TopicSnapshot]:
        async with self._sessions() as session:
            existing = list(
                await session.scalars(select(TopicSnapshot).where(TopicSnapshot.job_id == job.id))
            )
            if existing:
                return existing
            topics = list(
                await session.scalars(
                    select(Topic).where(Topic.last_seen_at >= job.updated_at - timedelta(days=14))
                )
            )
            candidates = []
            for recent_topic in topics:
                ids = set(
                    await session.scalars(
                        select(TopicSnapshotNote.note_id)
                        .join(
                            TopicSnapshot, TopicSnapshot.id == TopicSnapshotNote.topic_snapshot_id
                        )
                        .where(TopicSnapshot.topic_id == recent_topic.topic_id)
                    )
                )
                candidates.append(
                    TopicCandidate(
                        recent_topic.topic_id,
                        recent_topic.canonical_name,
                        recent_topic.summary or "",
                        ids,
                        _utc(recent_topic.last_seen_at),
                    )
                )
        assert self._llm is not None
        clusters = await self._llm.cluster_topics(
            job_id=job.id, notes=[_note_payload(n) for n, _ in notes.values()]
        )
        pending = []
        used_topics: set[str] = set()
        for cluster in clusters.clusters:
            ids = set(cluster.note_ids)
            if not ids or not ids <= notes.keys():
                raise LLMAnalysisUnavailableError("Cluster requires collected note evidence")
            candidate = CandidateCluster(
                ids, cluster.name, cluster.keywords, [notes[n][0].title or "" for n in sorted(ids)]
            )
            resolution = await resolve_topic(
                candidate, candidates, _IdentityResolver(self._llm, job.id), _utc(job.updated_at)
            )
            if resolution.topic_id in used_topics:
                raise LLMAnalysisUnavailableError("Duplicate topic clusters")
            used_topics.add(resolution.topic_id)
            async with self._sessions() as session:
                history = list(
                    await session.scalars(
                        select(TopicSnapshot)
                        .where(TopicSnapshot.topic_id == resolution.topic_id)
                        .order_by(TopicSnapshot.captured_at.desc())
                    )
                )
                comments = list(
                    await session.scalars(
                        select(Comment).where(Comment.job_id == job.id, Comment.note_id.in_(ids))
                    )
                )
                positions = list(
                    await session.execute(
                        select(
                            NoteSearchSnapshot.note_id,
                            NoteSearchSnapshot.keyword,
                            NoteSearchSnapshot.search_position,
                        ).where(
                            NoteSearchSnapshot.job_id == job.id, NoteSearchSnapshot.note_id.in_(ids)
                        )
                    )
                )
            selected = [notes[n] for n in sorted(ids)]
            now = max(_utc(snapshot.captured_at) for _, snapshot in selected)
            engagements = [
                weighted_engagement(s.likes or 0, s.collects or 0, s.comments or 0)
                for _, s in selected
                if any(v is not None for v in (s.likes, s.collects, s.comments))
            ]
            ages = [
                max(0, (now - _utc(n.published_at)).total_seconds() / 3600)
                for n, _ in selected
                if n.published_at is not None
            ]
            authors = {n.author_id for n, _ in selected if n.author_id}
            raw = {
                "engagement": median([math.log1p(e) for e in engagements]) if engagements else None,
                "freshness": median([math.exp(-age / 72) for age in ages]) if ages else None,
                "volume": float(len(ids)),
                "creator_spread": len(authors) / len(ids),
                "comment_demand": None,
            }
            if len(comments) >= 10:
                analysis = await self._llm.analyze_comments(
                    job_id=job.id,
                    topic_id=None,
                    comments=[{"comment_id": c.comment_id, "content": c.content} for c in comments],
                )
                demand = set(
                    analysis.categories.question
                    + analysis.categories.pain_point
                    + analysis.categories.request
                    + analysis.categories.purchase_intent
                )
                raw["comment_demand"] = len(demand) / len(comments)
            metrics: dict[str, Any] = {
                **raw,
                "engagement_total": sum(engagements),
                "note_ids": sorted(ids),
                "author_ids": sorted(authors),
                "positions": [list(p) for p in positions],
            }
            pending.append(
                (resolution, cluster, ids, history, selected, now, comments, raw, metrics)
            )
        saved = []
        for resolution, cluster, ids, history, selected, now, comments, raw, metrics in pending:
            normalized = {
                key: _percentile(value, [p[7][key] for p in pending]) for key, value in raw.items()
            }
            heat = current_heat(normalized)
            trend = _trend(metrics, json.loads(history[0].raw_metrics_json)) if history else None
            lifecycle = classify_lifecycle(
                [
                    SnapshotSignal(
                        _utc(h.captured_at),
                        h.current_heat or 0,
                        h.trend_score,
                        h.note_count,
                        True,
                        cast(Lifecycle, h.lifecycle),
                    )
                    for h in history
                ],
                SnapshotSignal(now, heat, trend, len(ids), not bool(job.error_summary)),
            )
            confidence = classify_confidence(
                len(history) + 1,
                len(ids),
                len(metrics["author_ids"]),
                sum(s.data_completeness for _, s in selected) / len(ids),
                len(comments),
                analysis_independent_of_comments=False,
                partial_success=bool(job.error_summary),
            )
            async with self._sessions() as session:
                topic = await session.get(Topic, resolution.topic_id)
                if topic is None:
                    topic = Topic(
                        topic_id=resolution.topic_id,
                        canonical_name=cluster.name,
                        first_seen_at=now,
                        last_seen_at=now,
                        status=lifecycle,
                    )
                    session.add(topic)
                topic.last_seen_at, topic.status = now, lifecycle
                await session.flush()
                snapshot = TopicSnapshot(
                    topic_id=topic.topic_id,
                    job_id=job.id,
                    captured_at=now,
                    note_count=len(ids),
                    unique_author_count=len(metrics["author_ids"]),
                    comment_sample_count=len(comments),
                    raw_metrics_json=json.dumps(metrics),
                    normalized_metrics_json=json.dumps(normalized),
                    current_heat=heat,
                    trend_score=trend,
                    lifecycle=lifecycle,
                    confidence=confidence,
                )
                session.add(snapshot)
                await session.flush()
                session.add_all(
                    [
                        TopicSnapshotNote(
                            topic_snapshot_id=snapshot.id,
                            note_id=n,
                            is_representative=bool(notes[n][0].body),
                        )
                        for n in sorted(ids)
                    ]
                )
                await session.commit()
                saved.append(snapshot)
        return saved


class _IdentityResolver:
    def __init__(self, llm: LLMService, job_id: str) -> None:
        self._llm, self._job_id = llm, job_id

    async def resolve(
        self, candidate: CandidateCluster, topics: list[TopicCandidate]
    ) -> SemanticAnswer:
        if not topics:
            return {
                "action": "CREATE_NEW",
                "topic_id": None,
                "confidence": 1,
                "reason": "first_topic",
            }
        answer = await self._llm.resolve_topic_identity(
            job_id=self._job_id,
            topic_id=None,
            context={
                "candidate": candidate.summary,
                "note_ids": sorted(candidate.note_ids),
                "topics": [{"topic_id": t.topic_id, "name": t.canonical_name} for t in topics],
            },
        )
        return {
            "action": "MATCH_EXISTING" if answer.canonical_topic_id else "CREATE_NEW",
            "topic_id": answer.canonical_topic_id,
            "confidence": answer.confidence,
            "reason": "semantic_resolution",
        }


def _note_payload(note: Note) -> dict[str, object]:
    # Explicit allowlist: never send the raw crawler payload or credentials to the model.
    return {
        "note_id": note.note_id,
        "title": note.title,
        "body": note.body,
        "url": note.url,
        "published_at": note.published_at.isoformat() if note.published_at else None,
    }


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _percentile(value: float | None, population: list[float | None]) -> float | None:
    if value is None:
        return None
    valid = [v for v in population if v is not None]
    return 100 * (sum(v < value for v in valid) + 0.5 * sum(v == value for v in valid)) / len(valid)


def _trend(current: dict[str, Any], previous: dict[str, Any]) -> float:
    previous_notes = set(previous.get("note_ids", []))
    previous_authors = set(previous.get("author_ids", []))
    positions = {(n, k): p for n, k, p in previous.get("positions", [])}
    momentum = [
        position_momentum(positions[n, k], p)
        for n, k, p in current["positions"]
        if (n, k) in positions
    ]
    engagement = (current["engagement_total"] - previous.get("engagement_total", 0)) / max(
        previous.get("engagement_total", 0), 1
    )
    return trend_score(
        min(
            100, 100 * len(set(current["note_ids"]) - previous_notes) / max(len(previous_notes), 1)
        ),
        min(100, max(0, engagement * 100)),
        min(100, max(0, 100 * sum(momentum) / len(momentum))) if momentum else 0,
        100 * len(set(current["note_ids"]) & previous_notes) / max(len(previous_notes), 1),
        min(
            100,
            100
            * len(set(current["author_ids"]) - previous_authors)
            / max(len(previous_authors), 1),
        ),
    )

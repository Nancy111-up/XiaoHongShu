from __future__ import annotations

import json

from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.db.models import Note, Opportunity, RefreshJob, TopicSnapshot, TopicSnapshotNote


def build_router(sessions: async_sessionmaker[AsyncSession]) -> APIRouter:
    router = APIRouter(tags=["opportunities"])

    @router.get("/opportunities")
    async def list_opportunities() -> dict[str, object]:
        async with sessions() as session:
            rows = list(
                await session.execute(
                    select(Opportunity, TopicSnapshot, RefreshJob)
                    .join(TopicSnapshot, TopicSnapshot.id == Opportunity.topic_snapshot_id)
                    .join(RefreshJob, RefreshJob.id == Opportunity.job_id)
                    .order_by(Opportunity.updated_at.desc())
                )
            )
            if not rows:
                return {"items": [], "data_source": "unavailable"}
            items = []
            response_source = "partial" if rows[0][2].status == "partial_success" else "live"
            for opportunity, snapshot, source_job in rows:
                urls = list(
                    await session.scalars(
                        select(Note.url)
                        .join(TopicSnapshotNote, TopicSnapshotNote.note_id == Note.note_id)
                        .where(
                            TopicSnapshotNote.topic_snapshot_id == snapshot.id,
                            Note.url.is_not(None),
                        )
                    )
                )
                items.append(
                    {
                        "id": opportunity.id,
                        "topicId": opportunity.topic_id,
                        "title": opportunity.title,
                        "currentHeat": snapshot.current_heat,
                        "trendScore": snapshot.trend_score,
                        "trendStage": snapshot.lifecycle,
                        "score": opportunity.score,
                        "decision": opportunity.decision,
                        "goal": opportunity.goal,
                        "eligibility": opportunity.eligibility,
                        "risk": opportunity.risk,
                        "confidence": opportunity.confidence,
                        "scores": json.loads(opportunity.score_breakdown_json),
                        "reasons": json.loads(opportunity.reasons_json),
                        "sources": [{"url": url} for url in urls],
                        "preview": (
                            json.loads(opportunity.copy_preview_json)
                            if opportunity.copy_preview_json
                            else None
                        ),
                        "updatedAt": opportunity.updated_at.isoformat(),
                        "data_source": (
                            "partial" if source_job.status == "partial_success" else "live"
                        ),
                    }
                )
            return {"items": items, "data_source": response_source}

    return router

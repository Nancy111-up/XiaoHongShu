from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


def _uuid() -> str:
    return str(uuid4())


def _utcnow() -> datetime:
    return datetime.now(UTC)


ACTIVE_REFRESH_STATUSES = frozenset(
    {
        "queued",
        "collecting_search",
        "collecting_detail",
        "normalizing",
        "clustering",
        "enriching",
        "scoring_trend",
        "scoring_opportunity",
        "generating_preview",
    }
)


def _active_refresh_slot(context) -> str | None:  # type: ignore[no-untyped-def]
    status = context.get_current_parameters()["status"]
    return "active" if status in ACTIVE_REFRESH_STATUSES else None


class RefreshJob(Base):
    __tablename__ = "refresh_jobs"
    __table_args__ = (Index("uq_refresh_jobs_single_active", "active_slot", unique=True),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    mode: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32), index=True)
    active_slot: Mapped[str | None] = mapped_column(String(16), default=_active_refresh_slot)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, index=True
    )
    successful_keywords: Mapped[str | None] = mapped_column(Text)
    failed_keywords: Mapped[str | None] = mapped_column(Text)
    error_code: Mapped[str | None] = mapped_column(String(64))
    error_summary: Mapped[str | None] = mapped_column(Text)


class Note(Base):
    __tablename__ = "notes"

    note_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str | None] = mapped_column(Text)
    body: Mapped[str | None] = mapped_column(Text)
    author_id: Mapped[str | None] = mapped_column(String(128))
    author_name: Mapped[str | None] = mapped_column(String(256))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    url: Mapped[str | None] = mapped_column(Text)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    raw_payload_json: Mapped[str] = mapped_column(Text)


class NoteSnapshot(Base):
    __tablename__ = "note_snapshots"
    __table_args__ = (UniqueConstraint("job_id", "note_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    job_id: Mapped[str] = mapped_column(ForeignKey("refresh_jobs.id"))
    note_id: Mapped[str] = mapped_column(ForeignKey("notes.note_id"))
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    likes: Mapped[int | None] = mapped_column(Integer)
    collects: Mapped[int | None] = mapped_column(Integer)
    comments: Mapped[int | None] = mapped_column(Integer)
    shares: Mapped[int | None] = mapped_column(Integer)
    data_completeness: Mapped[float] = mapped_column(Float)


class NoteSearchSnapshot(Base):
    __tablename__ = "note_search_snapshots"
    __table_args__ = (UniqueConstraint("job_id", "note_id", "keyword"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    job_id: Mapped[str] = mapped_column(ForeignKey("refresh_jobs.id"))
    note_id: Mapped[str] = mapped_column(ForeignKey("notes.note_id"))
    keyword: Mapped[str] = mapped_column(String(256))
    search_position: Mapped[int] = mapped_column(Integer)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Topic(Base):
    __tablename__ = "topics"

    topic_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    canonical_name: Mapped[str] = mapped_column(String(256))
    summary: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[str] = mapped_column(String(32))


class TopicSnapshot(Base):
    __tablename__ = "topic_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    topic_id: Mapped[str] = mapped_column(ForeignKey("topics.topic_id"))
    job_id: Mapped[str] = mapped_column(ForeignKey("refresh_jobs.id"))
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    note_count: Mapped[int] = mapped_column(Integer)
    unique_author_count: Mapped[int] = mapped_column(Integer)
    comment_sample_count: Mapped[int] = mapped_column(Integer)
    raw_metrics_json: Mapped[str] = mapped_column(Text)
    normalized_metrics_json: Mapped[str] = mapped_column(Text)
    current_heat: Mapped[float | None] = mapped_column(Float)
    trend_score: Mapped[float | None] = mapped_column(Float)
    lifecycle: Mapped[str | None] = mapped_column(String(32))
    confidence: Mapped[str] = mapped_column(String(32))


class TopicSnapshotNote(Base):
    __tablename__ = "topic_snapshot_notes"
    __table_args__ = (UniqueConstraint("topic_snapshot_id", "note_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    topic_snapshot_id: Mapped[str] = mapped_column(ForeignKey("topic_snapshots.id"))
    note_id: Mapped[str] = mapped_column(ForeignKey("notes.note_id"))
    relevance: Mapped[float | None] = mapped_column(Float)
    is_representative: Mapped[bool] = mapped_column(Boolean, default=False)


class Comment(Base):
    __tablename__ = "comments"
    __table_args__ = (UniqueConstraint("job_id", "comment_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    comment_id: Mapped[str] = mapped_column(String(64))
    note_id: Mapped[str] = mapped_column(ForeignKey("notes.note_id"))
    job_id: Mapped[str] = mapped_column(ForeignKey("refresh_jobs.id"))
    content: Mapped[str | None] = mapped_column(Text)
    likes: Mapped[int | None] = mapped_column(Integer)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class LLMRun(Base):
    __tablename__ = "llm_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    task_type: Mapped[str] = mapped_column(String(64))
    job_id: Mapped[str | None] = mapped_column(ForeignKey("refresh_jobs.id"))
    topic_id: Mapped[str | None] = mapped_column(ForeignKey("topics.topic_id"))
    model: Mapped[str] = mapped_column(String(128))
    prompt_version: Mapped[str] = mapped_column(String(64))
    schema_version: Mapped[str] = mapped_column(String(64))
    temperature: Mapped[float] = mapped_column(Float)
    input_hash: Mapped[str] = mapped_column(String(128))
    input_json: Mapped[str] = mapped_column(Text)
    raw_response: Mapped[str | None] = mapped_column(Text)
    parsed_response: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32))
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class BrandProfile(Base):
    __tablename__ = "brand_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    version: Mapped[int] = mapped_column(Integer, unique=True)
    profile_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class Opportunity(Base):
    __tablename__ = "opportunities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    topic_id: Mapped[str] = mapped_column(ForeignKey("topics.topic_id"))
    topic_snapshot_id: Mapped[str] = mapped_column(ForeignKey("topic_snapshots.id"))
    job_id: Mapped[str] = mapped_column(ForeignKey("refresh_jobs.id"))
    brand_profile_version: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(256))
    score: Mapped[float | None] = mapped_column(Float)
    decision: Mapped[str] = mapped_column(String(64))
    eligibility: Mapped[str] = mapped_column(String(32))
    risk: Mapped[str] = mapped_column(String(32))
    confidence: Mapped[str] = mapped_column(String(32))
    goal: Mapped[str | None] = mapped_column(String(128))
    score_breakdown_json: Mapped[str] = mapped_column(Text)
    reasons_json: Mapped[str] = mapped_column(Text)
    recommended_angle: Mapped[str | None] = mapped_column(Text)
    product_connection: Mapped[str | None] = mapped_column(Text)
    copy_preview_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, index=True
    )


class OpportunityLLMRun(Base):
    __tablename__ = "opportunity_llm_runs"
    __table_args__ = (UniqueConstraint("opportunity_id", "llm_run_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    opportunity_id: Mapped[str] = mapped_column(ForeignKey("opportunities.id"))
    llm_run_id: Mapped[str] = mapped_column(ForeignKey("llm_runs.id"))


class Draft(Base):
    __tablename__ = "drafts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    source_opportunity_id: Mapped[str] = mapped_column(ForeignKey("opportunities.id"))
    topic_id: Mapped[str] = mapped_column(ForeignKey("topics.topic_id"))
    brand_profile_version: Mapped[int] = mapped_column(Integer)
    prompt_version: Mapped[str] = mapped_column(String(64))
    titles_json: Mapped[str] = mapped_column(Text)
    body: Mapped[str] = mapped_column(Text)
    tags_json: Mapped[str] = mapped_column(Text)
    cta: Mapped[str | None] = mapped_column(Text)
    cover_text: Mapped[str | None] = mapped_column(Text)
    image_plan_json: Mapped[str] = mapped_column(Text)
    product_connection: Mapped[str | None] = mapped_column(Text)
    risk_check_json: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class RejectFeedback(Base):
    __tablename__ = "reject_feedback"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    opportunity_id: Mapped[str] = mapped_column(ForeignKey("opportunities.id"))
    reason: Mapped[str] = mapped_column(String(64))
    detail: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class CalendarItem(Base):
    __tablename__ = "calendar_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    draft_id: Mapped[str] = mapped_column(ForeignKey("drafts.id"), unique=True)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[str] = mapped_column(String(32))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class SystemSetting(Base):
    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value_json: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

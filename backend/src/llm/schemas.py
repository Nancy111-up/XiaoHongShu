from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TopicCluster(StrictModel):
    name: str
    note_ids: list[str]
    keywords: list[str] = Field(default_factory=list)


class TopicClusters(StrictModel):
    clusters: list[TopicCluster]


class TopicResolution(StrictModel):
    canonical_topic_id: str | None
    canonical_name: str
    aliases: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)


class CommentCategories(StrictModel):
    question: list[str]
    pain_point: list[str]
    request: list[str]
    purchase_intent: list[str]
    experience: list[str]
    other: list[str]


class CommentAnalysis(StrictModel):
    analyzed_comment_count: int = Field(ge=0)
    categories: CommentCategories


class ScoredEvidence(StrictModel):
    score: float = Field(ge=0, le=100)
    reason: str
    evidence_note_ids: list[str] = Field(default_factory=list)
    evidence_comment_ids: list[str] = Field(default_factory=list)


class ContentGap(StrictModel):
    gap: str
    angle: str
    evidence_note_ids: list[str] = Field(default_factory=list)
    evidence_comment_ids: list[str] = Field(default_factory=list)


class OpportunityExplanation(StrictModel):
    audience_need: str
    content_gap: str
    why_now: str
    why_brand: str
    why_audience: str
    why_this_angle: str
    product_connection: str
    evidence_note_ids: list[str] = Field(default_factory=list)
    evidence_comment_ids: list[str] = Field(default_factory=list)


class CopyPreview(StrictModel):
    title: str
    hook: str
    outline: list[str]
    call_to_action: str
    evidence_note_ids: list[str] = Field(default_factory=list)
    evidence_comment_ids: list[str] = Field(default_factory=list)


class FullCopy(StrictModel):
    title: str
    body: str
    hashtags: list[str] = Field(default_factory=list)
    evidence_note_ids: list[str] = Field(default_factory=list)
    evidence_comment_ids: list[str] = Field(default_factory=list)

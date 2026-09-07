from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class OpportunityAnalysisInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    topic_id: str
    topic_snapshot_id: str
    job_id: str
    brand_profile_version: int = Field(ge=1)
    title: str
    risk: str
    confidence: str
    lifecycle: str
    current_heat: float = Field(ge=0, le=100)
    trend_score: float | None = Field(default=None, ge=0, le=100)
    brand_relevance: float | None = Field(default=None, ge=0, le=100)
    audience_relevance: float | None = Field(default=None, ge=0, le=100)
    content_opportunity: float | None = Field(default=None, ge=0, le=100)
    product_fit: float | None = Field(default=None, ge=0, le=100)
    recent_duplicate: bool = False
    reasons: dict[str, str] = Field(default_factory=dict)
    recommended_angle: str | None = None
    product_connection: str | None = None
    copy_preview: dict[str, object] | None = None
    llm_run_ids: list[str] = Field(default_factory=list)


class OpportunityResult(BaseModel):
    id: str
    score: float | None
    decision: str
    eligibility: str
    goals: list[str]

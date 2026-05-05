"""Agent API schemas — 对齐 IMPLEMENTATION_PLAN §2.3 + §3"""

from __future__ import annotations

from pydantic import BaseModel, Field

from src.schemas.common import TopicCardSchema, VisualGuidanceSchema


class DiscoverRequest(BaseModel):
    keyword: str | None = None


class StartRequest(BaseModel):
    topic: str
    source: str = "manual"  # "manual" | "inspiration_pool"


class AgentStatusResponse(BaseModel):
    thread_id: str
    status: str  # "in_progress" | "waiting_for_human" | "done" | "cancelled"
    current_step: str
    draft_copy: str | None = None
    visual_guidance: VisualGuidanceSchema | None = None
    error_logs: list[str] = Field(default_factory=list)


class FeedbackRequest(BaseModel):
    thread_id: str
    action: str  # "approve" | "revise"
    feedback: str = ""
    edited_content: str = ""

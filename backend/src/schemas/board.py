"""Kanban board schemas — 对齐 IMPLEMENTATION_PLAN §2.3 + §3"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from src.schemas.common import TopicCardSchema, VisualGuidanceSchema


class TaskCardSchema(BaseModel):
    thread_id: str
    user_input: str
    status: str  # "in_progress" | "waiting_for_human" | "done" | "cancelled"
    column: str  # "inspiration" | "in_progress" | "pending_review" | "done"
    revision_count: int = 0
    draft_copy: str | None = None
    final_copy: str | None = None
    visual_guidance: VisualGuidanceSchema | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class KanbanBoardResponse(BaseModel):
    inspiration: list[TopicCardSchema] = Field(default_factory=list)
    in_progress: list[TaskCardSchema] = Field(default_factory=list)
    pending_review: list[TaskCardSchema] = Field(default_factory=list)
    done: list[TaskCardSchema] = Field(default_factory=list)

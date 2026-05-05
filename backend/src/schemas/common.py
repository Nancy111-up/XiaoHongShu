"""Unified API response envelope — 对齐 IMPLEMENTATION_PLAN §2.3 + patterns.md"""

from __future__ import annotations

from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationMeta(BaseModel):
    total: int
    page: int = 1
    limit: int = 50


class APIResponse(BaseModel, Generic[T]):
    success: bool
    data: T | None = None
    error: str | None = None
    meta: dict | None = None

    @classmethod
    def ok(cls, data: T, meta: dict | None = None) -> APIResponse[T]:
        return cls(success=True, data=data, meta=meta)

    @classmethod
    def fail(cls, error: str, data: T | None = None) -> APIResponse[T]:
        return cls(success=False, error=error, data=data)


class VisualGuidanceSchema(BaseModel):
    cover_suggestion: str = ""
    shot_descriptions: list[str] = Field(default_factory=list)
    domestic_image_prompts: list[str] = Field(default_factory=list)


class TopicCardSchema(BaseModel):
    card_id: str
    title: str
    reason: str
    heat_index: int = Field(ge=0, le=100)
    estimated_traffic: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

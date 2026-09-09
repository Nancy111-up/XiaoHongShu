from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CopyPreview(BaseModel):
    model_config = ConfigDict(extra="forbid")
    titles: list[str] = Field(min_length=3, max_length=3)
    angle: str
    body: str = Field(min_length=80, max_length=150)
    format: str
    tags: list[str]
    cover_direction: str
    product_connection: str
    cost: Literal["low", "medium", "high"]
    cta: str | None = None


class FullDraftContent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    titles: list[str] = Field(min_length=3, max_length=3)
    body: str
    tags: list[str]
    cta: str | None = None
    cover_text: str | None = None
    image_count: int = Field(ge=0)
    image_advice: list[str]
    product_connection: str | None = None
    risk_check: dict[str, object]
    prompt_version: str

    @model_validator(mode="after")
    def image_plan_matches_count(self) -> FullDraftContent:
        if len(self.image_advice) != self.image_count:
            raise ValueError("image advice count must match image_count")
        return self


class RejectInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: Literal[
        "brand_irrelevant",
        "product_fit_poor",
        "trend_expired",
        "tone_mismatch",
        "already_covered",
        "placement_forced",
        "risk_too_high",
        "other",
    ]
    detail: str | None = None

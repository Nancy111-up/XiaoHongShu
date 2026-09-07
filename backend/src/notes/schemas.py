from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class NormalizedNote:
    note_id: str
    title: str | None
    body: str | None
    author_id: str | None
    author_name: str | None
    published_at: datetime | None
    captured_at: datetime
    likes: int | None
    collects: int | None
    comments: int | None
    shares: int | None
    url: str | None
    raw_payload: dict[str, object]
    data_completeness: float
    keyword: str | None = None
    search_position: int | None = None


@dataclass(frozen=True, slots=True)
class NormalizedComment:
    comment_id: str
    note_id: str
    job_id: str
    content: str | None
    likes: int | None
    captured_at: datetime | None
    parent_comment_id: str | None
    raw_payload: dict[str, object]

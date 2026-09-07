from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class CandidateNote:
    note_id: str
    author_id: str
    relevance: float
    engagement: int
    published_at: datetime
    has_readable_detail: bool


def choose_representatives(notes: list[CandidateNote], limit: int = 3) -> list[CandidateNote]:
    selected: list[CandidateNote] = []
    seen_authors: set[str] = set()
    eligible = [note for note in notes if note.has_readable_detail]
    ranked = sorted(
        eligible,
        key=lambda note: (note.relevance, note.engagement, note.published_at),
        reverse=True,
    )
    while ranked and len(selected) < min(limit, 5):
        diverse = next((note for note in ranked if note.author_id not in seen_authors), ranked[0])
        selected.append(diverse)
        seen_authors.add(diverse.author_id)
        ranked.remove(diverse)
    return selected

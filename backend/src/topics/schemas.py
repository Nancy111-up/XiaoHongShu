from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal


@dataclass(frozen=True, slots=True)
class CandidateCluster:
    note_ids: set[str]
    summary: str
    keywords: list[str]
    sample_titles: list[str]


@dataclass(frozen=True, slots=True)
class TopicCandidate:
    topic_id: str
    canonical_name: str
    summary: str
    note_ids: set[str]
    last_seen_at: datetime


@dataclass(frozen=True, slots=True)
class TopicResolution:
    action: Literal["MATCH_EXISTING", "CREATE_NEW"]
    topic_id: str
    reason: str

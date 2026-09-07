from __future__ import annotations

from datetime import datetime, timedelta
from typing import Protocol, TypedDict
from uuid import uuid4

from src.topics.schemas import CandidateCluster, TopicCandidate, TopicResolution


class SemanticAnswer(TypedDict):
    action: str
    topic_id: str | None
    confidence: float
    reason: str


class TopicSemanticResolver(Protocol):
    async def resolve(
        self, candidate: CandidateCluster, topics: list[TopicCandidate]
    ) -> SemanticAnswer: ...


async def resolve_topic(
    candidate: CandidateCluster,
    topics: list[TopicCandidate],
    resolver: TopicSemanticResolver,
    now: datetime,
) -> TopicResolution:
    recent_topics = [topic for topic in topics if topic.last_seen_at >= now - timedelta(days=14)]
    matches = [topic for topic in recent_topics if len(candidate.note_ids & topic.note_ids) >= 2]
    if matches:
        selected = max(matches, key=lambda topic: _jaccard(candidate.note_ids, topic.note_ids))
        return TopicResolution("MATCH_EXISTING", selected.topic_id, "note_overlap")
    answer = await resolver.resolve(candidate, recent_topics)
    if (
        answer["action"] == "MATCH_EXISTING"
        and answer["topic_id"] is not None
        and answer["confidence"] >= 0.80
        and any(topic.topic_id == answer["topic_id"] for topic in recent_topics)
    ):
        return TopicResolution("MATCH_EXISTING", answer["topic_id"], answer["reason"])
    return TopicResolution("CREATE_NEW", str(uuid4()), answer["reason"])


def _jaccard(left: set[str], right: set[str]) -> float:
    return len(left & right) / len(left | right)

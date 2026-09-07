from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from src.topics.identity import resolve_topic
from src.topics.schemas import CandidateCluster, TopicCandidate


class NoSemanticMatch:
    async def resolve(self, candidate, topics):
        return {"action": "CREATE_NEW", "topic_id": None, "confidence": 1.0, "reason": "fixture"}


@pytest.mark.asyncio
async def test_overlap_below_two_uses_semantic_resolution() -> None:
    now = datetime(2026, 9, 7, tzinfo=UTC)
    cluster = CandidateCluster(
        note_ids={"a", "b"}, summary="candidate", keywords=[], sample_titles=[]
    )
    topics = [TopicCandidate("topic-1", "旧名", "summary", {"a", "x"}, now)]

    resolution = await resolve_topic(cluster, topics, NoSemanticMatch(), now)

    assert resolution.action == "CREATE_NEW"
    assert resolution.topic_id != "topic-1"


@pytest.mark.asyncio
async def test_overlap_chooses_highest_jaccard_and_keeps_existing_id() -> None:
    now = datetime(2026, 9, 7, tzinfo=UTC)
    cluster = CandidateCluster(
        note_ids={"a", "b", "c", "d"}, summary="candidate", keywords=[], sample_titles=[]
    )
    topics = [
        TopicCandidate("topic-low", "旧名", "summary", {"a", "b", "x", "y"}, now),
        TopicCandidate("topic-high", "新名", "summary", {"a", "b", "c"}, now),
    ]

    resolution = await resolve_topic(cluster, topics, NoSemanticMatch(), now)

    assert resolution.action == "MATCH_EXISTING"
    assert resolution.topic_id == "topic-high"


@pytest.mark.asyncio
async def test_topics_older_than_fourteen_days_do_not_participate() -> None:
    now = datetime(2026, 9, 7, tzinfo=UTC)
    cluster = CandidateCluster(
        note_ids={"a", "b"}, summary="candidate", keywords=[], sample_titles=[]
    )
    topics = [
        TopicCandidate(
            "expired-topic", "旧话题", "summary", {"a", "b"}, now - timedelta(days=15)
        )
    ]

    resolution = await resolve_topic(cluster, topics, NoSemanticMatch(), now)

    assert resolution.action == "CREATE_NEW"

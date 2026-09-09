import asyncio
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from src.app import create_app
from src.db.base import Base
from src.db.models import Opportunity, RefreshJob, Topic, TopicSnapshot
from src.db.session import create_session_factory


def test_opportunity_response_matches_frontend_contract(tmp_path) -> None:
    factory = create_session_factory(f"sqlite+aiosqlite:///{(tmp_path / 'api.db').as_posix()}")
    now = datetime.now(UTC)

    async def seed() -> None:
        async with factory() as session:
            async with session.bind.begin() as connection:  # type: ignore[union-attr]
                await connection.run_sync(Base.metadata.create_all)
            session.add_all(
                [
                    RefreshJob(id="job", mode="manual", status="completed", started_at=now),
                    Topic(
                        topic_id="topic",
                        canonical_name="城市夜跑",
                        first_seen_at=now,
                        last_seen_at=now,
                        status="Growing",
                    ),
                    TopicSnapshot(
                        id="snap",
                        topic_id="topic",
                        job_id="job",
                        captured_at=now,
                        note_count=5,
                        unique_author_count=4,
                        comment_sample_count=12,
                        raw_metrics_json="{}",
                        normalized_metrics_json="{}",
                        current_heat=82,
                        trend_score=76,
                        lifecycle="Growing",
                        confidence="High",
                    ),
                    Opportunity(
                        id="opp",
                        topic_id="topic",
                        topic_snapshot_id="snap",
                        job_id="job",
                        brand_profile_version=1,
                        title="城市夜跑",
                        score=81,
                        decision="High Opportunity",
                        eligibility="eligible",
                        risk="low",
                        confidence="High",
                        goal="品牌 + 产品",
                        score_breakdown_json='{"brand_relevance":85,"audience_relevance":80,'
                        '"trend_timing":75,"content_opportunity":78,"product_fit":72}',
                        reasons_json='{"why_now":"增长中"}',
                        copy_preview_json=None,
                        updated_at=now,
                    ),
                ]
            )
            await session.commit()

    asyncio.run(seed())

    response = TestClient(create_app(factory)).get("/api/opportunities")
    assert response.status_code == 200
    item = response.json()["items"][0]
    assert set(item) >= {
        "id",
        "topicId",
        "currentHeat",
        "trendScore",
        "trendStage",
        "score",
        "decision",
        "goal",
        "eligibility",
        "risk",
        "confidence",
        "scores",
        "reasons",
        "sources",
        "preview",
        "updatedAt",
        "data_source",
    }
    assert item["topicId"] == "topic" and item["data_source"] == "live"


def test_populated_response_marks_partial_refresh_data(tmp_path) -> None:
    factory = create_session_factory(f"sqlite+aiosqlite:///{(tmp_path / 'partial.db').as_posix()}")
    now = datetime.now(UTC)

    async def seed() -> None:
        async with factory() as session:
            async with session.bind.begin() as connection:  # type: ignore[union-attr]
                await connection.run_sync(Base.metadata.create_all)
            session.add_all(
                [
                    RefreshJob(
                        id="job",
                        mode="manual",
                        status="partial_success",
                        started_at=now,
                        updated_at=now,
                    ),
                    Topic(
                        topic_id="topic",
                        canonical_name="城市夜跑",
                        first_seen_at=now,
                        last_seen_at=now,
                        status="Growing",
                    ),
                    TopicSnapshot(
                        id="snap",
                        topic_id="topic",
                        job_id="job",
                        captured_at=now,
                        note_count=1,
                        unique_author_count=1,
                        comment_sample_count=0,
                        raw_metrics_json="{}",
                        normalized_metrics_json="{}",
                        current_heat=70,
                        lifecycle="Growing",
                        confidence="Medium",
                    ),
                    Opportunity(
                        id="opp",
                        topic_id="topic",
                        topic_snapshot_id="snap",
                        job_id="job",
                        brand_profile_version=1,
                        title="城市夜跑",
                        score=70,
                        decision="Recommend",
                        eligibility="eligible",
                        risk="low",
                        confidence="Medium",
                        score_breakdown_json="{}",
                        reasons_json="{}",
                        updated_at=now,
                    ),
                ]
            )
            await session.commit()

    asyncio.run(seed())
    response = TestClient(create_app(factory)).get("/api/opportunities")
    assert response.json()["data_source"] == "partial"
    assert response.json()["items"][0]["data_source"] == "partial"

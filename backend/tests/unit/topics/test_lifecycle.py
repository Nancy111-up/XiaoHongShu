from datetime import UTC, datetime, timedelta

from src.topics.lifecycle import SnapshotSignal, classify_lifecycle


def test_lifecycle_observes_topics_without_history() -> None:
    current = SnapshotSignal(datetime(2026, 9, 7, tzinfo=UTC), 90, 90, 3, True)
    assert classify_lifecycle([], current) == "Observing"


def test_lifecycle_prioritizes_expired_after_three_missing_successful_refreshes() -> None:
    current = SnapshotSignal(datetime(2026, 9, 7, tzinfo=UTC), 0, None, 0, True)
    history = [
        SnapshotSignal(current.captured_at - timedelta(days=days), 0, None, 0, True)
        for days in (1, 2, 3)
    ]
    assert classify_lifecycle(history, current) == "Expired"


def test_lifecycle_growing_requires_two_high_trend_scores() -> None:
    current = SnapshotSignal(datetime(2026, 9, 7, tzinfo=UTC), 70, 75, 4, True)
    history = [SnapshotSignal(current.captured_at - timedelta(days=1), 55, 65, 3, True)]
    assert classify_lifecycle(history, current) == "Growing"

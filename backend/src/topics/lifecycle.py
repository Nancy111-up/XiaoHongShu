from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

Lifecycle = Literal["Observing", "Emerging", "Growing", "Peak", "Declining", "Expired"]


@dataclass(frozen=True, slots=True)
class SnapshotSignal:
    captured_at: datetime
    current_heat: float
    trend_score: float | None
    valid_notes: int
    successful_refresh: bool
    previous_lifecycle: Lifecycle | None = None


def classify_lifecycle(history: list[SnapshotSignal], current: SnapshotSignal) -> Lifecycle:
    recent = [current, *history]
    if len(recent) >= 3 and all(
        item.successful_refresh and item.valid_notes == 0 for item in recent[:3]
    ):
        return "Expired"
    if len(recent) < 2 or current.trend_score is None:
        return "Observing"
    previous = history[0]
    if (
        current.trend_score >= 60
        and previous.trend_score is not None
        and previous.trend_score >= 60
    ):
        return "Growing"
    age = current.captured_at - min(item.captured_at for item in recent)
    if age <= timedelta(hours=72) and current.trend_score >= 60:
        return "Emerging"
    if (
        current.current_heat >= 80
        and 40 <= current.trend_score < 60
        and previous.previous_lifecycle in {"Emerging", "Growing", "Peak"}
    ):
        return "Peak"
    if current.trend_score < 40 and previous.trend_score is not None and previous.trend_score < 40:
        return "Declining"
    return "Observing"

from __future__ import annotations


def position_momentum(previous_position: int, current_position: int) -> float:
    return (previous_position - current_position) / max(previous_position, 1)


def trend_score(
    new_note_velocity: float,
    engagement_velocity: float,
    search_momentum: float,
    persistence: float,
    creator_expansion: float,
) -> float:
    return (
        new_note_velocity * 0.25
        + engagement_velocity * 0.25
        + search_momentum * 0.20
        + persistence * 0.15
        + creator_expansion * 0.15
    )

from __future__ import annotations


def weighted_engagement(likes: int, collects: int, comments: int) -> float:
    return likes + collects * 1.5 + comments * 2


def current_heat(metrics: dict[str, float | None]) -> float:
    weights = {
        "engagement": 35,
        "freshness": 25,
        "volume": 15,
        "creator_spread": 15,
        "comment_demand": 10,
    }
    available = {key: value for key, value in metrics.items() if value is not None}
    denominator = sum(weights[key] for key in available)
    if not denominator:
        return 0.0
    return sum(weights[key] * value for key, value in available.items()) / denominator

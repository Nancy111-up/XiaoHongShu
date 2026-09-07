from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class OpportunityDimensions:
    brand_relevance: float
    audience_relevance: float
    trend_timing: float
    content_opportunity: float
    product_fit: float


def opportunity_score(scores: OpportunityDimensions) -> float:
    return round(
        scores.brand_relevance * 0.30
        + scores.audience_relevance * 0.20
        + scores.trend_timing * 0.20
        + scores.content_opportunity * 0.20
        + scores.product_fit * 0.10,
        2,
    )


def trend_timing(current_heat: float, trend_score: float | None, lifecycle: str) -> float:
    if lifecycle == "Expired":
        return 0
    if trend_score is None:
        return min(current_heat * 0.8, 70)
    adjustments = {"Emerging": 10, "Growing": 15, "Peak": -5, "Declining": -25, "Observing": 0}
    return min(100, max(0, 0.6 * trend_score + 0.4 * current_heat + adjustments.get(lifecycle, 0)))


def decision(score: float, eligibility: str = "eligible") -> str:
    if eligibility == "filtered":
        return "Filtered"
    if score >= 80:
        return "High Opportunity"
    if score >= 65:
        return "Recommend"
    if score >= 50:
        return "Watch"
    return "Ignore"


def content_goals(scores: OpportunityDimensions) -> list[str]:
    if (
        scores.audience_relevance >= 70
        and scores.content_opportunity >= 65
        and scores.product_fit < 60
    ):
        return ["流量"]
    ranked = sorted(
        (
            (scores.audience_relevance, "流量"),
            (scores.brand_relevance, "品牌"),
            (scores.product_fit, "产品"),
        ),
        reverse=True,
    )
    return [goal for score, goal in ranked[:2] if score >= 50]

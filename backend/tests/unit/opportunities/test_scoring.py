import pytest

from src.opportunities.scoring import (
    OpportunityDimensions,
    decision,
    opportunity_score,
    trend_timing,
)


def test_opportunity_score_uses_contract_weights() -> None:
    scores = OpportunityDimensions(
        brand_relevance=100,
        audience_relevance=80,
        trend_timing=60,
        content_opportunity=40,
        product_fit=20,
    )
    assert opportunity_score(scores) == 68


@pytest.mark.parametrize(
    ("lifecycle", "expected"),
    [
        ("Emerging", 60),
        ("Growing", 65),
        ("Peak", 45),
        ("Declining", 25),
        ("Expired", 0),
        ("Observing", 50),
    ],
)
def test_trend_timing_applies_lifecycle_adjustments(lifecycle: str, expected: float) -> None:
    assert trend_timing(50, 50, lifecycle) == expected


def test_first_refresh_timing_is_capped_at_70() -> None:
    assert trend_timing(100, None, "Growing") == 70


@pytest.mark.parametrize(
    ("score", "expected"),
    [(80, "High Opportunity"), (65, "Recommend"), (50, "Watch"), (49, "Ignore")],
)
def test_decision_boundaries(score: float, expected: str) -> None:
    assert decision(score) == expected


def test_filtered_gate_always_wins() -> None:
    assert decision(100, eligibility="filtered") == "Filtered"

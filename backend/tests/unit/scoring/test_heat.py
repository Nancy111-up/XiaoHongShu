import pytest

from src.scoring.heat import current_heat, weighted_engagement


def test_weighted_engagement_uses_contract_weights() -> None:
    assert weighted_engagement(likes=10, collects=4, comments=3) == 22


def test_unavailable_comment_demand_reweights_remaining_metrics() -> None:
    normalized = {
        "engagement": 100,
        "freshness": 0,
        "volume": 0,
        "creator_spread": 0,
        "comment_demand": None,
    }
    assert current_heat(normalized) == pytest.approx(35 / 90 * 100)

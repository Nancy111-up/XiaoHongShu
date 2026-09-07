import pytest

from src.scoring.trend import position_momentum, trend_score


def test_position_momentum_reflects_search_rank_changes() -> None:
    assert position_momentum(20, 10) == pytest.approx(0.5)
    assert position_momentum(5, 10) == pytest.approx(-1.0)


def test_trend_score_uses_contract_weights() -> None:
    assert trend_score(100, 80, 50, 40, 20) == pytest.approx(64)

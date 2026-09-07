from src.scoring.confidence import classify_confidence


def test_confidence_high_requires_complete_evidence() -> None:
    assert classify_confidence(2, 5, 3, 0.8, 10, False, False) == "High"


def test_confidence_partial_success_is_penalized() -> None:
    assert classify_confidence(2, 5, 3, 0.9, 12, False, True) == "Medium"

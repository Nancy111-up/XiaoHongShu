from src.opportunities.gates import EligibilityContext, evaluate_eligibility


def test_brand_safety_and_expired_are_filtered_before_scoring() -> None:
    assert (
        evaluate_eligibility(EligibilityContext(risk="high", lifecycle="Growing")).status
        == "filtered"
    )
    assert (
        evaluate_eligibility(EligibilityContext(risk="low", lifecycle="Expired")).status
        == "filtered"
    )


def test_low_brand_and_product_fit_is_filtered() -> None:
    result = evaluate_eligibility(
        EligibilityContext(risk="low", lifecycle="Growing", brand_relevance=24, product_fit=19)
    )
    assert result.status == "filtered"


def test_recent_duplicate_requires_manual_review() -> None:
    result = evaluate_eligibility(
        EligibilityContext(
            risk="low",
            lifecycle="Growing",
            brand_relevance=70,
            product_fit=60,
            recent_duplicate=True,
        )
    )
    assert result.status == "manual_review"

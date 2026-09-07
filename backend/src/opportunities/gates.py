from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class EligibilityContext:
    risk: str
    lifecycle: str
    brand_relevance: float | None = None
    product_fit: float | None = None
    recent_duplicate: bool = False


@dataclass(frozen=True, slots=True)
class EligibilityResult:
    status: Literal["eligible", "filtered", "manual_review"]
    reason: str | None = None


def evaluate_eligibility(context: EligibilityContext) -> EligibilityResult:
    if context.risk.lower() == "high":
        return EligibilityResult("filtered", "brand_safety")
    if context.lifecycle == "Expired":
        return EligibilityResult("filtered", "expired")
    if (
        context.brand_relevance is not None
        and context.product_fit is not None
        and context.brand_relevance < 25
        and context.product_fit < 20
    ):
        return EligibilityResult("filtered", "relevance_floor")
    if context.recent_duplicate:
        return EligibilityResult("manual_review", "recent_duplicate")
    return EligibilityResult("eligible")

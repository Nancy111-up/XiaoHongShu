import pytest
from pydantic import ValidationError

from src.brand.schemas import BrandProfileInput, ContentStrategy


def test_content_strategy_must_total_one_hundred() -> None:
    with pytest.raises(ValidationError):
        BrandProfileInput(
            positioning="专业运动",
            content_strategy=ContentStrategy(traffic=40, brand=40, product=40),
        )

import pytest
from pydantic import ValidationError

from src.brand.schemas import BrandProfileInput, ContentStrategy
from src.brand.service import BrandService


class FakeBrandRepository:
    def __init__(self) -> None:
        self.saved = []

    async def latest_version(self) -> int | None:
        return self.saved[-1].version if self.saved else None

    async def save(self, profile):  # type: ignore[no-untyped-def]
        self.saved.append(profile)
        return profile


def profile() -> BrandProfileInput:
    return BrandProfileInput(
        positioning="专业运动",
        content_strategy=ContentStrategy(traffic=40, brand=35, product=25),
    )


def test_content_strategy_must_total_one_hundred() -> None:
    with pytest.raises(ValidationError):
        BrandProfileInput(
            positioning="专业运动",
            content_strategy=ContentStrategy(traffic=40, brand=40, product=40),
        )


@pytest.mark.asyncio
async def test_each_update_creates_an_immutable_incremented_version() -> None:
    repository = FakeBrandRepository()
    service = BrandService(repository)

    first = await service.update(profile())
    second = await service.update(profile())

    assert (first.version, second.version) == (1, 2)
    assert first is repository.saved[0]

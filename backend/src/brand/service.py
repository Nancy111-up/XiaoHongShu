from __future__ import annotations

from typing import Protocol

from src.brand.schemas import BrandProfileInput, BrandProfileVersion


class BrandRepository(Protocol):
    async def latest_version(self) -> int | None: ...

    async def save(self, profile: BrandProfileVersion) -> BrandProfileVersion: ...


class BrandService:
    def __init__(self, repository: BrandRepository) -> None:
        self._repository = repository

    async def update(self, profile: BrandProfileInput) -> BrandProfileVersion:
        latest = await self._repository.latest_version()
        versioned = BrandProfileVersion(version=(latest or 0) + 1, profile=profile)
        return await self._repository.save(versioned)

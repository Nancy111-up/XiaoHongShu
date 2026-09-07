from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.brand.schemas import BrandProfileVersion
from src.db.models import BrandProfile


class SQLBrandRepository:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def latest_version(self) -> int | None:
        async with self._sessions() as session:
            return await session.scalar(select(func.max(BrandProfile.version)))

    async def save(self, profile: BrandProfileVersion) -> BrandProfileVersion:
        async with self._sessions() as session:
            session.add(
                BrandProfile(
                    version=profile.version,
                    profile_json=profile.profile.model_dump_json(by_alias=True),
                )
            )
            await session.commit()
        return profile

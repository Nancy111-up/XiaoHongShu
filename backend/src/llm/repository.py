from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.db.models import LLMRun


class LLMRunRepository:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def save(self, **values: object) -> None:
        async with self._sessions() as session:
            session.add(LLMRun(**values))
            await session.commit()

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


def create_session_factory(database_url: str) -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(database_url)
    return async_sessionmaker(engine, expire_on_commit=False)


session_factory = create_session_factory("sqlite+aiosqlite:///./data/sports_brand_agent.sqlite3")


async def get_session() -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        yield session

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.db.models import Opportunity, OpportunityLLMRun


class OpportunityRepository:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def save(self, opportunity: Opportunity, llm_run_ids: list[str]) -> Opportunity:
        async with self._sessions() as session:
            session.add(opportunity)
            await session.flush()
            session.add_all(
                [
                    OpportunityLLMRun(opportunity_id=opportunity.id, llm_run_id=run_id)
                    for run_id in dict.fromkeys(llm_run_ids)
                ]
            )
            await session.commit()
        return opportunity

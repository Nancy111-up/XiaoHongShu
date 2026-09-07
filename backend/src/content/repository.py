from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.content.schemas import CopyPreview, FullDraftContent, RejectInput
from src.db.models import CalendarItem, Draft, Opportunity, RejectFeedback


class ContentRepository:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def get_opportunity(self, opportunity_id: str) -> Opportunity | None:
        async with self._sessions() as session:
            return await session.get(Opportunity, opportunity_id)

    async def save_preview(self, opportunity_id: str, preview: CopyPreview) -> None:
        async with self._sessions() as session:
            opportunity = await session.get(Opportunity, opportunity_id)
            if opportunity is None:
                raise LookupError("opportunity not found")
            opportunity.copy_preview_json = preview.model_dump_json()
            await session.commit()

    async def save_draft(self, opportunity: Opportunity, content: FullDraftContent) -> Draft:
        async with self._sessions() as session:
            draft = Draft(
                source_opportunity_id=opportunity.id,
                topic_id=opportunity.topic_id,
                brand_profile_version=opportunity.brand_profile_version,
                prompt_version=content.prompt_version,
                titles_json=json.dumps(content.titles, ensure_ascii=False),
                body=content.body,
                tags_json=json.dumps(content.tags, ensure_ascii=False),
                cta=content.cta,
                cover_text=content.cover_text,
                image_plan_json=json.dumps(
                    {"image_count": content.image_count, "image_advice": content.image_advice},
                    ensure_ascii=False,
                ),
                product_connection=content.product_connection,
                risk_check_json=json.dumps(content.risk_check, ensure_ascii=False),
                status="draft",
            )
            session.add(draft)
            await session.commit()
            await session.refresh(draft)
            return draft

    async def save_rejection(self, opportunity_id: str, rejection: RejectInput) -> RejectFeedback:
        async with self._sessions() as session:
            feedback = RejectFeedback(
                opportunity_id=opportunity_id, reason=rejection.reason, detail=rejection.detail
            )
            session.add(feedback)
            await session.commit()
            await session.refresh(feedback)
            return feedback

    async def schedule(self, draft_id: str, when: datetime) -> CalendarItem:
        async with self._sessions() as session:
            if await session.get(Draft, draft_id) is None:
                raise LookupError("draft not found")
            item = CalendarItem(draft_id=draft_id, scheduled_for=when, status="scheduled")
            session.add(item)
            await session.commit()
            await session.refresh(item)
            return item

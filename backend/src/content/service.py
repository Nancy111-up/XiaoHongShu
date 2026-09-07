from __future__ import annotations

from datetime import datetime
from typing import Protocol

from src.content.schemas import CopyPreview, FullDraftContent, RejectInput
from src.db.models import CalendarItem, Draft, Opportunity, RejectFeedback


class ContentStore(Protocol):
    async def get_opportunity(self, opportunity_id: str) -> Opportunity | None: ...
    async def save_preview(self, opportunity_id: str, preview: CopyPreview) -> None: ...
    async def save_draft(self, opportunity: Opportunity, content: FullDraftContent) -> Draft: ...
    async def save_rejection(
        self, opportunity_id: str, rejection: RejectInput
    ) -> RejectFeedback: ...
    async def schedule(self, draft_id: str, when: datetime) -> CalendarItem: ...


class ContentGenerator(Protocol):
    async def generate_preview(self, opportunity: Opportunity) -> CopyPreview: ...
    async def generate_full_copy(self, opportunity: Opportunity) -> FullDraftContent: ...


class ContentService:
    def __init__(self, repository: ContentStore, generator: ContentGenerator) -> None:
        self._repository = repository
        self._generator = generator

    async def _opportunity(self, opportunity_id: str) -> Opportunity:
        opportunity = await self._repository.get_opportunity(opportunity_id)
        if opportunity is None:
            raise LookupError("opportunity not found")
        return opportunity

    async def generate_preview(self, opportunity_id: str) -> CopyPreview:
        preview = await self._generator.generate_preview(await self._opportunity(opportunity_id))
        await self._repository.save_preview(opportunity_id, preview)
        return preview

    async def accept_opportunity(self, opportunity_id: str) -> Draft:
        opportunity = await self._opportunity(opportunity_id)
        if opportunity.eligibility == "filtered":
            raise ValueError("filtered opportunity cannot be accepted")
        content = await self._generator.generate_full_copy(opportunity)
        return await self._repository.save_draft(opportunity, content)

    async def reject_opportunity(
        self, opportunity_id: str, rejection: RejectInput
    ) -> RejectFeedback:
        await self._opportunity(opportunity_id)
        return await self._repository.save_rejection(opportunity_id, rejection)

    async def schedule_draft(self, draft_id: str, when: datetime) -> CalendarItem:
        if when.tzinfo is None:
            raise ValueError("scheduled time must include timezone")
        return await self._repository.schedule(draft_id, when)

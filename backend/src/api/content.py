import json
from datetime import UTC, datetime

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.content.schemas import RejectInput
from src.content.service import ContentService
from src.db.models import CalendarItem, Draft


def build_router(
    sessions: async_sessionmaker[AsyncSession], service: ContentService | None
) -> APIRouter:
    router = APIRouter(tags=["content"])

    @router.get("/drafts")
    async def list_drafts() -> dict[str, object]:
        async with sessions() as session:
            drafts = list(await session.scalars(select(Draft).order_by(Draft.updated_at.desc())))
        return {"items": [_draft(item) for item in drafts]}

    @router.get("/calendar")
    async def list_calendar() -> dict[str, object]:
        async with sessions() as session:
            items = list(
                await session.scalars(select(CalendarItem).order_by(CalendarItem.scheduled_for))
            )
        return {"items": [_calendar(item) for item in items]}

    @router.post("/opportunities/{opportunity_id}/accept")
    async def accept(opportunity_id: str) -> object:
        if service is None:
            return JSONResponse(status_code=503, content={"code": "ANALYSIS_UNAVAILABLE"})
        try:
            return _draft(await service.accept_opportunity(opportunity_id))
        except ValueError as exc:
            return JSONResponse(
                status_code=422, content={"code": "OPPORTUNITY_FILTERED", "message": str(exc)}
            )

    @router.post("/opportunities/{opportunity_id}/reject")
    async def reject(opportunity_id: str, payload: RejectInput) -> object:
        if service is None:
            return JSONResponse(status_code=503, content={"code": "CONTENT_SERVICE_UNAVAILABLE"})
        feedback = await service.reject_opportunity(opportunity_id, payload)
        return {"id": feedback.id, "reason": feedback.reason}

    @router.post("/drafts/{draft_id}/schedule")
    async def schedule(draft_id: str, when: datetime) -> object:
        if service is None:
            return JSONResponse(status_code=503, content={"code": "CONTENT_SERVICE_UNAVAILABLE"})
        item = await service.schedule_draft(draft_id, when)
        return _calendar(item)

    return router


def _calendar(item: CalendarItem) -> dict[str, str]:
    # The calendar contract is an explicit UTC instant, including SQLite's naive reads.
    when = item.scheduled_for
    if when.tzinfo is None:
        when = when.replace(tzinfo=UTC)
    return {
        "id": item.id,
        "draftId": item.draft_id,
        "scheduledFor": when.astimezone(UTC).isoformat(),
        "status": item.status,
    }


def _draft(draft: Draft) -> dict[str, object]:
    return {
        "id": draft.id,
        "sourceOpportunityId": draft.source_opportunity_id,
        "topicId": draft.topic_id,
        "brandProfileVersion": draft.brand_profile_version,
        "promptVersion": draft.prompt_version,
        "titles": json.loads(draft.titles_json),
        "body": draft.body,
        "tags": json.loads(draft.tags_json),
        "status": draft.status,
    }

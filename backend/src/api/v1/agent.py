"""Agent API endpoints — 对齐 IMPLEMENTATION_PLAN §3"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.agent.tools.tavily_search import search_trends
from src.core.constants import FeedbackAction
from src.db.session import get_db
from src.schemas.agent import (
    AgentStatusResponse,
    DiscoverRequest,
    FeedbackRequest,
    StartRequest,
)
from src.schemas.board import TaskCardSchema
from src.schemas.common import APIResponse, TopicCardSchema, VisualGuidanceSchema
from src.services import board_service
from src.services.task_service import (
    approve_task,
    cancel_task,
    create_task,
    get_task,
    revise_task,
    update_task_step,
)

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/discover")
async def discover(req: DiscoverRequest) -> APIResponse[list[TopicCardSchema]]:
    keyword = req.keyword or "小红书 时尚 穿搭 趋势"
    raw_topics = await search_trends(keyword)
    cards = [
        TopicCardSchema(
            card_id=str(i),
            title=t.split(" —— ")[0] if " —— " in t else t[:60],
            reason=t.split(" —— ")[1] if " —— " in t else "趋势发现",
            heat_index=min(60 + i * 8, 95),
            estimated_traffic=f"{3 + i * 2}-{8 + i * 4}k 曝光",
        )
        for i, t in enumerate(raw_topics[:5])
    ]
    return APIResponse.ok(cards)


@router.post("/start")
async def start_task(
    req: StartRequest, db: AsyncSession = Depends(get_db)
) -> APIResponse[dict]:
    task = await create_task(db, user_input=req.topic, source=req.source)
    return APIResponse.ok({"thread_id": task.id})


@router.get("/status/{thread_id}")
async def get_status(
    thread_id: str, db: AsyncSession = Depends(get_db)
) -> APIResponse[AgentStatusResponse]:
    task = await get_task(db, thread_id)
    guidance = None
    if task.visual_guidance_json:
        import json

        try:
            guidance = VisualGuidanceSchema(**json.loads(task.visual_guidance_json))
        except (json.JSONDecodeError, TypeError):
            guidance = None

    status = AgentStatusResponse(
        thread_id=task.id,
        status=task.status,
        current_step=task.current_step or "",
        draft_copy=task.draft_copy,
        visual_guidance=guidance,
        error_logs=[],
    )
    return APIResponse.ok(status)


@router.post("/feedback")
async def submit_feedback(
    req: FeedbackRequest, db: AsyncSession = Depends(get_db)
) -> APIResponse[dict]:
    if req.action == FeedbackAction.APPROVE:
        final = req.edited_content or req.feedback or ""
        await approve_task(db, req.thread_id, final)
    else:
        await revise_task(
            db,
            req.thread_id,
            feedback=req.feedback,
            edited_content=req.edited_content,
        )
    return APIResponse.ok({"thread_id": req.thread_id, "action": req.action})


@router.post("/cancel/{thread_id}")
async def cancel(
    thread_id: str, db: AsyncSession = Depends(get_db)
) -> APIResponse[dict]:
    await cancel_task(db, thread_id)
    return APIResponse.ok({"thread_id": thread_id, "status": "cancelled"})

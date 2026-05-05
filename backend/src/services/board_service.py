"""Kanban board aggregation — 四列看板全量查询"""

from __future__ import annotations

import json

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.constants import KanbanColumn
from src.schemas.board import KanbanBoardResponse, TaskCardSchema
from src.schemas.common import VisualGuidanceSchema
from src.services.task_service import list_tasks_by_column


def _to_task_card(task) -> TaskCardSchema:
    guidance = None
    if task.visual_guidance_json:
        try:
            guidance = VisualGuidanceSchema(**json.loads(task.visual_guidance_json))
        except (json.JSONDecodeError, TypeError):
            guidance = None

    return TaskCardSchema(
        thread_id=task.id,
        user_input=task.user_input,
        status=task.status,
        column=task.column,
        revision_count=task.revision_count,
        draft_copy=task.draft_copy,
        final_copy=task.final_copy,
        visual_guidance=guidance,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


async def get_kanban_board(db: AsyncSession) -> KanbanBoardResponse:
    in_progress_tasks = await list_tasks_by_column(db, KanbanColumn.IN_PROGRESS)
    pending_tasks = await list_tasks_by_column(db, KanbanColumn.PENDING_REVIEW)
    done_tasks = await list_tasks_by_column(db, KanbanColumn.DONE)

    return KanbanBoardResponse(
        inspiration=[],  # populated from agent discover endpoint
        in_progress=[_to_task_card(t) for t in in_progress_tasks],
        pending_review=[_to_task_card(t) for t in pending_tasks],
        done=[_to_task_card(t) for t in done_tasks],
    )

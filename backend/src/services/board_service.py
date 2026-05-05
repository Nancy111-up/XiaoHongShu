"""Kanban board aggregation — 四列看板全量查询"""

from __future__ import annotations

import json

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.constants import KanbanColumn
from src.schemas.board import KanbanBoardResponse, TaskCardSchema
from src.schemas.common import TopicCardSchema, VisualGuidanceSchema
from src.services.task_service import list_tasks_by_column


import re

# 灵感池缓存 — 由 /discover 端点写入，/board 端点读取
_inspiration_cache: list[TopicCardSchema] = []


def update_inspiration_cache(cards: list[TopicCardSchema]) -> None:
    global _inspiration_cache
    _inspiration_cache = list(cards)

def _format_draft(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw:
        return ""
    if raw.startswith("{"):
        # Try standard JSON first
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return _render_parsed_draft(parsed)
        except (json.JSONDecodeError, TypeError):
            pass

        # Fallback: LLM sometimes uses 「」 instead of "" for title values
        try:
            # Fix: LLM outputs 「value」" or 「value」 as JSON string delimiters
            fixed = re.sub(
                r':\s*「([^」]+)」"?',
                r': "\1"',
                raw,
            )
            parsed = json.loads(fixed)
            if isinstance(parsed, dict):
                return _render_parsed_draft(parsed)
        except (json.JSONDecodeError, TypeError):
            pass
    return raw


def _render_parsed_draft(parsed: dict) -> str:
    parts: list[str] = []
    title = parsed.get("title", "")
    body = parsed.get("body", "")
    tags = parsed.get("tags", [])
    if title:
        parts.append(f"**{title}**")
    if body:
        parts.append(body.replace("\\n", "\n"))
    if tags and isinstance(tags, list):
        parts.append(" ".join(str(t) for t in tags))
    return "\n\n".join(parts) if parts else json.dumps(parsed, ensure_ascii=False)


def _to_task_card(task) -> TaskCardSchema:
    guidance = None
    if task.visual_guidance_json:
        try:
            guidance = VisualGuidanceSchema(**json.loads(task.visual_guidance_json))
        except (json.JSONDecodeError, TypeError):
            guidance = None

    error_logs: list[str] | None = None
    if getattr(task, "error_logs", None):
        try:
            error_logs = json.loads(task.error_logs)
        except (json.JSONDecodeError, TypeError):
            error_logs = None

    return TaskCardSchema(
        thread_id=task.id,
        user_input=task.user_input,
        status=task.status,
        column=task.column,
        revision_count=task.revision_count,
        draft_copy=_format_draft(task.draft_copy or ""),
        final_copy=_format_draft(task.final_copy or ""),
        visual_guidance=guidance,
        error_logs=error_logs,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


async def get_kanban_board(db: AsyncSession) -> KanbanBoardResponse:
    in_progress_tasks = await list_tasks_by_column(db, KanbanColumn.IN_PROGRESS)
    pending_tasks = await list_tasks_by_column(db, KanbanColumn.PENDING_REVIEW)
    done_tasks = await list_tasks_by_column(db, KanbanColumn.DONE)

    return KanbanBoardResponse(
        inspiration=_inspiration_cache,
        in_progress=[_to_task_card(t) for t in in_progress_tasks],
        pending_review=[_to_task_card(t) for t in pending_tasks],
        done=[_to_task_card(t) for t in done_tasks],
    )

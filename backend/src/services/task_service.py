"""Task CRUD + state machine — 创作任务生命周期管理"""

from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.constants import TaskStatus
from src.core.exceptions import TaskNotCancellableError, TaskNotFoundError
from src.models.task import Task


async def create_task(
    db: AsyncSession,
    *,
    user_input: str,
    source: str = "manual",
) -> Task:
    task = Task(user_input=user_input, source=source)
    db.add(task)
    await db.flush()
    await db.refresh(task)
    return task


async def get_task(db: AsyncSession, thread_id: str) -> Task:
    task = await db.get(Task, thread_id)
    if task is None:
        raise TaskNotFoundError(f"Task {thread_id} not found")
    return task


async def update_task_step(
    db: AsyncSession,
    thread_id: str,
    *,
    current_step: str,
    draft_copy: str | None = None,
    visual_guidance_json: str | None = None,
    error_logs: str | None = None,
) -> Task:
    task = await get_task(db, thread_id)
    task.current_step = current_step
    if draft_copy is not None:
        task.draft_copy = draft_copy
    if visual_guidance_json is not None:
        task.visual_guidance_json = visual_guidance_json
    await db.flush()
    return task


async def set_task_waiting_for_human(
    db: AsyncSession,
    thread_id: str,
    *,
    draft_copy: str,
    visual_guidance_json: str | None = None,
    feedback_history_json: str | None = None,
) -> Task:
    task = await get_task(db, thread_id)
    task.status = TaskStatus.WAITING_FOR_HUMAN
    task.current_step = "human_review"
    task.column = "pending_review"
    task.draft_copy = draft_copy
    if visual_guidance_json is not None:
        task.visual_guidance_json = visual_guidance_json
    if feedback_history_json is not None:
        task.feedback_history_json = feedback_history_json
    await db.flush()
    return task


async def approve_task(db: AsyncSession, thread_id: str, final_copy: str) -> Task:
    task = await get_task(db, thread_id)
    task.status = TaskStatus.DONE
    task.current_step = "finalize"
    task.column = "done"
    task.final_copy = final_copy
    await db.flush()
    return task


async def revise_task(
    db: AsyncSession,
    thread_id: str,
    *,
    feedback: str,
    edited_content: str,
) -> Task:
    task = await get_task(db, thread_id)
    task.status = TaskStatus.IN_PROGRESS
    task.current_step = "generate_copy"
    task.column = "in_progress"
    task.revision_count += 1
    if edited_content:
        task.draft_copy = edited_content

    fb_history: list[dict] = []
    if task.feedback_history_json:
        try:
            fb_history = json.loads(task.feedback_history_json)
        except (json.JSONDecodeError, TypeError):
            fb_history = []
    fb_history.append({"round": task.revision_count, "feedback": feedback})
    task.feedback_history_json = json.dumps(fb_history, ensure_ascii=False)

    await db.flush()
    return task


async def update_task_status(
    db: AsyncSession,
    thread_id: str,
    *,
    status: str,
    current_step: str | None = None,
    column: str | None = None,
) -> Task:
    task = await get_task(db, thread_id)
    task.status = status
    if current_step is not None:
        task.current_step = current_step
    if column is not None:
        task.column = column
    await db.flush()
    return task


async def cancel_task(db: AsyncSession, thread_id: str) -> Task:
    task = await get_task(db, thread_id)
    if task.status in (TaskStatus.DONE, TaskStatus.CANCELLED):
        raise TaskNotCancellableError(
            f"Task {thread_id} is already {task.status}"
        )
    task.status = TaskStatus.CANCELLED
    task.current_step = "cancelled"
    await db.flush()
    return task


async def mark_task_failed(
    db: AsyncSession,
    thread_id: str,
    *,
    error_message: str,
) -> Task:
    task = await get_task(db, thread_id)
    task.status = TaskStatus.FAILED
    task.current_step = "graph_crashed"
    task.column = "in_progress"
    task.error_logs = json.dumps([error_message], ensure_ascii=False)
    await db.flush()
    return task


async def list_tasks_by_column(db: AsyncSession, column: str) -> list[Task]:
    result = await db.execute(
        select(Task)
        .where(Task.column == column)
        .order_by(Task.updated_at.desc())
    )
    return list(result.scalars().all())

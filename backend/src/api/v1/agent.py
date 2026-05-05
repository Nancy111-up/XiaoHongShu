"""Agent API endpoints — 对齐 IMPLEMENTATION_PLAN §3

P0 集成: /start 后台运行 LangGraph, /feedback 使用 Command(resume) 驱动 Graph.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re

from fastapi import APIRouter, Depends, Request
from langgraph.types import Command
from sqlalchemy.ext.asyncio import AsyncSession

from src.agent.state import create_initial_state
from src.agent.tools.mcp_client import MCPServiceError, get_mcp_manager
from src.core.constants import FeedbackAction, TaskStatus
from src.db.session import _get_sessionmaker, get_db
from src.deps import get_graph
from src.schemas.agent import (
    AgentStatusResponse,
    DiscoverRequest,
    FeedbackRequest,
    StartRequest,
)
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

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["agent"])


# ─────────────────────────────────────────────
#  Graph → ORM 状态同步
# ─────────────────────────────────────────────
def _format_draft_copy(raw: str) -> str:
    """将可能为 JSON 的 draft_copy 转为 Markdown 可读文本。"""
    raw = (raw or "").strip()
    if not raw:
        return ""
    if raw.startswith("{"):
        # Try standard JSON first
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return _render_draft_parts(parsed)
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
                return _render_draft_parts(parsed)
        except (json.JSONDecodeError, TypeError):
            pass
    return raw


def _render_draft_parts(parsed: dict) -> str:
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


async def _sync_graph_state_to_db(thread_id: str, state_values: dict) -> None:
    """读取 LangGraph checkpointer 中的最终状态，写回 Task ORM 行。"""
    try:
        async with _get_sessionmaker()() as session:
            try:
                task = await get_task(session, thread_id)
                current_step = state_values.get("current_step", "")

                if current_step == "review_complete":
                    task.status = TaskStatus.WAITING_FOR_HUMAN
                    task.column = "pending_review"
                    task.current_step = "human_review"
                elif current_step in ("finalize_complete",):
                    task.status = TaskStatus.DONE
                    task.column = "done"
                    task.current_step = current_step
                    task.final_copy = (
                        state_values.get("final_copy", "")
                        or state_values.get("draft_copy", "")
                    )
                else:
                    task.status = TaskStatus.IN_PROGRESS
                    task.column = "in_progress"
                    task.current_step = current_step

                draft_raw = state_values.get("draft_copy", "")
                task.draft_copy = _format_draft_copy(draft_raw) or task.draft_copy
                task.revision_count = state_values.get("revision_count", 0)

                vg = state_values.get("visual_guidance")
                if vg and isinstance(vg, dict):
                    task.visual_guidance_json = json.dumps(vg, ensure_ascii=False)

                fb_history = state_values.get("feedback_history")
                if fb_history and isinstance(fb_history, list):
                    task.feedback_history_json = json.dumps(fb_history, ensure_ascii=False)

                await session.commit()
            except Exception:
                await session.rollback()
                raise
    except Exception:
        logger.exception("Failed to sync graph state for %s", thread_id)


async def _run_graph_and_sync(
    graph,
    config: dict,
    *,
    initial_state: dict | None = None,
    command: Command | None = None,
) -> None:
    """在后台运行 graph.ainvoke()，完成后将状态同步到 ORM。"""
    thread_id = config["configurable"]["thread_id"]
    try:
        if command is not None:
            await graph.ainvoke(command, config)
        else:
            await graph.ainvoke(initial_state, config)
    except Exception as exc:
        logger.exception("Graph execution error for %s", thread_id)
        error_msg = f"{type(exc).__name__}: {exc}"
        try:
            async with _get_sessionmaker()() as session:
                from src.services.task_service import mark_task_failed
                await mark_task_failed(session, thread_id, error_message=error_msg)
                await session.commit()
        except Exception:
            logger.exception("Failed to mark task %s as FAILED", thread_id)
        return  # Don't attempt state sync after crash

    try:
        state = await graph.aget_state(config)
        if state and state.values:
            # Use state.next to detect interrupt — when the graph pauses
            # at human_review, the node's return value hasn't been applied
            # to state.values yet, so current_step is still from the
            # previous node. state.next tells us which node(s) are waiting.
            if state.next and any("human_review" in str(n) for n in state.next):
                async with _get_sessionmaker()() as session:
                    try:
                        task = await get_task(session, thread_id)
                        task.status = TaskStatus.WAITING_FOR_HUMAN
                        task.column = "pending_review"
                        task.current_step = "human_review"
                        draft_raw = state.values.get("draft_copy", "")
                        task.draft_copy = _format_draft_copy(draft_raw) or task.draft_copy
                        task.revision_count = state.values.get("revision_count", 0)
                        vg = state.values.get("visual_guidance")
                        if vg and isinstance(vg, dict):
                            task.visual_guidance_json = json.dumps(vg, ensure_ascii=False)
                        fb_history = state.values.get("feedback_history")
                        if fb_history and isinstance(fb_history, list):
                            task.feedback_history_json = json.dumps(fb_history, ensure_ascii=False)
                        await session.commit()
                    except Exception:
                        await session.rollback()
                        raise
            else:
                await _sync_graph_state_to_db(thread_id, state.values)
    except Exception:
        logger.exception("State sync error for %s", thread_id)


# ─────────────────────────────────────────────
#  端点
# ─────────────────────────────────────────────

# 时尚选题关键词轮转池 — 每次发现热点使用不同关键词，保证多样性
_KEYWORD_POOL = [
    "早秋穿搭",
    "通勤穿搭",
    "韩系穿搭",
    "法式复古穿搭",
    "微胖穿搭",
    "小个子穿搭",
    "色彩穿搭",
    "极简穿搭",
    "职场穿搭",
    "约会穿搭",
    "度假穿搭",
    "运动穿搭",
    "梨形身材穿搭",
    "高级感穿搭",
    "学生党穿搭",
    "新中式穿搭",
    "甜酷穿搭",
    "慵懒风穿搭",
    "老钱风穿搭",
    "Y2K穿搭",
]
_keyword_index = 0


def _pick_keyword(user_keyword: str | None) -> str:
    """选择一个搜索关键词。用户指定则用用户的，否则按轮转池轮转。"""
    global _keyword_index
    if user_keyword:
        return user_keyword
    kw = _KEYWORD_POOL[_keyword_index % len(_KEYWORD_POOL)]
    _keyword_index += 1
    return kw


def _likes_to_heat(likes_text: str) -> int:
    """将互动数映射为 0-100 热度指数。"""
    t = likes_text.strip()
    try:
        if "万" in t:
            num = float(t.replace("万", ""))
            return min(int(num * 20 + 40), 100)
        num = int(t)
        if num >= 5000:
            return min(60 + num // 500, 100)
        if num >= 1000:
            return 50 + num // 200
        if num >= 100:
            return 35 + num // 20
        return 20 + num * 2
    except (ValueError, AttributeError):
        return 45


def _likes_to_traffic(likes_text: str) -> str:
    """根据互动数估算曝光量。"""
    t = likes_text.strip()
    try:
        if "万" in t:
            num = float(t.replace("万", ""))
            return f"{int(num * 2)}-{int(num * 5)}万 曝光"
        num = int(t)
        if num >= 5000:
            return f"{num // 1000}K-{num // 200}K 曝光"
        if num >= 1000:
            return f"1K-{num // 100}K 曝光"
        return "500-2K 曝光"
    except (ValueError, AttributeError):
        return "1-5K 曝光"


@router.post("/discover")
async def discover(req: DiscoverRequest) -> APIResponse[list[TopicCardSchema]]:
    keyword = _pick_keyword(req.keyword)
    cards: list[TopicCardSchema] = []
    seen_ids: set[str] = set()

    # MCP 搜索
    try:
        manager = get_mcp_manager()
        if not manager.is_connected:
            await manager.connect()
        if manager.is_connected:
            # 搜索当前关键词 + 额外一个随机关键词混搭
            import random
            extra_kw = random.choice(_KEYWORD_POOL) if not req.keyword else None
            queries = [keyword]
            if extra_kw and extra_kw != keyword:
                queries.append(extra_kw)

            import hashlib
            for q in queries:
                if len(cards) >= 8:
                    break
                raw = await manager.call_tool("search_trends", query=q, max_results=4, timeout=90)
                if isinstance(raw, list):
                    for note in raw:
                        if not isinstance(note, dict):
                            continue
                        content_key = f"{note.get('title', '')}-{note.get('author', '')}"
                        card_id = f"mcp-{hashlib.md5(content_key.encode()).hexdigest()[:12]}"
                        if card_id in seen_ids:
                            continue
                        seen_ids.add(card_id)

                        likes_text = note.get("likes_text", "N/A")
                        title_text = note.get("title", "").strip()
                        if not title_text or title_text == "(笔记)":
                            continue

                        cards.append(TopicCardSchema(
                            card_id=card_id,
                            title=title_text[:60],
                            reason=f"作者: {note.get('author', '未知')} | 互动: {likes_text}",
                            heat_index=_likes_to_heat(likes_text),
                            estimated_traffic=_likes_to_traffic(likes_text),
                        ))
    except (MCPServiceError, Exception) as e:
        logger.warning("MCP discover fallback: %s", e)

    # 退路：品牌相关静态默认选题
    if not cards:
        import hashlib
        defaults = [
            ("法式通勤穿搭公式", "小红书长期流量密码，'不费力高级感'持续走红"),
            ("小众设计师品牌合集", "国货设计师品牌搜索量上升，'小众不撞款'受追捧"),
            ("一包多背实用主义", "实用主义消费观盛行，多功能收纳成卖点"),
            ("胶囊衣橱极简生活", "低消费主义趋势，'少即是多'理念持续发酵"),
            ("质感穿搭底层逻辑", "深度穿搭内容互动率高，用户偏爱有理有据的分析"),
        ]
        for i, (title, reason) in enumerate(defaults):
            card_id = f"default-{hashlib.md5(title.encode()).hexdigest()[:12]}"
            cards.append(TopicCardSchema(
                card_id=card_id,
                title=title,
                reason=reason,
                heat_index=min(65 + i * 7, 90),
                estimated_traffic=f"{3 + i * 2}-{8 + i * 4}k 曝光",
            ))

    # 同步到灵感缓存，使 /board 端点可读取
    board_service.update_inspiration_cache(cards)
    return APIResponse.ok(cards)


@router.post("/start")
async def start_task(
    req: StartRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[dict]:
    # 1) 创建 DB 任务记录（看板用）
    task = await create_task(db, user_input=req.topic, source=req.source)

    # 2) 构建初始 AgentState（thread_id 与 ORM task.id 对齐）
    initial = create_initial_state(req.topic, thread_id=task.id)

    # 3) 后台运行 Graph
    graph = request.app.state.graph
    config = {"configurable": {"thread_id": task.id}}
    asyncio.create_task(
        _run_graph_and_sync(graph, config, initial_state=initial)
    )

    return APIResponse.ok({"thread_id": task.id})


@router.get("/status/{thread_id}")
async def get_status(
    thread_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[AgentStatusResponse]:
    # 优先从 checkpointer 读取最新状态
    try:
        state = await request.app.state.graph.aget_state(
            {"configurable": {"thread_id": thread_id}}
        )
    except Exception:
        state = None

    if state and state.values:
        s = state.values
        guidance = None
        vg = s.get("visual_guidance")
        if vg and isinstance(vg, dict):
            guidance = VisualGuidanceSchema(
                cover_suggestion=vg.get("cover_suggestion", ""),
                shot_descriptions=vg.get("shot_descriptions", []),
                domestic_image_prompts=vg.get("domestic_image_prompts", []),
            )

        current_step = s.get("current_step", "")
        # state.next reveals interrupt — human_review pauses before
        # returning, so current_step is still from the previous node
        if state.next and any("human_review" in str(n) for n in state.next):
            status_str = TaskStatus.WAITING_FOR_HUMAN
            current_step = "human_review"
        elif current_step == "review_complete":
            status_str = TaskStatus.WAITING_FOR_HUMAN
        elif current_step == "finalize_complete":
            status_str = TaskStatus.DONE
        else:
            status_str = TaskStatus.IN_PROGRESS

        draft = _format_draft_copy(s.get("draft_copy", ""))
        return APIResponse.ok(
            AgentStatusResponse(
                thread_id=thread_id,
                status=status_str,
                current_step=current_step,
                draft_copy=draft,
                visual_guidance=guidance,
                error_logs=s.get("error_logs", []),
            )
        )

    # 退路：从 ORM 读取
    task = await get_task(db, thread_id)
    guidance = None
    if task.visual_guidance_json:
        try:
            guidance = VisualGuidanceSchema(**json.loads(task.visual_guidance_json))
        except (json.JSONDecodeError, TypeError):
            guidance = None

    error_logs: list[str] = []
    if task.error_logs:
        try:
            error_logs = json.loads(task.error_logs)
        except (json.JSONDecodeError, TypeError):
            error_logs = []

    return APIResponse.ok(
        AgentStatusResponse(
            thread_id=task.id,
            status=task.status,
            current_step=task.current_step or "",
            draft_copy=task.draft_copy,
            visual_guidance=guidance,
            error_logs=error_logs,
        )
    )


@router.post("/feedback")
async def submit_feedback(
    req: FeedbackRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[dict]:
    # 1) 更新 ORM（保留兼容）
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

    # 2) 构建 Command(resume=...) 并后台恢复 Graph
    graph = request.app.state.graph
    config = {"configurable": {"thread_id": req.thread_id}}
    resume_payload = {
        "action": req.action,
        "feedback": req.feedback,
        "edited_content": req.edited_content,
    }
    cmd = Command(resume=resume_payload)
    asyncio.create_task(
        _run_graph_and_sync(graph, config, command=cmd)
    )

    return APIResponse.ok({"thread_id": req.thread_id, "action": req.action})


@router.post("/cancel/{thread_id}")
async def cancel(
    thread_id: str, db: AsyncSession = Depends(get_db)
) -> APIResponse[dict]:
    await cancel_task(db, thread_id)
    return APIResponse.ok({"thread_id": thread_id, "status": "cancelled"})

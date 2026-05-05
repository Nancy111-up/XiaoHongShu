"""AsyncSqliteSaver 工厂 — LangGraph checkpoint 异步持久化

对齐 IMPLEMENTATION_PLAN §4 — 替换 Phase 1 MemorySaver

注意：
- langgraph-checkpoint-sqlite 2.0.x 调用 conn.is_alive()，但 aiosqlite 0.22.x
  的 Connection 没有该方法。此处 monkey-patch 返回 True（连接由我们管理生命周期）。
- 所有节点均为 async，必须使用 AsyncSqliteSaver。
"""

from __future__ import annotations

from pathlib import Path

import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

# langgraph-checkpoint-sqlite 2.0.x 调用 conn.is_alive()，
# 但 aiosqlite 0.22.x Connection 未实现该方法。
if not hasattr(aiosqlite.Connection, "is_alive"):
    aiosqlite.Connection.is_alive = lambda self: True  # type: ignore[method-assign]

_async_saver: AsyncSqliteSaver | None = None


def _checkpoint_db_path() -> str:
    """从数据库 URL 提取文件路径。"""
    from src.config import get_settings

    db_url = get_settings().db_url
    if "///" in db_url:
        rel_path = db_url.split("///", 1)[1]
        p = Path(rel_path)
        if not p.is_absolute():
            p = Path.cwd() / p
        p.parent.mkdir(parents=True, exist_ok=True)
        return str(p)
    return "./data/xhs_agent.db"


async def create_checkpointer() -> AsyncSqliteSaver:
    """创建 AsyncSqliteSaver 单例。

    langgraph-checkpoint-sqlite 2.0.x 调用 conn.is_alive()，
    但 aiosqlite 0.22.x Connection 未实现该方法。monkey-patch 返回 True。
    调用方负责在应用关闭时调用 close_checkpointer()。
    """
    global _async_saver
    if _async_saver is not None:
        return _async_saver

    db_path = _checkpoint_db_path()
    conn = await aiosqlite.connect(db_path)
    _async_saver = AsyncSqliteSaver(conn=conn)
    return _async_saver


async def close_checkpointer() -> None:
    """关闭 AsyncSqliteSaver 的 aiosqlite 连接。"""
    global _async_saver
    if _async_saver is not None:
        conn = _async_saver.conn  # type: ignore[union-attr]
        await conn.close()
        _async_saver = None

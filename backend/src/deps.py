"""FastAPI 依赖注入 — graph / checkpointer 共享依赖"""

from __future__ import annotations

from fastapi import Request


def get_graph(request: Request):
    """注入编译后的 LangGraph CompiledGraph 实例。"""
    return request.app.state.graph


def get_checkpointer(request: Request):
    """注入 AsyncSqliteSaver checkpointer 实例。"""
    return request.app.state.checkpointer

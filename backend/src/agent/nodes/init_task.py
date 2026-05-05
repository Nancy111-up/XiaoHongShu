"""init_task 节点 —— 纯逻辑：初始化任务追踪字段，判断创作来源

无模型调用，无条件边逻辑
"""

from __future__ import annotations

from src.agent.state import AgentState


async def init_task_node(state: AgentState) -> dict:
    source = "inspiration_pool" if state.get("topic_cards") else "manual"

    return {
        "revision_count": 0,
        "is_revision": False,
        "violation_count": 0,
        "error_logs": [],
        "current_step": "init_task_complete",
    }

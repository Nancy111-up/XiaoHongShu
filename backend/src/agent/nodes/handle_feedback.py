"""handle_feedback 节点 —— 纯逻辑路由，将人类审核判决转化为状态变更

对齐 IMPLEMENTATION_PLAN §4.1 节点 8

行为：
- approve: 设定 final_copy = edited_draft_copy or draft_copy，路由至 finalize
- revise:  设定 is_revision=True, revision_count+1, 快照 draft_versions，路由至 extract_rules → generate_copy

注意：实际条件路由由 graph.py 根据 current_step 决定（见 Sub-round 5.9）
"""

from __future__ import annotations

from src.agent.state import AgentState


async def handle_feedback_node(state: AgentState) -> dict:
    action = state.get("feedback_action", "")

    if action == "approve":
        final_copy = state.get("edited_draft_copy") or state.get("draft_copy", "")
        return {
            "final_copy": final_copy,
            "feedback_action": "",  # 消费后清空，防止重复路由
            "current_step": "handle_feedback_approve",
        }

    # revise — 回流重写
    revision_count = state.get("revision_count", 0) + 1
    draft_versions = [*state.get("draft_versions", []), state.get("draft_copy", "")]

    return {
        "is_revision": True,
        "revision_count": revision_count,
        "draft_versions": draft_versions,
        "feedback_action": "",  # 消费后清空
        "current_step": "handle_feedback_revise",
    }

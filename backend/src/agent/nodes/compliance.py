"""风控校验节点 —— 识别敏感词，红线违规时路由回选题雷达"""

from __future__ import annotations

import asyncio

from src.agent.state import AgentState

# Mock 敏感词库
_SENSITIVE_WORDS = [
    "最",
    "第一",
    "国家级",
    "全网首发",
    "永久有效",
    "根治",
    "立竿见影",
    "100%",
    "绝对",
    "零风险",
]


async def compliance_node(state: AgentState) -> dict:
    await asyncio.sleep(0.2)

    draft = state.get("draft_copy", "")
    errors: list[str] = []

    for word in _SENSITIVE_WORDS:
        if word in draft:
            errors.append(f"命中敏感词：{word}")

    if errors:
        return {
            "current_step": "compliance_failed",
            "error_logs": errors,
        }

    return {
        "current_step": "compliance_pass",
        "error_logs": [],
    }

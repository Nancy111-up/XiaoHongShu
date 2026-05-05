"""human_review 节点 —— LangGraph interrupt 断点，等待人类审核判决

行为：
- 调用 interrupt() 暂停 Graph 执行
- 向审核面板展示 draft_copy + visual_guidance + compliance_severity
- 等待前端通过 Command(resume=...) 注入判决
- 返回 feedback_action / human_feedback / edited_draft_copy

独立节点原因（§4.1）：
- 状态持久化 SQLite（由 SqliteSaver 在 graph 层处理）
- 与 compliance / handle_feedback 解耦
"""

from __future__ import annotations

from langgraph.types import interrupt

from src.agent.state import AgentState


async def human_review_node(state: AgentState) -> dict:
    """暂停 Graph，等待人类审核员做出判决。

    interrupt() 返回前端通过 Command(resume=...) 注入的 dict：
        {
            "action": "approve" | "revise",
            "feedback": "修改意见文本（revise 时必填）",
            "edited_content": "微调后的文案（可选）",
        }
    """
    decision = interrupt({
        "action": "waiting_for_human",
        "draft_copy": state["draft_copy"],
        "visual_guidance": state.get("visual_guidance", {}),
        "compliance_severity": state.get("compliance_severity", "pass"),
        "violation_count": state.get("violation_count", 0),
        "topic_cards": state.get("topic_cards", []),
    })

    return {
        "feedback_action": decision.get("action", ""),
        "human_feedback": decision.get("feedback", ""),
        "edited_draft_copy": decision.get("edited_content", ""),
        "current_step": "review_complete",
    }

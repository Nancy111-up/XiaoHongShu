"""LangGraph 状态机 —— 编排「选题→撰写→风控→人类审核→循环」全链路

图结构:
    START → research → write → compliance ──[pass]→ human_review(interrupt)
                                    │                    │
                                    └──[fail]──→ research │
                                                     ┌───┘
                                              [approve] → END
                                              [revise]  → write
"""

from __future__ import annotations

from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt, Command

from src.agent.state import AgentState
from src.agent.nodes.research import research_node
from src.agent.nodes.write import write_node
from src.agent.nodes.compliance import compliance_node


# ============================
#  审核节点（中断点）
# ============================
async def human_review_node(state: AgentState) -> dict:
    """向人类展示文案草稿，暂停等待判决"""
    decision = interrupt({
        "action": "waiting_for_human",
        "draft_copy": state["draft_copy"],
        "topics": state.get("generated_topics", []),
    })

    # Command(resume=...) 注入的判决
    return {
        "human_action": decision.get("action", ""),
        "human_feedback": decision.get("feedback", ""),
        "edited_draft_copy": decision.get("edited_content", ""),
        "current_step": "review_complete",
    }


# ============================
#  路由函数
# ============================
def route_compliance(state: AgentState) -> str:
    step = state.get("current_step", "")
    if step == "compliance_failed":
        return "research"
    return "human_review"


def route_after_review(state: AgentState) -> str:
    action = state.get("human_action", "")
    if action == "approve":
        # 如果用户手动改了字，把编辑版本设为最终稿
        if state.get("edited_draft_copy"):
            return END
        return END

    # revise：回流到撰写节点
    state["is_revision"] = True
    state["revision_count"] = state.get("revision_count", 0) + 1
    return "write"


# ============================
#  构建状态图
# ============================
def build_graph(checkpointer=None):
    builder = StateGraph(AgentState)

    builder.add_node("research", research_node)
    builder.add_node("write", write_node)
    builder.add_node("compliance", compliance_node)
    builder.add_node("human_review", human_review_node)

    builder.add_edge(START, "research")
    builder.add_edge("research", "write")
    builder.add_edge("write", "compliance")

    builder.add_conditional_edges("compliance", route_compliance, {
        "research": "research",
        "human_review": "human_review",
    })

    builder.add_conditional_edges("human_review", route_after_review, {
        "write": "write",
        END: END,
    })

    return builder.compile(checkpointer=checkpointer)

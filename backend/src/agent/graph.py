"""LangGraph 状态机 — 10 节点完整拓扑

对齐 IMPLEMENTATION_PLAN §4 流程图 + §4.2 条件边表格

拓扑:
    START → init_task → crawl_trends → load_assets → generate_copy
       → generate_visuals → compliance ──[pass/mild]→ human_review(interrupt)
                                      └──[severe & <3]→ generate_copy
                                      └──[severe & >=3]→ END
       human_review → handle_feedback ──[approve]→ finalize → END
                                      └──[revise]→ extract_rules → generate_copy (loop)

SqliteSaver: 替换 Phase 1 MemorySaver，checkpoint 持久化到 SQLite
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from src.agent.state import AgentState
from src.agent.nodes.compliance import compliance_node
from src.agent.nodes.crawl_trends import crawl_trends_node
from src.agent.nodes.extract_rules import extract_rules_node
from src.agent.nodes.finalize import finalize_node
from src.agent.nodes.generate_copy import generate_copy_node
from src.agent.nodes.generate_visuals import generate_visuals_node
from src.agent.nodes.handle_feedback import handle_feedback_node
from src.agent.nodes.human_review import human_review_node
from src.agent.nodes.init_task import init_task_node
from src.agent.nodes.load_assets import load_assets_node


# ============================
#  条件路由函数（纯函数，不修改 state）
# ============================
def route_compliance(state: AgentState) -> str:
    severity = state.get("compliance_severity", "pass")

    if severity in ("pass", "mild_warning"):
        return "human_review"

    # severe_violation
    if state.get("violation_count", 0) >= 3:
        return END
    return "generate_copy"


def route_handle_feedback(state: AgentState) -> str:
    step = state.get("current_step", "")

    if step == "handle_feedback_approve":
        return "finalize"
    return "extract_rules"


# ============================
#  图构建
# ============================
def build_graph(checkpointer=None):
    """构建 10 节点完整拓扑。

    参数:
        checkpointer: AsyncSqliteSaver 实例或 None。
                      生产环境通过 create_checkpointer() 创建后传入。
                      测试环境通过 AsyncSqliteSaver.from_conn_string() 传入。
    """
    builder = StateGraph(AgentState)

    # —— 注册全部 10 个节点 ——
    builder.add_node("init_task", init_task_node)
    builder.add_node("crawl_trends", crawl_trends_node)
    builder.add_node("load_assets", load_assets_node)
    builder.add_node("generate_copy", generate_copy_node)
    builder.add_node("generate_visuals", generate_visuals_node)
    builder.add_node("compliance", compliance_node)
    builder.add_node("human_review", human_review_node)
    builder.add_node("handle_feedback", handle_feedback_node)
    builder.add_node("extract_rules", extract_rules_node)
    builder.add_node("finalize", finalize_node)

    # —— 线性边（主路径） ——
    builder.add_edge(START, "init_task")
    builder.add_edge("init_task", "crawl_trends")
    builder.add_edge("crawl_trends", "load_assets")
    builder.add_edge("load_assets", "generate_copy")
    builder.add_edge("generate_copy", "generate_visuals")
    builder.add_edge("generate_visuals", "compliance")

    # —— 条件边：compliance 三分支 ——
    builder.add_conditional_edges(
        "compliance",
        route_compliance,
        {
            "human_review": "human_review",
            "generate_copy": "generate_copy",
            END: END,
        },
    )

    # —— 线性边：human_review → handle_feedback ——
    builder.add_edge("human_review", "handle_feedback")

    # —— 条件边：handle_feedback 两分支 ——
    builder.add_conditional_edges(
        "handle_feedback",
        route_handle_feedback,
        {
            "finalize": "finalize",
            "extract_rules": "extract_rules",
        },
    )

    # —— 尾部边 ——
    builder.add_edge("extract_rules", "generate_copy")  # revise → 重写循环
    builder.add_edge("finalize", END)

    return builder.compile(checkpointer=checkpointer)

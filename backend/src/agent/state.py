"""小红书品牌运营 Agent 全局状态 — 对齐 PRD §5 & §6.4"""

from __future__ import annotations

from typing import TypedDict
from uuid import uuid4


# ============================
# 子结构体
# ============================
class TopicCard(TypedDict):
    """选题卡片 — PRD §5 topic_cards 元素"""
    title: str
    reason: str
    heat_index: int              # 0-100 热度指数
    estimated_traffic: str


class FeedbackRecord(TypedDict):
    """单轮反馈记录 — PRD §5 feedback_history 元素"""
    round: int
    feedback: str


class VisualGuidance(TypedDict):
    """视觉策划 — PRD §5 visual_guidance 字段"""
    cover_suggestion: str
    shot_descriptions: list[str]          # 3-4 条分镜描述
    domestic_image_prompts: list[str]     # 2-3 个国产模型 prompt


# ============================
# AgentState 主结构体
# ============================
class AgentState(TypedDict, total=False):
    """LangGraph Agent 全局状态 — 完整字段矩阵对齐 PRD §6.4"""

    # ---- 基础标识 ----
    user_input: str
    thread_id: str

    # ---- 选题数据 ----
    topic_cards: list[TopicCard]

    # ---- 过程产物 ----
    draft_copy: str
    visual_guidance: VisualGuidance
    is_revision: bool

    # ---- 人类交互 ----
    human_feedback: str
    edited_draft_copy: str
    feedback_action: str            # "approve" | "revise"
    feedback_history: list[FeedbackRecord]
    draft_versions: list[str]       # 各轮 draft_copy 快照

    # ---- 审核追踪 ----
    revision_count: int
    final_copy: str

    # ---- 品牌资产上下文（Pinned，不可压缩）----
    brand_context: str
    product_context: str
    best_practices: str
    negative_prompts: str

    # ---- 过程上下文（节点间传递）----
    trends_context: str
    compliance_severity: str        # "pass" | "mild_warning" | "severe_violation"
    violation_count: int

    # ---- 系统追踪 ----
    current_step: str
    error_logs: list[str]


# ============================
# 工厂函数
# ============================
def create_initial_state(
    user_input: str,
    *,
    topic_cards: list[TopicCard] | None = None,
) -> AgentState:
    """创建初始 AgentState，填充所有必需默认值"""
    initial: AgentState = {
        "user_input": user_input,
        "thread_id": str(uuid4()),
        "topic_cards": topic_cards or [],
        "draft_copy": "",
        "visual_guidance": VisualGuidance(
            cover_suggestion="",
            shot_descriptions=[],
            domestic_image_prompts=[],
        ),
        "is_revision": False,
        "human_feedback": "",
        "edited_draft_copy": "",
        "feedback_action": "",
        "feedback_history": [],
        "draft_versions": [],
        "revision_count": 0,
        "final_copy": "",
        "brand_context": "",
        "product_context": "",
        "best_practices": "",
        "negative_prompts": "",
        "trends_context": "",
        "compliance_severity": "pass",
        "violation_count": 0,
        "current_step": "init",
        "error_logs": [],
    }
    return initial


# ============================
# 不可变更新辅助
# ============================
def update_state(state: AgentState, **kwargs: object) -> AgentState:
    """返回一个新的 AgentState dict，用 kwargs 覆盖指定字段。

    原 state 不受影响（符合 immutability 规范）。
    """
    new: AgentState = dict(state)  # type: ignore[arg-type]
    for key, value in kwargs.items():
        if key not in AgentState.__annotations__:
            raise TypeError(f"Unknown AgentState field: {key}")
        new[key] = value  # type: ignore[literal-required]
    return new

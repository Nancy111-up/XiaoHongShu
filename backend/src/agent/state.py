from __future__ import annotations

from typing import TypedDict


class AgentState(TypedDict, total=False):
    """小红书品牌运营 Agent 全局状态"""

    # ---- 基础标识 ----
    user_input: str
    thread_id: str

    # ---- 过程产物 ----
    generated_topics: list[str]
    draft_copy: str
    is_revision: bool

    # ---- 人类审核判决 ----
    human_action: str          # "approve" | "revise"
    human_feedback: str        # 文字反馈
    edited_draft_copy: str     # 手动修改后的内容

    # ---- 品牌资产（Pinned，永不压缩）----
    brand_context: str
    product_context: str

    # ---- 系统追踪 ----
    current_step: str
    revision_count: int
    error_logs: list[str]

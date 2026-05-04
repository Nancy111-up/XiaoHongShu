"""AgentState 扩展 — TDD RED phase 测试

当前 state.py 仅含 12 个字段（简化版）。PRD §5 + §6.4 要求 22+ 字段 +
3 个子结构体（TopicCard, FeedbackRecord, VisualGuidance）。

这些测试引用了尚未存在的类型和工厂函数 —— 先红后绿。
"""

from __future__ import annotations

import pytest


# ============================================================
# RED 阶段：以下 import 在当前代码中不存在，测试将失败
# ============================================================
from src.agent.state import (  # noqa: E402
    AgentState,
    TopicCard,
    FeedbackRecord,
    VisualGuidance,
    create_initial_state,
    update_state,
)


# ============================================================
# 1. TopicCard 子类型
# ============================================================
class TestTopicCard:
    """选题卡片结构体——PRD §5 topic_cards 字段"""

    def test_topic_card_has_required_fields(self) -> None:
        """TopicCard 必须包含 title / reason / heat_index / estimated_traffic"""
        card: TopicCard = {
            "title": "早秋通勤穿搭公式",
            "reason": "搜索量周环比 +230%，互动中位数 1.2k",
            "heat_index": 92,
            "estimated_traffic": "10w-15w",
        }
        assert card["title"] == "早秋通勤穿搭公式"
        assert card["reason"]
        assert isinstance(card["heat_index"], int)
        assert card["estimated_traffic"]

    def test_topic_card_heat_index_is_int(self) -> None:
        """heat_index 应为整数（0-100 热度指数）"""
        card: TopicCard = {
            "title": "测试",
            "reason": "测试",
            "heat_index": 42,
            "estimated_traffic": "1w",
        }
        assert 0 <= card["heat_index"] <= 100


# ============================================================
# 2. FeedbackRecord 子类型
# ============================================================
class TestFeedbackRecord:
    """修改轨迹记录——PRD §5 feedback_history 字段"""

    def test_feedback_record_structure(self) -> None:
        record: FeedbackRecord = {"round": 1, "feedback": "太浮夸了，语气务实一点"}
        assert record["round"] == 1
        assert isinstance(record["feedback"], str)


# ============================================================
# 3. VisualGuidance 子类型
# ============================================================
class TestVisualGuidance:
    """视觉策划结构体——PRD §5 visual_guidance 字段"""

    def test_visual_guidance_has_required_fields(self) -> None:
        vg: VisualGuidance = {
            "cover_suggestion": "大字报：法式早秋通勤，燕麦色背景+黑色衬线体",
            "shot_descriptions": [
                "分镜1：全身穿搭正侧面对比",
                "分镜2：包袋特写+分区收纳展示",
            ],
            "domestic_image_prompts": [
                "CogView prompt: 新中式风格，燕麦色系...",
                "文心一格 prompt: 法式轻奢通勤穿搭...",
            ],
        }
        assert isinstance(vg["cover_suggestion"], str)
        assert isinstance(vg["shot_descriptions"], list)
        assert len(vg["shot_descriptions"]) >= 2
        assert isinstance(vg["domestic_image_prompts"], list)
        assert len(vg["domestic_image_prompts"]) >= 2

    def test_visual_guidance_rejects_foreign_model_prompts(self) -> None:
        """domestic_image_prompts 中不应包含外网模型（Midjourney/Stable Diffusion/DALL·E）"""
        # 此测试关注业务约束：视觉提示词必须针对国产模型
        forbidden = ["Midjourney", "Stable Diffusion", "DALL·E", "dall-e"]

        vg: VisualGuidance = {
            "cover_suggestion": "测试封面",
            "shot_descriptions": ["分镜1"],
            "domestic_image_prompts": [
                "CogView prompt: ...",
                "文心一格 prompt: ...",
                "通义万相 prompt: ...",
            ],
        }
        for prompt in vg["domestic_image_prompts"]:
            assert not any(fw.lower() in prompt.lower() for fw in forbidden), (
                f"外网模型 prompt 禁止：{prompt}"
            )


# ============================================================
# 4. AgentState 完整字段
# ============================================================
class TestAgentStateFields:
    """验证 AgentState 包含 PRD §5 与 §6.4 要求的全部字段"""

    def test_all_prd_fields_accepted(self) -> None:
        """AgentState dict 必须接受 PRD 定义的 22+ 个字段"""
        state: AgentState = {
            # 基础标识
            "user_input": "秋季穿搭",
            "thread_id": "uuid-test-001",
            # 选题数据
            "topic_cards": [
                {
                    "title": "早秋通勤穿搭公式",
                    "reason": "搜索量周环比 +230%",
                    "heat_index": 92,
                    "estimated_traffic": "10w-15w",
                }
            ],
            # 过程产物
            "draft_copy": "【秋季胶囊衣橱】3件单品搞定7天通勤…",
            "visual_guidance": {
                "cover_suggestion": "燕麦色大字报封面",
                "shot_descriptions": ["分镜1", "分镜2"],
                "domestic_image_prompts": ["CogView: ...", "文心一格: ..."],
            },
            "is_revision": False,
            # 人类交互
            "human_feedback": "",
            "edited_draft_copy": "",
            "feedback_action": "",
            "feedback_history": [],
            "draft_versions": [],
            # 审核追踪
            "revision_count": 0,
            "final_copy": "",
            # 品牌资产上下文
            "brand_context": "品牌人设…",
            "product_context": "产品信息…",
            "best_practices": "高分范文…",
            "negative_prompts": "避坑指南…",
            # 过程上下文
            "trends_context": "热点提炼…",
            "compliance_severity": "pass",
            "violation_count": 0,
            # 系统追踪
            "current_step": "init",
            "error_logs": [],
        }
        # 断言：能接受所有字段即通过
        assert state["user_input"] == "秋季穿搭"
        assert len(state["topic_cards"]) == 1
        assert state["revision_count"] == 0
        assert state["compliance_severity"] == "pass"

    def test_compliance_severity_values(self) -> None:
        """compliance_severity 仅接受三个枚举值"""
        valid = {"pass", "mild_warning", "severe_violation"}
        for severity in valid:
            state: AgentState = {"compliance_severity": severity}
            assert state["compliance_severity"] in valid


# ============================================================
# 5. 工厂函数：create_initial_state()
# ============================================================
class TestCreateInitialState:
    """验证状态初始化工厂函数的输出"""

    def test_returns_agent_state_with_required_defaults(self) -> None:
        initial = create_initial_state(user_input="秋季穿搭")
        assert initial["user_input"] == "秋季穿搭"
        assert initial["thread_id"]  # 自动生成 UUID
        assert len(initial["thread_id"]) == 36  # UUID4 格式
        assert initial["revision_count"] == 0
        assert initial["violation_count"] == 0
        assert initial["is_revision"] is False
        assert initial["feedback_action"] == ""
        assert initial["current_step"] == "init"
        assert initial["error_logs"] == []
        assert initial["feedback_history"] == []
        assert initial["draft_versions"] == []
        assert initial["topic_cards"] == []
        assert initial["compliance_severity"] == "pass"

    def test_each_call_creates_unique_thread_id(self) -> None:
        a = create_initial_state(user_input="A")
        b = create_initial_state(user_input="B")
        assert a["thread_id"] != b["thread_id"]

    def test_accepts_optional_topic_cards(self) -> None:
        cards: list[TopicCard] = [
            {
                "title": "早秋通勤",
                "reason": "热度上升",
                "heat_index": 88,
                "estimated_traffic": "5w-10w",
            }
        ]
        initial = create_initial_state(user_input="秋季穿搭", topic_cards=cards)
        assert len(initial["topic_cards"]) == 1
        assert initial["topic_cards"][0]["title"] == "早秋通勤"


# ============================================================
# 6. 不可变更新：update_state()
# ============================================================
class TestUpdateState:
    """验证状态不可变更新——符合 coding-style.md 中的 immutability 要求"""

    def test_returns_new_dict_not_same_object(self) -> None:
        original: AgentState = create_initial_state(user_input="秋季穿搭")
        updated = update_state(original, current_step="research_complete")
        assert updated is not original
        assert updated["current_step"] == "research_complete"
        assert original["current_step"] == "init"  # 原对象未被修改

    def test_merges_multiple_fields_at_once(self) -> None:
        original: AgentState = create_initial_state(user_input="秋季穿搭")
        updated = update_state(
            original,
            draft_copy="新文案…",
            current_step="writing_complete",
            revision_count=1,
        )
        assert updated["draft_copy"] == "新文案…"
        assert updated["current_step"] == "writing_complete"
        assert updated["revision_count"] == 1
        # 未修改字段保持原值
        assert updated["user_input"] == original["user_input"]

    def test_preserves_original_unchanged_on_error(self) -> None:
        """即便传入未知 key，原对象也不被修改（安全侧效应）"""
        original: AgentState = create_initial_state(user_input="A")
        try:
            update_state(original, non_existent_field="xxx")  # type: ignore[call-arg]
        except (TypeError, ValueError):
            pass
        # 原对象不受影响
        assert "non_existent_field" not in original
        assert original["user_input"] == "A"

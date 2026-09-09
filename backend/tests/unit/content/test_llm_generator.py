from types import SimpleNamespace

import pytest

from src.content.generator import LLMContentGenerator
from src.llm.schemas import FullCopy


class FakeLLM:
    async def generate_full_copy(self, **context):
        assert context["job_id"] == "job-1"
        assert context["topic_id"] == "topic-1"
        return FullCopy(
            title="夜跑装备这样选",
            body="从真实趋势证据出发，说明夜跑装备的选择方法。",
            hashtags=["夜跑", "跑步装备"],
            evidence_note_ids=[],
            evidence_comment_ids=[],
        )


@pytest.mark.asyncio
async def test_full_copy_maps_to_persistable_draft_contract() -> None:
    opportunity = SimpleNamespace(
        job_id="job-1",
        topic_id="topic-1",
        title="夜跑装备",
        reasons_json='{"why_now":"热度正在上升"}',
        copy_preview_json='{"call_to_action":"分享你的夜跑路线"}',
    )

    draft = await LLMContentGenerator(FakeLLM()).generate_full_copy(opportunity)

    assert draft.titles == [
        "夜跑装备这样选",
        "夜跑装备｜夜跑装备这样选",
        "夜跑装备这样选｜实用指南",
    ]
    assert draft.tags == ["夜跑", "跑步装备"]
    assert draft.cta == "分享你的夜跑路线"
    assert draft.prompt_version == "full_copy_v1"

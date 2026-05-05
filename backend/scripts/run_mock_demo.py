"""端到端验证脚本 —— 在本地演示 Agent 状态机的完整运转

用法:
    cd backend
    uv run python run_mock_demo.py
"""

from __future__ import annotations

import asyncio
import sys

from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from src.agent.graph import build_graph
from src.agent.state import create_initial_state

# Windows 控制台 GBK 编码补偿
sys.stdout.reconfigure(encoding="utf-8")


def _fmt_topic(item: str | dict) -> str:
    """兼容 Tavily str 与 TopicCard dict 两种格式"""
    if isinstance(item, dict):
        return item.get("title", str(item))
    return str(item)


async def main():
    checkpointer = MemorySaver()
    graph = build_graph(checkpointer=checkpointer)

    config = {"configurable": {"thread_id": "demo-001"}}

    # ── 第一轮：启动任务 ──
    initial = create_initial_state(user_input="秋季穿搭")
    initial["thread_id"] = "demo-001"  # 用固定 ID 方便调试

    print("=" * 60)
    print("▶ 第一轮：选题 → 撰写 → 风控 → 等待审核")
    print("=" * 60)

    state = await graph.ainvoke(initial, config)

    # ── 展示中断产物 ──
    step = state.get("current_step", "")
    print(f"\n当前状态: {step}")
    print("生成选题:")
    for t in state.get("topic_cards", []):
        print(f"  • {_fmt_topic(t)}")
    print(f"\n📝 初稿:\n{state.get('draft_copy', '')}")
    print(f"\n风控日志: {state.get('error_logs', [])}")
    print(f"\n⏸️ 状态: 等待人类审核...")

    # ── 第二轮：模拟人类「不满意，改稿」──
    feedback = Command(resume={
        "action": "revise",
        "feedback": "少用感叹号，语气再温柔一点",
    })

    print("\n" + "=" * 60)
    print("▶ 第二轮：人类反馈 → 回到撰写节点重写")
    print("=" * 60)

    state = await graph.ainvoke(feedback, config)

    step = state.get("current_step", "")
    print(f"\n当前状态: {step}")
    print(f"修改轮次: 第 {state.get('revision_count', 0)} 轮")
    print(f"\n📝 改后稿:\n{state.get('draft_copy', '')}")
    print(f"\n⏸️ 状态: 等待人类审核...")

    # ── 第三轮：模拟人类「手动改字 + 保存通过」──
    draft = state.get("draft_copy", "")
    approval = Command(resume={
        "action": "approve",
        "edited_content": draft.replace("一个被问了800遍的搭配公式", "秋季胶囊衣橱の万能公式") if "一个被问了800遍的搭配公式" in draft else draft,
    })

    print("\n" + "=" * 60)
    print("▶ 第三轮：人类手动改字 → 保存通过 → 结束")
    print("=" * 60)

    state = await graph.ainvoke(approval, config)

    print(f"\n最终状态: {state.get('current_step', '')}")
    print(f"人类操作: {state.get('feedback_action', '')}")
    if state.get("edited_draft_copy"):
        print(f"\n📝 最终定稿:\n{state['edited_draft_copy']}")

    print("\n✅ 状态机跑通：搜索 → 撰写 → 风控 → 审核 → 改稿 → 再审核 → 保存通过")


if __name__ == "__main__":
    asyncio.run(main())

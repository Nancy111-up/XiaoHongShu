"""品牌撰写节点 —— 结合选题 + 品牌资产 + 产品信息，调用 LLM 生成小红书文案"""

from __future__ import annotations

from src.agent.state import AgentState
from src.agent.tools.llm_client import chat_completion
from src.services.asset_loader import load_asset


def _build_system_prompt() -> str:
    brand = load_asset("brand_voice.md")
    product = load_asset("product_info.md")
    negative = load_asset("negative_prompts.md")

    return f"""你是小红书文案写手，严格遵守以下品牌规范。

# 品牌人设 & 口癖
{brand}

# 产品信息
{product}

# 避坑指南
{negative}

# 输出格式要求
- 标题：用「」或【】包裹，不超过15字
- 正文：3-4个短段落，每段不超过3行，行间用 --- 分隔
- 结尾：3-5个#标签
- 产品植入：放在最后1/3处，用「最近上架」「新到」等弱营销词引入
- 直接输出最终文案，不要加任何前缀说明"""


def _build_user_prompt(state: AgentState) -> str:
    topics = state.get("generated_topics", [])
    user_input = state["user_input"]
    feedback = state.get("human_feedback", "")

    if state.get("is_revision") and feedback:
        return f"""以下文案需要根据反馈修改：

【原文案】
{state["draft_copy"]}

【修改意见】
{feedback}

请重写这篇小红书文案，保持品牌调性不变，针对意见做出调整。"""

    topic_list = "\n".join(f"- {t}" for t in topics) if topics else f"- {user_input}相关趋势"

    return f"""根据以下热点选题，撰写一篇小红书带货文案：

【选题灵感】
{topic_list}

【用户搜索主题】
{user_input}

请基于选题灵感中与你品牌调性最匹配的角度来写。"""


async def write_node(state: AgentState) -> dict:
    brand_context = state.get("brand_context") or load_asset("brand_voice.md")
    product_context = state.get("product_context") or load_asset("product_info.md")
    is_revision = state.get("is_revision", False)

    messages = [
        {"role": "system", "content": _build_system_prompt()},
        {"role": "user", "content": _build_user_prompt(state)},
    ]

    draft = await chat_completion(messages)
    step = "revision_complete" if is_revision else "writing_complete"

    return {
        "draft_copy": draft,
        "brand_context": brand_context,
        "product_context": product_context,
        "current_step": step,
    }

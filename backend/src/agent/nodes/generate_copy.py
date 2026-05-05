"""generate_copy 节点 —— 主力 LLM 生成小红书文案（JSON 结构化输出）

对齐 IMPLEMENTATION_PLAN §4.1 节点 4

增强（vs Phase 1 write.py）：
- 强制 JSON 结构化输出 {title, body, tags, ad_placement}
- is_revision=True 时跳过趋势上下文，基于 human_feedback 重写
- 解析后格式化为 readable draft_copy，JSON 解析失败 → 原始文本降级
- draft_versions 快照追加
"""

from __future__ import annotations

import json
import re

from src.agent.state import AgentState
from src.agent.tools.llm_client import chat_completion


def _topic_title(item: str | dict) -> str:
    if isinstance(item, dict):
        return item.get("title", str(item))
    return str(item)


def _build_system_prompt(state: AgentState) -> str:
    brand = state.get("brand_context", "")
    product = state.get("product_context", "")
    negative = state.get("negative_prompts", "")
    best = state.get("best_practices", "")

    return f"""你是小红书文案写手，严格遵守以下品牌规范，输出 JSON 结构化文案。

# 品牌人设 & 口癖
{brand}

# 产品信息
{product}

# 范文结构参考
{best}

# 避坑指南
{negative}

# 输出格式（必须严格输出 JSON）
{{
  "title": "用「」或【】包裹的标题，不超过15字",
  "body": "3-4个短段落，每段不超过3行，段间用 --- 分隔。产品植入放在最后1/3处，用「最近上架」「新到」等弱营销词引入",
  "tags": ["标签1", "标签2", "标签3", "标签4"],
  "ad_placement": "产品自然植入的具体位置和话术"
}}

只输出 JSON，不要加任何前缀、说明或 markdown 代码块。"""


def _build_user_prompt(state: AgentState) -> str:
    topic_cards = state.get("topic_cards", [])
    user_input = state["user_input"]
    trends = state.get("trends_context", "")
    feedback = state.get("human_feedback", "")

    if state.get("is_revision") and feedback:
        return f"""以下文案需要根据反馈修改：

【原文案】
{state["draft_copy"]}

【修改意见】
{feedback}

请重写这篇小红书文案，保持品牌调性不变，针对意见做出调整。输出 JSON。"""

    topic_list = "\n".join(
        f"- {_topic_title(c)}" for c in topic_cards
    ) if topic_cards else f"- {user_input}相关趋势"

    trend_block = f"【趋势参考】\n{trends}" if trends else ""

    return f"""根据以下信息撰写小红书带货文案：

{trend_block}
【选题灵感】
{topic_list}

【用户搜索主题】
{user_input}

请基于选题灵感中与你品牌调性最匹配的角度来写。输出 JSON。"""


def _parse_json_output(raw: str) -> dict | None:
    """3 层 JSON 提取 + 字段校验"""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"```(?:json)?\s*(.*?)\n?```", raw, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group(1))
            except json.JSONDecodeError:
                return None
        else:
            m = re.search(r"\{.*\}", raw, re.DOTALL)
            if m:
                try:
                    data = json.loads(m.group(0))
                except json.JSONDecodeError:
                    return None
            else:
                return None

    if not isinstance(data, dict):
        return None
    if "title" not in data and "body" not in data:
        return None

    return {
        "title": str(data.get("title", "")),
        "body": str(data.get("body", "")),
        "tags": [str(t) for t in data.get("tags", [])] if isinstance(data.get("tags"), list) else [],
        "ad_placement": str(data.get("ad_placement", "")),
    }


def _format_draft(parsed: dict) -> str:
    """将结构化 JSON 格式化为小红书可读文案"""
    title = parsed["title"]
    body = parsed["body"]
    tags = parsed["tags"]

    parts = [title, "", body]
    if tags:
        parts.append("")
        parts.append(" ".join(f"#{t}" for t in tags))

    return "\n".join(parts)


async def generate_copy_node(state: AgentState) -> dict:
    is_revision = state.get("is_revision", False)

    messages = [
        {"role": "system", "content": _build_system_prompt(state)},
        {"role": "user", "content": _build_user_prompt(state)},
    ]

    try:
        raw = await chat_completion(
            messages,
            model="qwen-plus",
            temperature=0.7,
            max_tokens=1024,
        )
    except Exception as e:
        return {
            "draft_copy": state.get("draft_copy", ""),
            "current_step": "generate_copy_failed",
            "error_logs": [f"generate_copy LLM 调用失败: {type(e).__name__}: {e}"],
        }

    parsed = _parse_json_output(raw)

    if parsed is None:
        # JSON 解析失败 → 降级，使用原始输出
        fallback_draft = raw.strip() or state.get("draft_copy", "")
        return {
            "draft_copy": fallback_draft,
            "current_step": "generate_copy_complete",
            "error_logs": ["generate_copy JSON 解析失败，使用原始文本降级"],
        }

    draft = _format_draft(parsed)

    step = "generate_copy_revision" if is_revision else "generate_copy_complete"

    return {
        "draft_copy": draft,
        "current_step": step,
        "error_logs": [],
    }

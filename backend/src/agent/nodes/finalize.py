"""finalize 节点 —— 资产进化 + Token 瘦身

对齐 IMPLEMENTATION_PLAN §4.1 节点 10

行为：
1. revision_count == 0（一稿过）→ 提取范文结构 → 追加 best_practices.md
2. revision_count > 3（高轮次）→ 深层反思失败模式 → 追加 negative_prompts.md
3. 品牌资产 Token 总量 > 8000 → error_logs 标记 needs_trimming

不阻断 Graph，所有异常静默降级。
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone

from src.agent.state import AgentState
from src.agent.tools.llm_client import chat_completion
from src.services.asset_loader import append_to_asset

_TOKEN_THRESHOLD = 8000

_BEST_PRACTICE_PROMPT = """你是品牌内容策略师。以下文案一稿通过审核，请从中提取可复用的结构模式。

提取要求：
1. 标题公式（1-2种）
2. 段落结构模式
3. 植入话术亮点
4. 标签策略

输出格式：
{
  "patterns": "提炼的结构模式文本（100字以内，用中文）"
}

只输出JSON。"""

_REFLECTION_PROMPT = """你是品牌内容策略师。以下文案经过多轮修改才通过审核。请从修改过程中提炼教训。

根据反馈历史和当前文案，提取：
1. 反复出现的问题类型
2. 应该加入避坑指南的规则

输出格式：
{
  "lesson": "提炼的教训/规则文本（80字以内，用中文）"
}

只输出JSON。"""


def _estimate_tokens(text: str) -> int:
    """粗略估算 Token 数：中文每字 ~1 token，英文每词 ~1.3 token"""
    # 简单估算：字符数 / 1.5（混合中英文）
    return max(1, len(text) // 1.5)


def _estimate_state_tokens(state: AgentState) -> int:
    fields = [
        state.get("brand_context", ""),
        state.get("product_context", ""),
        state.get("best_practices", ""),
        state.get("negative_prompts", ""),
        state.get("trends_context", ""),
        state.get("draft_copy", ""),
        state.get("final_copy", ""),
    ]
    return sum(_estimate_tokens(f) for f in fields)


def _extract_json(raw: str) -> dict | None:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{[^}]+\}", raw)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
    return None


async def finalize_node(state: AgentState) -> dict:
    revision_count = state.get("revision_count", 0)
    final_copy = state.get("final_copy") or state.get("draft_copy", "")
    error_logs: list[str] = []
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # 一稿过 → 提取范文结构 → best_practices.md
    if revision_count == 0 and final_copy:
        try:
            raw = await chat_completion(
                [
                    {"role": "system", "content": "你是内容策略师，只输出指定JSON。"},
                    {"role": "user", "content": f"{_BEST_PRACTICE_PROMPT}\n\n# 一稿过文案\n{final_copy}"},
                ],
                model="qwen-turbo",
                temperature=0.3,
                max_tokens=256,
            )
            data = _extract_json(raw)
            if data and data.get("patterns"):
                entry = f"\n<!-- {timestamp} auto-extracted from one-shot success -->\n- {data['patterns']}\n"
                append_to_asset("best_practices.md", entry)
        except Exception as e:
            error_logs.append(f"finalize 一稿过提取失败: {type(e).__name__}: {e}")

    # 高轮次 → 深层反思 → negative_prompts.md
    if revision_count > 3 and final_copy:
        feedback_history = state.get("feedback_history", [])
        history_text = ""
        if feedback_history:
            history_text = "\n".join(
                f"第{f.get('round', '?')}轮: {f.get('feedback', '')}"
                for f in feedback_history[-5:]  # 最近 5 轮
            )

        try:
            raw = await chat_completion(
                [
                    {"role": "system", "content": "你是内容策略师，只输出指定JSON。"},
                    {"role": "user", "content": (
                        f"{_REFLECTION_PROMPT}\n\n"
                        f"# 修改历史\n{history_text}\n\n"
                        f"# 最终文案\n{final_copy}"
                    )},
                ],
                model="qwen-turbo",
                temperature=0.3,
                max_tokens=256,
            )
            data = _extract_json(raw)
            if data and data.get("lesson"):
                entry = f"\n<!-- {timestamp} auto-extracted from {revision_count}-round revision -->\n- {data['lesson']}\n"
                append_to_asset("negative_prompts.md", entry)
        except Exception as e:
            error_logs.append(f"finalize 高轮次反思失败: {type(e).__name__}: {e}")

    # Token 瘦身检测
    estimated_tokens = _estimate_state_tokens(state)
    if estimated_tokens > _TOKEN_THRESHOLD:
        error_logs.append(
            f"品牌资产 Token 超限: 预估 {estimated_tokens} > {_TOKEN_THRESHOLD}，触发瘦身标记"
        )

    return {
        "current_step": "finalize_complete",
        "error_logs": error_logs,
    }

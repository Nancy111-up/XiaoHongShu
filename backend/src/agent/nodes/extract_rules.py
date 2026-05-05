"""extract_rules 节点 —— 从人类反馈中提取通用规则，写入品牌资产

对齐 IMPLEMENTATION_PLAN §4.1 节点 9

行为：
1. 用 Qwen-Turbo 判定 human_feedback 是否包含可泛化的通用规则
2. 是 → 追加写入 negative_prompts.md（带时间戳注释）
3. 否 → 丢弃（NOT_A_RULE），不修改资产文件
4. 写入失败不阻断 Graph，记录 error_logs

判定标准：
- 规则类：禁止某种写法/用词/调性 → 写入
- 一次性：针对当前文案的具体措辞修改 → 丢弃
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone

from src.agent.state import AgentState
from src.agent.tools.llm_client import chat_completion
from src.services.asset_loader import append_to_asset


_RULE_CLASSIFIER_PROMPT = """你是品牌内容规则提取器。判断以下人类反馈是否包含可以泛化为"品牌避坑规则"的内容。

# 泛化规则（应提取）示例：
- "不要使用'必入''必买'这类营销词" → RULE
- "避免在文案中提到任何竞品品牌名" → RULE
- "标题必须控制在15字以内" → RULE
- "产品描述不要用'奢华'，用'质感'替代" → RULE

# 一次性修改（应丢弃）示例：
- "把第二段的'很好看'改成'很百搭'" → NOT_A_RULE
- "这篇的标题换成'通勤必备'" → NOT_A_RULE
- "第三段太长了，拆分一下" → NOT_A_RULE
- "配图建议用浅色背景" → NOT_A_RULE

请严格输出以下JSON，不要加任何前缀或说明：
{"is_rule": true|false, "rule_text": "提炼后的规则文本（仅 is_rule=true 时填写）"}"""


async def extract_rules_node(state: AgentState) -> dict:
    feedback = state.get("human_feedback", "")

    if not feedback:
        return {
            "current_step": "extract_rules_skip",
            "error_logs": [],
        }

    # 调用小模型判定
    try:
        raw = await chat_completion(
            [
                {"role": "system", "content": "你是一个精确的文本分类器，只输出指定JSON，不加解释。"},
                {"role": "user", "content": f"{_RULE_CLASSIFIER_PROMPT}\n\n# 待判定反馈\n{feedback}"},
            ],
            model="qwen-turbo",
            temperature=0.0,
            max_tokens=256,
        )
    except Exception as e:
        return {
            "current_step": "extract_rules_complete",
            "error_logs": [f"extract_rules LLM 调用失败: {type(e).__name__}: {e}"],
        }

    # 解析 JSON
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{[^}]+\}", raw)
        if m:
            try:
                data = json.loads(m.group(0))
            except json.JSONDecodeError:
                return {"current_step": "extract_rules_complete", "error_logs": []}
        else:
            return {"current_step": "extract_rules_complete", "error_logs": []}

    is_rule = data.get("is_rule", False)
    if not is_rule:
        return {
            "current_step": "extract_rules_complete",
            "error_logs": [],
        }

    rule_text = str(data.get("rule_text", "")).strip()
    if not rule_text:
        return {
            "current_step": "extract_rules_complete",
            "error_logs": [],
        }

    # 写入 negative_prompts.md
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    entry = f"\n<!-- {timestamp} auto-extracted from human feedback -->\n- {rule_text}\n"

    try:
        append_to_asset("negative_prompts.md", entry)
    except Exception as e:
        return {
            "current_step": "extract_rules_complete",
            "error_logs": [f"extract_rules 写入资产失败: {type(e).__name__}: {e}"],
        }

    return {
        "current_step": "extract_rules_complete",
        "error_logs": [],
    }

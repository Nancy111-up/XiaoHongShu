"""风控校验节点 —— 双层审核机制

对齐 IMPLEMENTATION_PLAN §4.1 节点 6

第一层：config.toml [compliance] 敏感词词典匹配（快速预筛）
第二层：LLM 二次判定 → pass / mild_warning / severe_violation
        - pass: 内容安全，进入 human_review
        - mild_warning: 轻微问题，进入 human_review（附带提醒）
        - severe_violation: 严重违规，回流 generate_copy 重写
          · 累计 >= 3 次 → 图路由至 END（由 graph.py 条件边处理）

行为：
- LLM 调用失败 → 退回 Layer 1 结果（有命中 = severe，无命中 = pass）
- 违规不计入 revision_count（revision_count 仅跟踪人类反馈轮次）
"""

from __future__ import annotations

import asyncio
import json

from src.agent.state import AgentState
from src.agent.tools.llm_client import chat_completion
from src.agent.tools.sensitive_words import check_sensitive
from src.config import get_settings


def _build_compliance_prompt(draft: str, visual: str, hits: list[str]) -> str:
    return f"""你是小红书平台内容安全审核员。审查以下内容是否存在违规风险。

# 审查维度
1. **虚假/夸大宣传**：使用「第一」「最」「全网」「绝对」等极限词，或对功效做无依据承诺
2. **竞品贬低**：点名或暗示竞品品牌劣势
3. **敏感话题**：涉及政治、医疗断言、金融诱导、色情低俗
4. **平台违禁**：导流外站、诱导私下交易、虚假营销话术
5. **品牌调性偏离**：与法式轻奢/简约高级的品牌定位严重不符

# 内容
【文案草稿】
{draft or "（无）"}

【视觉策划】
{visual or "（无）"}

# 第一层敏感词命中
{", ".join(hits) if hits else "（无命中）"}

请严格输出以下JSON，不要加任何前缀或说明：
{{"severity": "pass|mild_warning|severe_violation", "reason": "一句话理由"}}

判定标准：
- pass: 内容安全，无任何违规
- mild_warning: 存在轻微夸大或措辞不当，可修改后发布
- severe_violation: 存在明确违规（极限词、竞品贬低、敏感话题、导流外站）"""


async def _llm_compliance_review(
    draft: str,
    visual_guidance: dict,
    hits: list[str],
) -> tuple[str, str]:
    """调用 LLM 二次判定。返回 (severity, reason)。"""
    visual_str = json.dumps(visual_guidance, ensure_ascii=False) if visual_guidance else ""

    messages = [
        {"role": "system", "content": "你是严格但公正的内容安全审核员。只输出指定JSON，不加解释。"},
        {"role": "user", "content": _build_compliance_prompt(draft, visual_str, hits)},
    ]

    raw = await chat_completion(
        messages,
        model="qwen-turbo",
        temperature=0.0,
        max_tokens=256,
    )

    # 提取 JSON
    import re
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{[^}]+\}", raw)
        if m:
            data = json.loads(m.group(0))
        else:
            return ("pass", "LLM 输出无法解析，默认放行")

    severity = str(data.get("severity", "pass")).lower().strip()
    reason = str(data.get("reason", ""))

    if severity not in ("pass", "mild_warning", "severe_violation"):
        severity = "pass"

    return severity, reason


async def compliance_node(state: AgentState) -> dict:
    draft = state.get("draft_copy", "")
    visual = state.get("visual_guidance", {})

    # 拼接审查文本
    check_text = draft
    if visual:
        visual_str = " ".join([
            visual.get("cover_suggestion", ""),
            *visual.get("shot_descriptions", []),
            *visual.get("domestic_image_prompts", []),
        ])
        check_text += " " + visual_str

    # Layer 1: 敏感词词典匹配
    await asyncio.sleep(0.1)
    hits = check_sensitive(check_text)

    error_logs: list[str] = []
    if hits:
        error_logs.append(f"Layer1 敏感词命中: {', '.join(hits)}")

    # Layer 2: LLM 二次判定（可通过 config.toml 关闭）
    if get_settings().llm_review_enabled:
        try:
            severity, reason = await _llm_compliance_review(draft, visual, hits)
        except Exception as e:
            severity = "severe_violation" if hits else "pass"
            reason = f"LLM 审核不可用，退回 Layer 1 判定: {e}"
            error_logs.append(f"Layer2 LLM 调用失败: {type(e).__name__}: {e}")
    else:
        severity = "severe_violation" if hits else "pass"
        reason = "LLM 审核已关闭，依 Layer 1 判定"

    if reason and severity != "pass":
        error_logs.append(f"Layer2 判定 [{severity}]: {reason}")

    # 违规计数
    violation_count = state.get("violation_count", 0)
    if severity == "severe_violation":
        violation_count += 1

    return {
        "compliance_severity": severity,
        "violation_count": violation_count,
        "current_step": f"compliance_{severity}",
        "error_logs": error_logs,
    }

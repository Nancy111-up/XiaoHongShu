"""generate_visuals 节点 —— 根据品牌调性和文案草稿生成视觉策划

对齐 IMPLEMENTATION_PLAN §4.1 节点 5

行为：
1. 基于 brand_context + product_context + draft_copy 生成 VisualGuidance JSON
2. 强制输出 3 个国产模型（通义万相 / 文心一格 / CogView）适配 prompt
3. 校验禁止输出 DALL-E / Midjourney / Stable Diffusion 等外网模型 prompt
4. LLM 调用失败 / JSON 解析失败 / 外网模型检测 → 降级为通用视觉建议
"""

from __future__ import annotations

import json
import re

from src.agent.state import AgentState, VisualGuidance
from src.agent.tools.llm_client import chat_completion

# 禁止出现的外网模型名称/模式（大小写不敏感）
_FOREIGN_MODEL_PATTERNS = [
    r"dall[\s\-]?e",
    r"midjourney",
    r"stable\s*diffusion",
    r"sdxl",
    r"imagen",
    r"adobe\s*firefly",
    r"leonardo\s*ai",
    r"playground\s*ai",
]

_FALLBACK_VISUAL: VisualGuidance = {
    "cover_suggestion": "法式简约风格封面，暖调燕麦底色，产品居中摆放，柔和侧光营造高级质感",
    "shot_descriptions": [
        "中景：产品置于大理石板，自然光从左侧打来，背景虚化呈现咖啡厅氛围",
        "特写：手持产品细节，皮质纹理清晰可见，配合柔和景深",
        "全景：都市女性通勤场景，产品自然融入日常穿搭，捕捉动态瞬间",
        "平铺：产品与同色系配饰（丝巾、墨镜）组合摆放，俯拍构图",
    ],
    "domestic_image_prompts": [
        "一只浅棕色真皮托特包，置于白色大理石桌面，自然柔光，高质感产品摄影，小红书风格",
        "都市女性手提简约通勤包走在梧桐树下，法式穿搭，柔焦背景，生活感氛围",
        "产品细节特写，五金件和皮质纹理，温暖自然光，极简构图，高级感",
    ],
}


def _build_system_prompt() -> str:
    return """你是小红书视觉策划专家。根据品牌调性、产品信息和文案草稿，输出一份完整的视觉策划方案。

要求：
1. 封面建议：1-2句话描述封面视觉方向
2. 分镜描述：3-4个拍摄分镜，每个描述场景、构图、光线
3. 国产模型提示词：为以下3个国产AI绘画模型各写一条中文prompt：
   - 通义万相（阿里 Tongyi Wanxiang）
   - 文心一格（百度 Wenxin Yige）
   - CogView（智谱清言 CogView）

你必须严格输出以下JSON格式，不要加任何前缀、说明或markdown代码块：
{
  "cover_suggestion": "...",
  "shot_descriptions": ["...", "...", "..."],
  "domestic_image_prompts": ["通义万相 prompt", "文心一格 prompt", "CogView prompt"]
}

注意：
- 所有prompt必须针对国产文生图模型优化（中文自然语言prompt、东方审美偏好）
- 禁止在prompt中出现任何外网模型名称（DALL-E、Midjourney、Stable Diffusion等）
- 分镜描述要具体，包含机位、景别、光线方向、氛围
- domestic_image_prompts 必须恰好3条，分别对应通义万相、文心一格、CogView"""


def _build_user_prompt(state: AgentState) -> str:
    brand = state.get("brand_context", "")
    product = state.get("product_context", "")
    best_practices = state.get("best_practices", "")
    draft = state.get("draft_copy", "")
    trends = state.get("trends_context", "")
    user_input = state["user_input"]

    return f"""请根据以下信息生成视觉策划：

# 品牌人设 & 调性
{brand or "（无品牌信息）"}

# 产品信息
{product or "（无产品信息）"}

# 范文结构参考
{best_practices or "（无范文参考）"}

# 文案草稿
{draft or "（尚未生成）"}

# 当前趋势
{trends or user_input}

请输出完整的视觉策划JSON。"""


def _validate_no_foreign_models(visual: VisualGuidance) -> list[str]:
    """扫描 visual_guidance 中是否包含外网模型名称。返回违规描述列表。"""
    violations: list[str] = []
    texts = [
        visual["cover_suggestion"],
        *visual["shot_descriptions"],
        *visual["domestic_image_prompts"],
    ]
    for text in texts:
        text_lower = text.lower()
        for pattern in _FOREIGN_MODEL_PATTERNS:
            if re.search(pattern, text_lower):
                violations.append(f"检测到外网模型引用: 匹配模式 '{pattern}'")
    return violations


def _parse_json_output(raw: str) -> VisualGuidance | None:
    """尝试从 LLM 原始输出中提取 JSON 并反序列化为 VisualGuidance"""
    # 尝试直接解析
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # 尝试提取 ```json ... ``` 代码块
        m = re.search(r"```(?:json)?\s*(.*?)\n?```", raw, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group(1))
            except json.JSONDecodeError:
                return None
        else:
            # 尝试找到第一个 { 到最后一个 }
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
    if "cover_suggestion" not in data and "shot_descriptions" not in data:
        return None

    cover = str(data.get("cover_suggestion", ""))
    shots = data.get("shot_descriptions", [])
    prompts = data.get("domestic_image_prompts", [])

    if not isinstance(shots, list):
        shots = []
    if not isinstance(prompts, list):
        prompts = []

    shots = [str(s) for s in shots[:5]]
    prompts = [str(p) for p in prompts[:4]]

    if not cover:
        cover = _FALLBACK_VISUAL["cover_suggestion"]
    if not shots:
        shots = _FALLBACK_VISUAL["shot_descriptions"]
    if not prompts:
        prompts = _FALLBACK_VISUAL["domestic_image_prompts"]

    return {
        "cover_suggestion": cover,
        "shot_descriptions": shots,
        "domestic_image_prompts": prompts,
    }


async def generate_visuals_node(state: AgentState) -> dict:
    messages = [
        {"role": "system", "content": _build_system_prompt()},
        {"role": "user", "content": _build_user_prompt(state)},
    ]

    try:
        raw = await chat_completion(
            messages,
            model="qwen-plus",
            temperature=0.5,
            max_tokens=1024,
        )
    except Exception as e:
        return {
            "visual_guidance": _FALLBACK_VISUAL,
            "current_step": "generate_visuals_complete",
            "error_logs": [f"generate_visuals LLM 调用失败: {type(e).__name__}: {e}"],
        }

    visual = _parse_json_output(raw)
    if visual is None:
        return {
            "visual_guidance": _FALLBACK_VISUAL,
            "current_step": "generate_visuals_complete",
            "error_logs": ["generate_visuals JSON 解析失败，使用通用视觉建议降级"],
        }

    violations = _validate_no_foreign_models(visual)
    if violations:
        visual["domestic_image_prompts"] = _FALLBACK_VISUAL["domestic_image_prompts"]
        return {
            "visual_guidance": visual,
            "current_step": "generate_visuals_complete",
            "error_logs": violations,
        }

    return {
        "visual_guidance": visual,
        "current_step": "generate_visuals_complete",
        "error_logs": [],
    }

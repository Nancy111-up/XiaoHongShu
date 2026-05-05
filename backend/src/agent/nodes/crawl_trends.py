"""crawl_trends 节点 —— MCP 搜索小红书热点趋势，提炼结构化 trends_context

对齐 IMPLEMENTATION_PLAN §4.1 节点 2

行为：
1. 尝试通过 MCP Client 调用 MediaCrawler search_trends
2. 30s 超时 / MCP 不可用 / 任何异常 → 降级为通用趋势上下文
3. 降级不阻断 Graph，返回友好默认值 + error_logs 记录
"""

from __future__ import annotations

import asyncio

from src.agent.state import AgentState
from src.agent.tools.llm_client import chat_completion
from src.agent.tools.mcp_client import MCPServiceError, get_mcp_manager

_FALLBACK_TRENDS_CONTEXT = """当前小红书平台趋势（通用降级数据）：

**叙事角度**：
1. 法式简约通勤 — 「不费力高级感」仍是流量密码
2. 国货设计师品牌 — 「小众不撞款」搜索量上升
3. 一包多背 — 实用主义消费观受追捧

**高频关键词**：
通勤穿搭、法式风格、小众设计、质感生活、胶囊衣橱

**标题特征**：
- 数字型：「3件单品搞定一周通勤」
- 反常识型：「越简单越显贵」
- 场景型：「上班第1年 VS 第3年的包」

**结构模式**：
- 痛点开场 → 干货分段 → 软植入收尾
- 每段不超过3行，多用短句
"""


async def crawl_trends_node(state: AgentState) -> dict:
    user_input = state["user_input"]
    manager = get_mcp_manager()

    try:
        if not manager.is_connected:
            raise MCPServiceError("MCP client not connected")

        raw_trends = await manager.call_tool(
            "search_trends",
            query=user_input,
            max_results=5,
            timeout=30,
        )

        # 用 Qwen-Turbo 提炼原始热点数据为结构化 trends_context
        trends_context = await _refine_with_llm(str(raw_trends))
        return {
            "trends_context": trends_context,
            "current_step": "crawl_trends_complete",
            "error_logs": [],
        }

    except asyncio.TimeoutError:
        return _fallback("MCP search_trends 超时 (30s)，使用通用趋势降级")
    except MCPServiceError as e:
        return _fallback(f"MCP 服务不可用: {e}")
    except Exception as e:
        return _fallback(f"crawl_trends 异常: {type(e).__name__}: {e}")


def _fallback(reason: str) -> dict:
    return {
        "trends_context": _FALLBACK_TRENDS_CONTEXT,
        "current_step": "crawl_trends_fallback",
        "error_logs": [reason],
    }


async def _refine_with_llm(raw_data: str) -> str:
    """用小模型（Qwen-Turbo）将原始热点提炼为结构化趋势摘要"""
    messages = [
        {
            "role": "system",
            "content": (
                "你是小红书趋势分析师。根据提供的原始热点数据，提炼出：\n"
                "1. 2-3个可用的叙事角度\n"
                "2. 5-8个高频关键词\n"
                "3. 标题特征（2-3种模式）\n"
                "4. 结构模式\n"
                "用中文输出，300字以内。"
            ),
        },
        {"role": "user", "content": f"原始热点数据：\n{raw_data}"},
    ]
    try:
        return await chat_completion(
            messages,
            model="qwen-turbo",
            temperature=0.3,
            max_tokens=512,
        )
    except Exception:
        return _FALLBACK_TRENDS_CONTEXT

"""选题雷达节点 —— 调用 Tavily 搜索热点趋势，输出 3-5 个高潜力选题
TODO(Phase 2): 替换为 MediaCrawler MCP Server 调用，输出结构化 list[TopicCard]
"""

from __future__ import annotations

import asyncio

from src.agent.state import AgentState
from src.agent.tools.tavily_search import search_trends
from src.config import get_settings

settings = get_settings()


async def research_node(state: AgentState) -> dict:
    user_input = state["user_input"]

    await asyncio.sleep(0.3)

    topics = await search_trends(user_input, max_results=settings.max_search_results)

    return {
        "topic_cards": topics,  # Phase 2 替换为 list[TopicCard]
        "is_revision": False,
        "current_step": "research_complete",
        "error_logs": [],
    }

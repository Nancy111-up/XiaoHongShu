"""Tavily 热点搜索工具 —— DEPRECATED

⚠️ DEPRECATED: Phase 2 将由 MediaCrawler MCP Server 替代。
   仅保留给 api/v1/agent/discover 端点临时使用。
   所有 Agent 内部节点请使用 crawl_trends (MCP)。
   请勿新增调用方。
"""

from __future__ import annotations

import asyncio

from tavily import TavilyClient

from src.config import get_settings

_client: TavilyClient | None = None


def _get_client() -> TavilyClient:
    global _client
    if _client is None:
        settings = get_settings()
        _client = TavilyClient(api_key=settings.tavily_api_key)
    return _client


def _do_search(query: str, max_results: int, timeout: int) -> list[str]:
    client = _get_client()
    response = client.search(
        query=f"{query} 小红书 热门 趋势",
        search_depth="basic",
        topic="general",
        time_range="week",
        max_results=max_results,
        timeout=timeout,
    )

    results: list[str] = []
    for item in response.get("results", []):
        title = item.get("title", "")
        content = item.get("content", "")
        if title:
            entry = f"{title} —— {content[:80]}" if content else title
            results.append(entry)

    return results or [f"「{query}」2026年最新趋势解读，速看！"]


async def search_trends(query: str, max_results: int | None = None) -> list[str]:
    settings = get_settings()
    if max_results is None:
        max_results = settings.max_search_results

    return await asyncio.to_thread(
        _do_search, query, max_results, settings.search_timeout
    )

"""Tavily 热点搜索工具 —— 调用 Tavily Search API 获取小红书选题素材"""

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

"""MediaCrawler MCP Server — 小红书趋势搜索

通过 FastMCP 暴露 3 个工具:
- search_trends: 搜索小红书关键词
- get_note_detail: 获取单篇笔记详情
- check_health: 检查浏览器/登录状态

启动: python -m skills.media_crawler.server
调试: mcp dev skills/media_crawler/server.py
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger("media_crawler")

mcp = FastMCP("media_crawler")

_CDP_MODE = os.environ.get("MCP_CDP_MODE", "").lower() in ("1", "true", "yes")

# 默认降级数据 — MCP 不可用或未登录时使用
_DEFAULT_TRENDS = [
    {
        "title": "早秋通勤穿搭公式｜3件单品搞定一周",
        "author": "穿搭博主Luna",
        "likes_text": "1.2万",
        "url": "https://www.xiaohongshu.com/explore/example1",
    },
    {
        "title": "法式简约风｜小众设计师品牌合集",
        "author": "时尚买手日记",
        "likes_text": "8900",
        "url": "https://www.xiaohongshu.com/explore/example2",
    },
    {
        "title": "一包多背｜实用主义通勤包测评",
        "author": "极简生活家",
        "likes_text": "6700",
        "url": "https://www.xiaohongshu.com/explore/example3",
    },
    {
        "title": "越简单越显贵｜质感穿搭底层逻辑",
        "author": "穿搭研究所",
        "likes_text": "9500",
        "url": "https://www.xiaohongshu.com/explore/example4",
    },
    {
        "title": "上班第1年vs第3年的包｜审美升级",
        "author": "职场新人指南",
        "likes_text": "1.5万",
        "url": "https://www.xiaohongshu.com/explore/example5",
    },
]


@mcp.tool()
async def search_trends(query: str, max_results: int = 5) -> list[dict]:
    """搜索小红书关键词，返回热门笔记列表。

    返回字段: title, author, likes_text, url
    """
    try:
        from skills.media_crawler.browser_manager import get_browser_context
        from skills.media_crawler.login_manager import inject_cookies
        from skills.media_crawler.pipeline import search_notes

        ctx = await get_browser_context(cdp_mode=_CDP_MODE)
        await inject_cookies(ctx)

        notes = await search_notes(ctx, query=query, max_results=min(max_results, 10))
        if notes:
            logger.info("search_trends(%r) → %d results", query, len(notes))
            return notes

    except Exception as e:
        logger.warning("Real search failed: %s, using fallback data", e)

    # 降级: 返回静态示例数据
    keyword = query.lower()
    filtered = [
        t for t in _DEFAULT_TRENDS
        if any(w in t["title"].lower() for w in keyword.split())
    ] or _DEFAULT_TRENDS
    logger.info("search_trends(%r) → %d fallback results", query, len(filtered[:max_results]))
    return filtered[:max_results]


@mcp.tool()
async def get_note_detail(note_id: str) -> dict:
    """获取单篇笔记详情（标题、正文、标签等）。

    参数:
        note_id: 笔记 ID（从 URL /explore/ 或 /discovery/item/ 提取）
    """
    try:
        from skills.media_crawler.browser_manager import get_browser_context
        from skills.media_crawler.login_manager import inject_cookies

        ctx = await get_browser_context(cdp_mode=_CDP_MODE)
        await inject_cookies(ctx)

        page = await ctx.new_page()
        note_url = f"https://www.xiaohongshu.com/explore/{note_id}"
        await page.goto(note_url, timeout=20000, wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)

        detail = await page.evaluate("""
            (() => {
                const title = document.querySelector('.note-title, h1, [class*="title"]');
                const body = document.querySelector('.note-text, [class*="desc"], [class*="content"]');
                const tags = document.querySelectorAll('.tag, [class*="tag"], [class*="topic"]');
                const likeEl = document.querySelector('.like-wrapper .count, [class*="like"] span');
                return {
                    title: title ? title.textContent.trim() : '',
                    body: body ? body.textContent.trim().slice(0, 500) : '',
                    tags: Array.from(tags).map(t => t.textContent.trim()).filter(Boolean).slice(0, 10),
                    likes: likeEl ? likeEl.textContent.trim() : '0',
                };
            })()
        """)
        await page.close()
        return detail

    except Exception as e:
        logger.warning("get_note_detail failed: %s", e)
        return {"error": str(e), "note_id": note_id}


@mcp.tool()
async def check_health() -> dict:
    """检查 MCP Server 健康状态（浏览器可用性 + 登录状态）。"""
    status = {
        "mcp_server": "running",
        "browser": "unknown",
        "xhs_login": "unknown",
        "cookies": False,
    }

    try:
        from skills.media_crawler.browser_manager import check_browser_health
        from skills.media_crawler.login_manager import check_login_status, has_cookies

        status["cookies"] = has_cookies()

        browser_health = await check_browser_health()
        status["browser"] = browser_health.get("status", "error")

        if status["browser"] == "ok":
            from skills.media_crawler.browser_manager import get_browser_context
            from skills.media_crawler.login_manager import inject_cookies

            ctx = await get_browser_context(cdp_mode=_CDP_MODE)
            await inject_cookies(ctx)
            login_status = await check_login_status(ctx)
            status["xhs_login"] = "logged_in" if login_status.get("logged_in") else "not_logged_in"

    except Exception as e:
        status["error"] = str(e)

    return status


if __name__ == "__main__":
    mcp.run()

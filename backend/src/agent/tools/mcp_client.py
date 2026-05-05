"""MCP Client 单例 — 封装 MediaCrawler MCP Server 通信

Phase 1: langchain-mcp-adapters 未安装 → is_connected 恒为 False → 所有调用降级
Phase 2: 安装 langchain-mcp-adapters 后，connect() 连接 MediaCrawler MCP Server
"""

from __future__ import annotations

import asyncio
from functools import lru_cache
from importlib.util import find_spec
from pathlib import Path

_MCP_ADAPTERS_AVAILABLE = find_spec("langchain_mcp_adapters") is not None


class MCPServiceError(Exception):
    """MCP 服务不可用或调用失败"""


class MCPClientManager:
    """MCP 客户端单例管理器

    特性：
    - 懒连接，connect() 失败不抛异常
    - call_tool() 自动包装 asyncio.wait_for(timeout=30)
    - 依赖缺失时 is_connected 恒为 False
    """

    def __init__(self) -> None:
        self._connected: bool = False
        self._tools: dict[str, object] = {}

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def connect(self, server_config: dict | None = None) -> None:
        """尝试连接 MCP Server。任何失败均静默降级，不抛异常。"""
        if not _MCP_ADAPTERS_AVAILABLE:
            return

        try:
            from langchain_mcp_adapters.client import (  # type: ignore[import-untyped]
                MultiServerMCPClient,
            )

            config = server_config or {
                "media_crawler": {
                    "command": "python",
                    "args": ["-m", "skills.media_crawler.server"],
                    "transport": "stdio",
                    "cwd": str(Path(__file__).parent.parent.parent.parent),
                }
            }
            client = MultiServerMCPClient(config)
            tools = await asyncio.wait_for(client.get_tools(), timeout=15)
            self._tools = {t.name: t for t in tools}
            self._connected = True
        except Exception:
            self._connected = False
            self._tools = {}

    async def call_tool(self, name: str, timeout: float = 30, **kwargs: object) -> object:
        """调用 MCP Tool，带超时保护"""
        if not self._connected:
            raise MCPServiceError("MCP client not connected")

        tool = self._tools.get(name)
        if tool is None:
            raise MCPServiceError(f"MCP tool '{name}' not found")

        raw = await asyncio.wait_for(
            tool.ainvoke(kwargs),
            timeout=timeout,
        )
        return _unwrap_mcp_result(raw)


def _unwrap_mcp_result(raw: object) -> object:
    """展开 langchain_mcp_adapters / FastMCP 的 content-block 响应格式。

    FastMCP 返回 [{"type":"text","text":"<json>","id":"..."}],
    需要提取 text 字段并解析 JSON。如果不是这种格式，原样返回。
    """
    import json

    if isinstance(raw, list) and all(
        isinstance(b, dict) and b.get("type") == "text" for b in raw
    ):
        if len(raw) == 1:
            try:
                return json.loads(raw[0]["text"])
            except (json.JSONDecodeError, KeyError):
                return raw[0].get("text", raw)
        return [
            _try_parse(b.get("text", b)) for b in raw
        ]

    if isinstance(raw, dict) and raw.get("type") == "text":
        try:
            return json.loads(raw["text"])
        except (json.JSONDecodeError, KeyError):
            return raw.get("text", raw)

    return raw


def _try_parse(text: str | object) -> object:
    import json

    if not isinstance(text, str):
        return text
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return text


@lru_cache
def get_mcp_manager() -> MCPClientManager:
    return MCPClientManager()

"""敏感词词典 — 从 config.toml [compliance] 加载，供 compliance 节点使用"""

from __future__ import annotations

from functools import lru_cache

from src.config import get_settings


@lru_cache
def load_sensitive_words() -> list[str]:
    return get_settings().sensitive_words


def check_sensitive(text: str) -> list[str]:
    """扫描文本，返回命中的敏感词列表"""
    words = load_sensitive_words()
    if not words:
        return []
    return [w for w in words if w in text]

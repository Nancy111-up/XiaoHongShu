"""品牌资产加载器 —— 读取 Markdown 文件，在 Token 压缩时执行 Pinned 保护"""

from __future__ import annotations

from pathlib import Path

from src.config import get_settings

settings = get_settings()


def load_asset(filename: str) -> str:
    """从 assets/ 目录读取 Markdown 文件内容"""
    path: Path = settings.assets_dir / filename
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def load_all_assets() -> dict[str, str]:
    """加载全部品牌资产，返回 {文件名(不含扩展名): 内容}"""
    result: dict[str, str] = {}
    for ext in ("*.md",):
        for p in settings.assets_dir.glob(ext):
            key = p.stem  # brand_voice, negative_prompts, product_info
            result[key] = p.read_text(encoding="utf-8")
    return result

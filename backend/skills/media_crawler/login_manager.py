"""XHS Cookie 持久化管理器

首次运行 → 保存空占位文件。用户需手动在浏览器中登录 XHS，
然后将 Cookie JSON 放入 data/xhs_cookies.json，或通过 MCP Inspector 调用 check_health 调试。

Cookie 文件格式 (cookie JSON 数组):
[{"name": "a1", "value": "...", "domain": ".xiaohongshu.com", "path": "/"}, ...]
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from playwright.async_api import BrowserContext

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).parent.parent.parent / "data"
_COOKIE_FILE = _DATA_DIR / "xhs_cookies.json"


def cookie_file_path() -> Path:
    return _COOKIE_FILE


def has_cookies() -> bool:
    return _COOKIE_FILE.exists() and _COOKIE_FILE.stat().st_size > 10


def load_cookies() -> list[dict]:
    if not has_cookies():
        return []
    try:
        data = json.loads(_COOKIE_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def save_cookies(cookies: list[dict]) -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    _COOKIE_FILE.write_text(
        json.dumps(cookies, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("Cookies saved to %s", _COOKIE_FILE)


def _normalize_cookies(raw: list[dict]) -> list[dict]:
    """清洗从 Chrome DevTools 导出的 Cookie 为 Playwright 可接收的格式。

    Playwright add_cookies() 要求的字段:
      name, value, domain, path — 必填
      expires — Unix 秒级时间戳 (float)
      httpOnly, secure, sameSite — 可选但需合法值
    """
    VALID_SAME_SITE = {"Strict", "Lax", "None"}
    cleaned: list[dict] = []

    for c in raw:
        # 只保留 Playwright 需要的字段
        keep = {
            "name": str(c.get("name", "")),
            "value": str(c.get("value", "")),
            "domain": str(c.get("domain", "")),
            "path": str(c.get("path", "/")),
        }

        # expires: 优先用 expires，其次 expirationDate
        exp = c.get("expires") or c.get("expirationDate")
        if exp is not None:
            try:
                keep["expires"] = float(exp)
            except (ValueError, TypeError):
                pass

        if c.get("httpOnly") or c.get("httponly"):
            keep["httpOnly"] = True
        if c.get("secure"):
            keep["secure"] = True

        same_site = str(c.get("sameSite", "")).capitalize()
        if same_site in VALID_SAME_SITE:
            keep["sameSite"] = same_site
        elif same_site.lower() in ("no_restriction", "unspecified"):
            keep["sameSite"] = "None"
        # else: omit sameSite entirely, Playwright will default

        if keep["name"] and keep["domain"]:
            cleaned.append(keep)

    return cleaned


async def inject_cookies(context: BrowserContext) -> bool:
    """将持久化的 Cookie 注入浏览器上下文。返回是否成功。"""
    cookies = load_cookies()
    if not cookies:
        logger.warning("No cookies found at %s", _COOKIE_FILE)
        return False
    try:
        normalized = _normalize_cookies(cookies)
        if normalized:
            await context.add_cookies(normalized)
            logger.info("Injected %d cookies from %s", len(normalized), _COOKIE_FILE)
            return True
        return False
    except Exception as e:
        logger.error("Failed to inject cookies: %s", e)
        return False


async def save_cookies_from_context(context: BrowserContext) -> None:
    """从当前浏览器上下文提取并持久化 Cookie。"""
    try:
        cookies = await context.cookies()
        xhs_cookies = [
            c for c in cookies
            if "xiaohongshu.com" in (c.get("domain", ""))
        ]
        save_cookies(xhs_cookies)
    except Exception as e:
        logger.error("Failed to save cookies: %s", e)


async def check_login_status(context: BrowserContext) -> dict:
    """检查当前是否已登录 XHS。"""
    try:
        page = await context.new_page()
        await page.goto("https://www.xiaohongshu.com", timeout=15000, wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)
        # 如果被重定向到登录页，则未登录
        current_url = page.url
        is_logged_in = "login" not in current_url
        title = await page.title()
        await page.close()
        return {
            "logged_in": is_logged_in,
            "url": current_url,
            "title": title,
            "has_cookies": has_cookies(),
        }
    except Exception as e:
        return {"logged_in": False, "error": str(e), "has_cookies": has_cookies()}

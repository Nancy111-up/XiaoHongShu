"""Playwright 浏览器单例管理器

参考 MediaCrawler 的反检测策略:
- 禁用 headless 特征（--disable-blink-features=AutomationControlled）
- 注入 stealth.js 隐藏 webdriver 属性
- 设置 realistic viewport + user-agent

支持两种模式:
- headless（默认）：启动无头 Chromium
- CDP 模式：连接已运行的 Chrome 浏览器，复用其登录态
  使用方式：chrome.exe --remote-debugging-port=9222，然后将 get_browser_context(cdp_mode=True)
"""

from __future__ import annotations

import logging
from pathlib import Path

from playwright.async_api import Browser, BrowserContext, async_playwright

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).parent.parent.parent / "data"
_CDP_PORT = 9222

_STEALTH_JS = """
// 移除 webdriver 检测标志
Object.defineProperty(navigator, 'webdriver', { get: () => false });
// 伪造 chrome 对象
window.chrome = { runtime: {} };
// 伪造权限查询
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) => (
    parameters.name === 'notifications'
        ? Promise.resolve({ state: Notification.permissionState })
        : originalQuery(parameters)
);
// 伪造 plugins
Object.defineProperty(navigator, 'plugins', {
    get: () => [1, 2, 3, 4, 5],
});
// 伪造 languages
Object.defineProperty(navigator, 'languages', {
    get: () => ['zh-CN', 'zh', 'en'],
});
"""

_browser: Browser | None = None
_context: BrowserContext | None = None


async def get_browser_context(cdp_mode: bool = False) -> BrowserContext:
    """获取或创建浏览器上下文（单例）。

    cdp_mode=True: 连接 http://127.0.0.1:9222 的 Chrome，复用其登录态。
    """
    global _browser, _context

    if _context is not None:
        try:
            await _context.pages()
        except Exception:
            _context = None

    if _context is None:
        pw = await async_playwright().start()

        if cdp_mode:
            _browser = await pw.chromium.connect_over_cdp(
                f"http://127.0.0.1:{_CDP_PORT}"
            )
            _context = _browser.contexts[0] if _browser.contexts else await _browser.new_context()
        else:
            _browser = await pw.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                ],
            )
            _context = await _browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            )
            await _context.add_init_script(_STEALTH_JS)

    return _context


async def close_browser() -> None:
    global _browser, _context
    if _context:
        await _context.close()
        _context = None
    if _browser:
        await _browser.close()
        _browser = None


async def check_browser_health() -> dict:
    try:
        ctx = await get_browser_context()
        page = await ctx.new_page()
        await page.goto("https://www.xiaohongshu.com", timeout=15000)
        title = await page.title()
        await page.close()
        return {"status": "ok", "title": title}
    except Exception as e:
        return {"status": "error", "error": str(e)}

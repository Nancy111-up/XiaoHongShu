"""XHS 搜索爬取管线

XHS 搜索结果是混淆 JS 渲染的，必须用 Playwright DOM 提取。
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from playwright.async_api import BrowserContext

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

# XHS note URL 模式
_NOTE_URL_PATTERN = re.compile(r"/explore/([a-f0-9]{24})")


def _debug_save(filename: str, data: object) -> None:
    """将调试数据写入 data/ 目录。"""
    try:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        out = _DATA_DIR / filename
        out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("Debug dump saved: %s", out)
    except Exception as e:
        logger.warning("Failed to save debug dump %s: %s", filename, e)


async def search_notes(
    context: BrowserContext,
    query: str,
    max_results: int = 5,
    timeout: int = 30,
) -> list[dict]:
    """搜索 XHS 笔记，返回结构化趋势数据。"""
    try:
        page = await context.new_page()
        search_url = (
            "https://www.xiaohongshu.com/search_result"
            f"?keyword={query}&source=web_search_result_notes"
        )
        await page.goto(search_url, timeout=timeout * 1000, wait_until="load")
        # 等待 JS 渲染完成
        await page.wait_for_timeout(4000)

        # 滚动触发懒加载
        for _ in range(3):
            try:
                await page.evaluate("window.scrollBy(0, 800)")
            except Exception:
                pass
            await page.wait_for_timeout(600)

        # 从渲染后的 DOM 提取笔记数据
        notes = await _extract_notes_from_dom(page, max_results)
        await page.close()

        if notes:
            logger.info("search_trends(%r) -> %d results", query, len(notes))
        return notes

    except Exception as e:
        logger.error("search_notes failed: %s", e)
        return []


async def _extract_notes_from_dom(page, max_results: int) -> list[dict]:
    """从渲染后的搜索页 DOM 提取笔记卡片。"""

    js_extract = """
    (() => {
        const results = [];
        const seen = new Set();

        // 直接从 section.note-item 提取（而非从隐藏链接出发）
        const sections = document.querySelectorAll('section.note-item');
        sections.forEach(section => {
            if (results.length >= 30) return;

            // 提取 note_id：从隐藏的 /explore/ 链接
            let noteId = '';
            const hiddenA = section.querySelector('a[href*="/explore/"]');
            if (hiddenA) {
                const href = hiddenA.href || hiddenA.getAttribute('href') || '';
                const m = href.match(/\\/explore\\/([a-f0-9]{24})/);
                if (m) noteId = m[1];
            }
            if (!noteId || seen.has(noteId)) return;
            seen.add(noteId);

            // 提取标题：a.title span
            let title = '';
            const titleA = section.querySelector('a.title');
            if (titleA) {
                const span = titleA.querySelector('span');
                title = (span || titleA).textContent.trim();
            }

            // 提取作者：.name div
            let author = '';
            const nameDiv = section.querySelector('.name');
            if (nameDiv) author = nameDiv.textContent.trim();

            // 提取时间：.time div
            let timeText = '';
            const timeDiv = section.querySelector('.time');
            if (timeDiv) timeText = timeDiv.textContent.trim();

            // 提取 likes：.like-wrapper .count 或 .like-wrapper span
            let likes = '';
            const likeWrapper = section.querySelector('.like-wrapper');
            if (likeWrapper) {
                const countEl = likeWrapper.querySelector('.count, [class*=\"count\"]');
                if (countEl) {
                    likes = countEl.textContent.trim();
                } else {
                    // 可能 count 在 like-lottie 后面的文本节点中
                    const spans = likeWrapper.querySelectorAll('span');
                    spans.forEach(s => {
                        const t = s.textContent.trim();
                        if (t && /^[\\d.]+万?$/.test(t)) likes = t;
                    });
                }
            }

            // 提取封面图
            let cover = '';
            const img = section.querySelector('.cover img');
            if (img) cover = img.src || img.getAttribute('src') || '';

            results.push({
                title: title.slice(0, 200) || '',
                author: author,
                time: timeText,
                likes: likes || '0',
                likes_text: likes || '0',
                note_id: noteId,
                url: 'https://www.xiaohongshu.com/explore/' + noteId,
                cover: cover,
            });
        });

        // 如果没找到 note-item，回退到宽泛搜索
        if (results.length === 0) {
            const allLinks = document.querySelectorAll('a[href*=\"/explore/\"]');
            allLinks.forEach(a => {
                if (results.length >= 10) return;
                const href = a.href || a.getAttribute('href') || '';
                const m = href.match(/\\/explore\\/([a-f0-9]{24})/);
                if (!m || seen.has(m[1])) return;
                seen.add(m[1]);
                const container = a.closest('section, article, li') || a.parentElement;
                const text = (container || a).textContent.trim().slice(0, 150);
                results.push({
                    title: text || '(笔记)',
                    author: '',
                    likes: 'N/A',
                    likes_text: 'N/A',
                    note_id: m[1],
                    url: 'https://www.xiaohongshu.com/explore/' + m[1],
                    cover: '',
                });
            });
        }

        return results.slice(0, 30);
    })()
    """

    try:
        raw = await page.evaluate(js_extract)
        notes = []
        for card in raw:
            title = (card.get("title") or "").strip()
            note_id = card.get("note_id", "")
            url = card.get("url", "")
            if not url and note_id:
                url = f"https://www.xiaohongshu.com/explore/{note_id}"

            if title:
                notes.append({
                    "title": title[:200],
                    "author": card.get("author", "").strip(),
                    "time": card.get("time", "").strip(),
                    "likes_text": card.get("likes_text") or card.get("likes") or "N/A",
                    "url": url,
                    "cover": card.get("cover", ""),
                })
            elif url and len(notes) < max_results:
                notes.append({
                    "title": "(笔记)",
                    "author": "",
                    "time": "",
                    "likes_text": "N/A",
                    "url": url,
                    "cover": "",
                })
            if len(notes) >= max_results:
                break
        return notes[:max_results]
    except Exception as e:
        logger.warning("DOM extraction failed: %s", e)
        return []

"""Run or validate the bounded MediaCrawler P0 probe.

This script deliberately does not synthesize crawl output. Live runs require the
user's normal MediaCrawler login flow and a checked-out pinned repository.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.crawler.adapter import MediaCrawlerAdapter
from src.crawler.settings import MediaCrawlerSettings

KEYWORDS = ("校园足球", "足球装备", "大学生体育")


def _records(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for item in sorted(path.rglob("*.jsonl")):
        for line in item.read_text(encoding="utf-8").splitlines():
            if line.strip():
                value = json.loads(line)
                if isinstance(value, dict):
                    rows.append(value)
    return rows


def validate(root: Path) -> int:
    """Validate real job artifacts, returning non-zero when they are absent/invalid."""
    jobs = sorted(p for p in root.iterdir() if p.is_dir()) if root.exists() else []
    search_jobs = [p for p in jobs if "search" in p.name.lower()]
    detail_jobs = [p for p in jobs if "detail" in p.name.lower()]
    if len(search_jobs) != 3:
        print(f"UNAVAILABLE: expected 3 Search job directories, found {len(search_jobs)}")
        return 2
    if len(detail_jobs) != 1:
        print(f"UNAVAILABLE: expected 1 Detail job directory, found {len(detail_jobs)}")
        return 2
    search_rows = _records(search_jobs[0]) + _records(search_jobs[1]) + _records(search_jobs[2])
    if any(row.get("comments") or row.get("comment_count") for row in search_rows):
        print("INVALID: Search output contains comments despite get_comment=false")
        return 3
    detail_rows = _records(detail_jobs[0])
    if not detail_rows:
        print("UNAVAILABLE: Detail job contains no JSONL records")
        return 2
    print("P0 artifacts validated: 3 Search jobs, comments disabled, 1 Detail job")
    return 0


async def run_live(root: Path) -> int:
    settings = MediaCrawlerSettings.from_yaml(Path("../config/mediacrawler.yaml"))
    adapter = MediaCrawlerAdapter(settings)
    root.mkdir(parents=True, exist_ok=True)
    for keyword in KEYWORDS:
        path = root / f"search-{KEYWORDS.index(keyword) + 1}"
        execution = await adapter.run_search(keyword, path)
        if execution.exit_code != 0:
            summary = execution.stderr_summary or "no stderr"
            print(f"NEEDS_CONTEXT: Search failed for {keyword}: {summary}")
            return execution.exit_code or 1
    print("Search jobs complete; select three readable note IDs before running Detail.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    return validate(args.path) if args.validate_only else asyncio.run(run_live(args.path))


if __name__ == "__main__":
    raise SystemExit(main())

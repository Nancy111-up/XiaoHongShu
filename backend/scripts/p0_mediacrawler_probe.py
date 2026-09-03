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
    search_jobs = [p for p in jobs if p.name.lower().startswith("search-")]
    detail_jobs = [p for p in jobs if p.name.lower().startswith("detail-")]
    if len(search_jobs) != 3:
        print(f"UNAVAILABLE: expected 3 Search job directories, found {len(search_jobs)}")
        return 2
    if len(detail_jobs) != 1:
        print(f"UNAVAILABLE: expected 1 Detail job directory, found {len(detail_jobs)}")
        return 2
    manifests = []
    for path in (*search_jobs, *detail_jobs):
        manifest_path = path / "manifest.json"
        if not manifest_path.exists():
            print(f"INVALID: missing execution manifest in {path.name}")
            return 3
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifests.append(manifest)
        if (
            manifest.get("exit_code") != 0
            or not manifest.get("started_at")
            or not manifest.get("finished_at")
        ):
            print(f"INVALID: unsuccessful or stale manifest in {path.name}")
            return 3
        if manifest.get("raw_path") != str(path):
            print(f"INVALID: mixed raw_path in {path.name}")
            return 3
        expected_mode = "search" if path in search_jobs else "detail"
        if manifest.get("mode") != expected_mode:
            print(f"INVALID: {expected_mode.title()} manifest mode in {path.name}")
            return 3
    keywords = {manifest.get("keyword") for manifest in manifests[:3]}
    if keywords != set(KEYWORDS):
        print(f"INVALID: keyword coverage is {sorted(keywords)}")
        return 3
    search_rows = sum((_records(path) for path in search_jobs), [])
    if not search_rows:
        print("UNAVAILABLE: Search jobs contain no note records")
        return 2
    if any("comments" in row or "comment_id" in row or "content" in row for row in search_rows):
        print("INVALID: Search output contains comment records")
        return 3
    if any(
        not isinstance(row.get("note_url"), str) or not row["note_url"].startswith("https://")
        for row in search_rows
    ):
        print("INVALID: Search note URL is not HTTPS")
        return 3
    detail_rows = _records(detail_jobs[0])
    if not detail_rows:
        print("UNAVAILABLE: Detail job contains no JSONL records")
        return 2
    note_ids = {row.get("note_id") for row in detail_rows}
    if len(note_ids) != 3:
        print(f"INVALID: Detail must contain exactly 3 representative notes, found {len(note_ids)}")
        return 3
    representatives = manifests[-1].get("note_ids")
    if (
        not isinstance(representatives, list)
        or len(representatives) != 3
        or len(set(representatives)) != 3
        or set(representatives) != note_ids
    ):
        print("INVALID: Detail manifest note IDs must exactly match 3 distinct records")
        return 3
    if any(
        not isinstance(row.get("note_url"), str) or not row["note_url"].startswith("https://")
        for row in detail_rows
    ):
        print("INVALID: Detail note URL is not HTTPS")
        return 3
    if any(len(row.get("comments", [])) > 20 for row in detail_rows):
        print("INVALID: Detail exceeds 20 first-level comments per note")
        return 3
    if any(
        comment.get("is_sub_comment") for row in detail_rows for comment in row.get("comments", [])
    ):
        print("INVALID: Detail contains second-level comments")
        return 3
    print("P0 artifacts validated: 3 Search jobs, comments disabled, 1 Detail job")
    return 0


def _validate_search_jobs(root: Path) -> int:
    jobs = sorted(p for p in root.iterdir() if p.is_dir() and p.name.startswith("search-"))
    if len(jobs) != 3:
        print("INVALID: resume requires exactly three Search jobs")
        return 3
    seen: set[str] = set()
    for path in jobs:
        manifest_path = path / "manifest.json"
        if not manifest_path.exists():
            return 3
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        keyword = manifest.get("keyword")
        if manifest.get("mode") != "search" or keyword not in KEYWORDS or keyword in seen:
            return 3
        seen.add(keyword)
        if manifest.get("exit_code") != 0 or manifest.get("raw_path") != str(path):
            return 3
        rows = _records(path)
        if not rows or any(
            "comments" in row or "comment_id" in row or "content" in row for row in rows
        ):
            return 3
        if any(
            not isinstance(row.get("note_url"), str) or not row["note_url"].startswith("https://")
            for row in rows
        ):
            return 3
    return 0


async def run_live(root: Path, note_ids: list[str]) -> int:
    settings = MediaCrawlerSettings.from_yaml(Path("../config/mediacrawler.yaml"))
    adapter = MediaCrawlerAdapter(settings)
    try:
        settings.verify_checkout()
    except RuntimeError as exc:
        print(f"NEEDS_CONTEXT: {exc}")
        return 2
    root.mkdir(parents=True, exist_ok=True)
    existing = [p for p in root.iterdir() if p.is_dir() and p.name.startswith("search-")]
    if existing:
        if not note_ids:
            print(
                "NEEDS_DETAIL_SELECTION: select exactly three note IDs, then resume with "
                "--detail-note ID1 --detail-note ID2 --detail-note ID3"
            )
            return 2
        if len(note_ids) != 3 or len(set(note_ids)) != 3 or _validate_search_jobs(root) != 0:
            print("REFUSED: existing Search jobs are not a valid current run")
            return 3
    else:
        if note_ids:
            print("REFUSED: Detail IDs supplied without a successful Search run")
            return 3
    for keyword in () if existing else KEYWORDS:
        path = root / f"search-{KEYWORDS.index(keyword) + 1}-{keyword}"
        if path.exists():
            print(f"REFUSED: job directory already exists: {path}")
            return 2
        execution = await adapter.run_search(keyword, path)
        (path / "manifest.json").write_text(
            json.dumps(
                {
                    "keyword": keyword,
                    "mode": "search",
                    "started_at": execution.started_at.isoformat(),
                    "finished_at": execution.finished_at.isoformat(),
                    "exit_code": execution.exit_code,
                    "raw_path": str(path),
                }
            ),
            encoding="utf-8",
        )
        if execution.exit_code != 0:
            summary = execution.stderr_summary or "no stderr"
            print(f"NEEDS_CONTEXT: Search failed for {keyword}: {summary}")
            return execution.exit_code or 1
    if len(note_ids) != 3 or len(set(note_ids)) != 3:
        print("NEEDS_DETAIL_SELECTION: select exactly three distinct representative note IDs")
        return 2
    detail_path = root / "detail-1"
    if detail_path.exists():
        print(f"REFUSED: job directory already exists: {detail_path}")
        return 2
    execution = await adapter.run_detail(note_ids, detail_path)
    (detail_path / "manifest.json").write_text(
        json.dumps(
            {
                "keyword": "representative",
                "mode": "detail",
                "note_ids": note_ids,
                "started_at": execution.started_at.isoformat(),
                "finished_at": execution.finished_at.isoformat(),
                "exit_code": execution.exit_code,
                "raw_path": str(detail_path),
            }
        ),
        encoding="utf-8",
    )
    print("Search and Detail jobs complete.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--detail-note", action="append", default=[])
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    return (
        validate(args.path)
        if args.validate_only
        else asyncio.run(run_live(args.path, args.detail_note))
    )


if __name__ == "__main__":
    raise SystemExit(main())

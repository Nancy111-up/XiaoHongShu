"""Run or validate the bounded MediaCrawler P0 probe.

Live runs require the user's normal MediaCrawler login flow and the pinned checkout.
Search and Detail are bound by a persisted, unpredictable run identifier.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import secrets
import sys
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.crawler.adapter import CrawlExecution, MediaCrawlerAdapter, redact_sensitive_text
from src.crawler.settings import MediaCrawlerSettings

KEYWORDS = ("校园足球", "足球装备", "大学生体育")
RUN_MANIFEST = "run.json"
RUN_MAX_AGE = timedelta(hours=24)


def _records(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for item in sorted(path.rglob("*.jsonl")):
        for line in item.read_text(encoding="utf-8").splitlines():
            if line.strip():
                value = json.loads(line)
                if isinstance(value, dict):
                    rows.append(value)
    return rows


def _read_manifest(path: Path, label: str) -> dict[str, Any] | None:
    if not path.exists():
        print(f"INVALID: missing {label} manifest")
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"INVALID: malformed {label} manifest: {exc}")
        return None
    if not isinstance(value, dict):
        print(f"INVALID: {label} manifest must be an object")
        return None
    return value


def _write_manifest(path: Path, value: dict[str, object]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


def _timestamp(manifest: dict[str, Any], field: str, label: str) -> datetime | None:
    value = manifest.get(field)
    if not isinstance(value, str):
        print(f"INVALID: {label} {field} must be an ISO timestamp")
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        print(f"INVALID: {label} {field} is not an ISO timestamp")
        return None
    if parsed.tzinfo is None:
        print(f"INVALID: {label} {field} must include a timezone")
        return None
    return parsed.astimezone(UTC)


def _representative_ids(value: object) -> list[str] | None:
    if not isinstance(value, list) or len(value) != 3:
        return None
    if any(not isinstance(item, str) or not item.strip() or item != item.strip() for item in value):
        return None
    ids = [str(item) for item in value]
    return ids if len(set(ids)) == 3 else None


def _job_manifest(
    path: Path,
    expected_mode: str,
    run_id: str,
    run_started: datetime,
    run_finished: datetime | None,
) -> dict[str, Any] | None:
    label = f"{expected_mode.title()} {path.name}"
    manifest = _read_manifest(path / "manifest.json", label)
    if manifest is None:
        return None
    if manifest.get("run_id") != run_id:
        print(f"INVALID: {label} run_id does not match the top-level run")
        return None
    if manifest.get("mode") != expected_mode:
        print(f"INVALID: {label} manifest mode must be {expected_mode}")
        return None
    if (
        not isinstance(manifest.get("exit_code"), int)
        or isinstance(manifest.get("exit_code"), bool)
        or manifest["exit_code"] != 0
    ):
        print(f"INVALID: {label} exit_code must be 0")
        return None
    raw_path = manifest.get("raw_path")
    if not isinstance(raw_path, str) or Path(raw_path).resolve() != path.resolve():
        print(f"INVALID: {label} raw_path does not match its job directory")
        return None
    started = _timestamp(manifest, "started_at", label)
    finished = _timestamp(manifest, "finished_at", label)
    if started is None or finished is None:
        return None
    if started < run_started:
        print(f"INVALID: {label} started_at predates the top-level run")
        return None
    if finished < started:
        print(f"INVALID: {label} finished_at predates started_at")
        return None
    if run_finished is not None and finished > run_finished:
        print(f"INVALID: {label} finished_at exceeds the top-level run")
        return None
    return manifest


def _search_phase(root: Path, run: dict[str, Any], *, completed: bool) -> int:
    run_id = run["run_id"]
    run_started = run["_started"]
    run_finished = run.get("_finished") if completed else None
    search_jobs = sorted(p for p in root.iterdir() if p.is_dir() and p.name.startswith("search-"))
    if len(search_jobs) != 3:
        print(f"INVALID: expected exactly 3 Search job directories, found {len(search_jobs)}")
        return 3
    seen_keywords: set[str] = set()
    for path in search_jobs:
        manifest = _job_manifest(path, "search", run_id, run_started, run_finished)
        if manifest is None:
            return 3
        keyword = manifest.get("keyword")
        if not isinstance(keyword, str) or keyword not in KEYWORDS or keyword in seen_keywords:
            print(f"INVALID: Search keyword is missing, foreign, or duplicated in {path.name}")
            return 3
        seen_keywords.add(keyword)
        rows = _records(path)
        if not rows:
            print(f"UNAVAILABLE: Search job {path.name} contains no note records")
            return 2
        if any("comments" in row or "comment_id" in row for row in rows):
            print(f"INVALID: Search output contains comment records in {path.name}")
            return 3
        if any(
            not isinstance(row.get("note_url"), str)
            or not str(row["note_url"]).startswith("https://")
            for row in rows
        ):
            print(f"INVALID: Search note URL is not HTTPS in {path.name}")
            return 3
    if seen_keywords != set(KEYWORDS):
        print("INVALID: Search keyword coverage is incomplete")
        return 3
    return 0


def _top_run(root: Path, *, completed: bool) -> dict[str, Any] | None:
    run = _read_manifest(root / RUN_MANIFEST, "top-level run")
    if run is None:
        return None
    run_id = run.get("run_id")
    if not isinstance(run_id, str) or len(run_id) < 32 or not run_id.strip():
        print("INVALID: top-level run_id is missing or malformed")
        return None
    expected_status = "completed" if completed else "awaiting_detail"
    if run.get("status") != expected_status:
        print(f"INVALID: top-level run status must be {expected_status}")
        return None
    started = _timestamp(run, "started_at", "top-level run")
    if started is None:
        return None
    finished: datetime | None = None
    if completed:
        finished = _timestamp(run, "finished_at", "top-level run")
        if finished is None:
            return None
        if finished < started:
            print("INVALID: top-level run finished_at predates started_at")
            return None
    elif run.get("finished_at") is not None:
        print("INVALID: unfinished top-level run must have null finished_at")
        return None
    return {**run, "_started": started, "_finished": finished}


def validate(root: Path) -> int:
    """Validate a complete real run, returning non-zero when absent or invalid."""
    if not root.is_dir():
        print("UNAVAILABLE: P0 artifact root does not exist")
        return 2
    run = _top_run(root, completed=True)
    if run is None:
        return 3
    search_result = _search_phase(root, run, completed=True)
    if search_result:
        return search_result
    detail_jobs = sorted(p for p in root.iterdir() if p.is_dir() and p.name.startswith("detail-"))
    if len(detail_jobs) != 1:
        print(f"INVALID: expected exactly 1 Detail job directory, found {len(detail_jobs)}")
        return 3
    detail_path = detail_jobs[0]
    manifest = _job_manifest(
        detail_path, "detail", run["run_id"], run["_started"], run["_finished"]
    )
    if manifest is None:
        return 3
    representatives = _representative_ids(manifest.get("note_ids"))
    if representatives is None:
        print("INVALID: Detail manifest requires three non-empty distinct representative note IDs")
        return 3
    all_detail_rows = _records(detail_path)
    detail_rows = [row for row in all_detail_rows if "comment_id" not in row]
    comment_rows = [row for row in all_detail_rows if "comment_id" in row]
    if len(detail_rows) != 3:
        print(f"INVALID: expected exactly 3 Detail note records, found {len(detail_rows)}")
        return 3
    detail_ids = _representative_ids([row.get("note_id") for row in detail_rows])
    if detail_ids is None or set(detail_ids) != set(representatives):
        print("INVALID: Detail manifest note IDs must exactly match the three Detail note records")
        return 3
    if any(
        not isinstance(row.get("note_url"), str) or not str(row["note_url"]).startswith("https://")
        for row in detail_rows
    ):
        print("INVALID: Detail note URL is not HTTPS")
        return 3
    comments_by_note: Counter[str] = Counter()
    for row in detail_rows:
        embedded = row.get("comments", [])
        if not isinstance(embedded, list):
            print("INVALID: Detail comments must be a list")
            return 3
        for comment in embedded:
            if not isinstance(comment, dict):
                print("INVALID: Detail comments must contain objects")
                return 3
            comment_rows.append({"note_id": row["note_id"], **comment})
    for comment in comment_rows:
        note_id = comment.get("note_id")
        if note_id not in representatives:
            print("INVALID: Detail comment is not bound to a representative note")
            return 3
        if comment.get("is_sub_comment") or comment.get("parent_comment_id"):
            print("INVALID: Detail contains second-level comments")
            return 3
        comments_by_note[str(note_id)] += 1
    if any(count > 20 for count in comments_by_note.values()):
        print("INVALID: Detail exceeds 20 first-level comments per note")
        return 3
    print("P0 artifacts validated: one bound run, 3 Search jobs, and 1 Detail job")
    return 0


def _execution_manifest(
    execution: CrawlExecution,
    run_id: str,
    mode: str,
    *,
    keyword: str | None = None,
    note_ids: list[str] | None = None,
) -> dict[str, object]:
    manifest: dict[str, object] = {
        "run_id": run_id,
        "mode": mode,
        "started_at": execution.started_at.isoformat(),
        "finished_at": execution.finished_at.isoformat(),
        "exit_code": execution.exit_code,
        "raw_path": str(execution.raw_path.resolve()),
    }
    if keyword is not None:
        manifest["keyword"] = keyword
    if note_ids is not None:
        manifest["note_ids"] = note_ids
    return manifest


def _finish_run(
    root: Path,
    run: dict[str, object],
    status: str,
    finished_at: datetime | None = None,
) -> None:
    run["status"] = status
    run["finished_at"] = (finished_at or datetime.now(UTC)).isoformat()
    _write_manifest(root / RUN_MANIFEST, run)


def _safe_summary(execution: CrawlExecution) -> str:
    return redact_sensitive_text(execution.stderr_summary or "no stderr")


async def run_live(root: Path, note_ids: list[str], run_id: str | None = None) -> int:
    settings = MediaCrawlerSettings.from_yaml(Path("../config/mediacrawler.yaml"))
    adapter = MediaCrawlerAdapter(settings)
    try:
        settings.verify_checkout()
    except RuntimeError as exc:
        print(f"NEEDS_CONTEXT: {exc}")
        return 2

    root = root.resolve()
    run_path = root / RUN_MANIFEST
    if not run_path.exists():
        if run_id is not None or note_ids:
            print("REFUSED: Detail resume requires its persisted top-level run manifest")
            return 3
        if root.exists() and any(root.iterdir()):
            print("REFUSED: a new run requires an empty artifact directory")
            return 3
        root.mkdir(parents=True, exist_ok=True)
        new_run_id = secrets.token_hex(32)
        run: dict[str, object] = {
            "run_id": new_run_id,
            "started_at": datetime.now(UTC).isoformat(),
            "finished_at": None,
            "status": "searching",
        }
        _write_manifest(run_path, run)
        try:
            for index, keyword in enumerate(KEYWORDS, 1):
                path = root / f"search-{index}-{keyword}"
                execution = await adapter.run_search(keyword, path)
                _write_manifest(
                    path / "manifest.json",
                    _execution_manifest(execution, new_run_id, "search", keyword=keyword),
                )
                if execution.exit_code != 0:
                    _finish_run(root, run, "failed", execution.finished_at)
                    print(f"NEEDS_CONTEXT: Search failed for {keyword}: {_safe_summary(execution)}")
                    return execution.exit_code or 1
        except (asyncio.CancelledError, KeyboardInterrupt):
            _finish_run(root, run, "interrupted")
            raise
        run["status"] = "awaiting_detail"
        _write_manifest(run_path, run)
        print(
            "NEEDS_DETAIL_SELECTION: select exactly three note IDs, then run "
            f"uv run python scripts/p0_mediacrawler_probe.py --run-id {new_run_id} "
            f"--detail-note ID1 --detail-note ID2 --detail-note ID3 {root}"
        )
        return 2

    if run_id is None:
        print("REFUSED: Detail resume requires explicit --run-id")
        return 3
    representatives = _representative_ids(note_ids)
    if representatives is None:
        print("REFUSED: Detail requires three non-empty distinct representative note IDs")
        return 3
    run = _top_run(root, completed=False)
    if run is None:
        return 3
    if run_id != run["run_id"]:
        print("REFUSED: --run-id does not match the unfinished run")
        return 3
    if datetime.now(UTC) - run["_started"] > RUN_MAX_AGE:
        print("REFUSED: unfinished run has expired")
        return 3
    if datetime.now(UTC) < run["_started"]:
        print("REFUSED: unfinished run started_at is in the future")
        return 3
    if any(p.is_dir() and p.name.startswith("detail-") for p in root.iterdir()):
        print("REFUSED: Detail output already exists for this run")
        return 3
    if _search_phase(root, run, completed=False) != 0:
        print("REFUSED: Search artifacts are not bound to this unfinished run")
        return 3

    detail_path = root / "detail-1"
    persisted_run = {key: value for key, value in run.items() if not key.startswith("_")}
    try:
        execution = await adapter.run_detail(representatives, detail_path)
    except (asyncio.CancelledError, KeyboardInterrupt):
        _finish_run(root, persisted_run, "interrupted")
        raise
    except Exception:
        _finish_run(root, persisted_run, "failed")
        raise
    _write_manifest(
        detail_path / "manifest.json",
        _execution_manifest(execution, run_id, "detail", note_ids=representatives),
    )
    if execution.exit_code != 0:
        _finish_run(root, persisted_run, "failed", execution.finished_at)
        print(f"NEEDS_CONTEXT: Detail failed: {_safe_summary(execution)}")
        return execution.exit_code or 1
    _finish_run(root, persisted_run, "completed", execution.finished_at)
    print("Search and Detail jobs complete.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--run-id")
    parser.add_argument("--detail-note", action="append", default=[])
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    return (
        validate(args.path)
        if args.validate_only
        else asyncio.run(run_live(args.path, args.detail_note, args.run_id))
    )


if __name__ == "__main__":
    raise SystemExit(main())

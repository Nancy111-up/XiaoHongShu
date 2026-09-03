from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.p0_mediacrawler_probe import validate
from src.crawler.settings import MediaCrawlerSettings


def _job(root: Path, name: str, keyword: str, mode: str, notes: list[dict]) -> None:
    path = root / name
    path.mkdir()
    (path / "manifest.json").write_text(
        json.dumps(
            {
                "keyword": keyword,
                "mode": mode,
                "started_at": "2026-09-03T00:00:00+00:00",
                "finished_at": "2026-09-03T00:01:00+00:00",
                "exit_code": 0,
                "raw_path": str(path),
            }
        ),
        encoding="utf-8",
    )
    (path / "notes.jsonl").write_text(
        "\n".join(json.dumps(note) for note in notes), encoding="utf-8"
    )


def test_validator_requires_three_keyword_searches_and_one_three_note_detail(
    tmp_path: Path,
) -> None:
    note = {
        "note_id": "n1",
        "note_url": "https://www.xiaohongshu.com/explore/n1",
        "comment_count": 4,
    }
    for i, keyword in enumerate(("校园足球", "足球装备", "大学生体育"), 1):
        _job(tmp_path, f"search-{i}", keyword, "search", [note])
    _job(
        tmp_path,
        "detail-1",
        "校园足球",
        "detail",
        [
            {
                "note_id": f"n{i}",
                "note_url": f"https://www.xiaohongshu.com/explore/n{i}",
                "comments": [],
            }
            for i in range(1, 4)
        ],
    )
    assert validate(tmp_path) == 0


def test_validator_rejects_empty_search_and_detail_with_more_than_twenty_comments(
    tmp_path: Path,
) -> None:
    for i, keyword in enumerate(("校园足球", "足球装备", "大学生体育"), 1):
        _job(tmp_path, f"search-{i}", keyword, "search", [])
    comments = [{"comment_id": str(i), "content": "x", "is_sub_comment": False} for i in range(21)]
    _job(
        tmp_path,
        "detail-1",
        "校园足球",
        "detail",
        [
            {
                "note_id": "n1",
                "note_url": "https://www.xiaohongshu.com/explore/n1",
                "comments": comments,
            }
        ],
    )
    assert validate(tmp_path) != 0


def test_settings_rejects_unpinned_or_dirty_checkout(tmp_path: Path) -> None:
    checkout = tmp_path / "MediaCrawler"
    checkout.mkdir()
    settings = MediaCrawlerSettings(checkout_path=checkout)
    with pytest.raises(RuntimeError, match="checkout"):
        settings.verify_checkout()

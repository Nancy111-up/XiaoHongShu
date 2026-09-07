from __future__ import annotations

import importlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

FIXTURE_ROOT = Path(__file__).resolve().parents[4] / "tests" / "fixtures" / "mediacrawler"


def normalize_search_record(raw: dict[str, object], captured_at: datetime):  # type: ignore[no-untyped-def]
    return importlib.import_module("src.notes.normalizer").normalize_search_record(raw, captured_at)


def normalize_comment_record(raw: dict[str, object], job_id: str):  # type: ignore[no-untyped-def]
    return importlib.import_module("src.notes.normalizer").normalize_comment_record(raw, job_id)


def _records(name: str) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in (FIXTURE_ROOT / name).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


@pytest.fixture
def captured_at() -> datetime:
    return datetime(2026, 9, 6, 10, 0, tzinfo=UTC)


@pytest.fixture
def search_record() -> dict[str, object]:
    return _records("search_notes.anonymized.jsonl")[0]


def test_missing_metrics_remain_none_and_reduce_completeness(
    search_record: dict[str, object], captured_at: datetime
) -> None:
    raw = {**search_record, "liked_count": None}
    note = normalize_search_record(raw, captured_at)
    assert note.likes is None
    assert note.data_completeness < 1.0


def test_explicit_zero_remains_zero_but_empty_metrics_are_missing(captured_at: datetime) -> None:
    raw = _records("search_notes.anonymized.jsonl")[-1]
    note = normalize_search_record(raw, captured_at)
    assert note.likes == 0
    assert note.collects is None
    assert note.comments is None


def test_compact_chinese_counts_are_parsed_deterministically(
    search_record: dict[str, object], captured_at: datetime
) -> None:
    note = normalize_search_record(search_record, captured_at)
    assert note.likes == 12_000
    assert note.collects == 876
    assert note.comments == 205


def test_published_at_is_millisecond_epoch_converted_to_utc(
    search_record: dict[str, object], captured_at: datetime
) -> None:
    note = normalize_search_record(search_record, captured_at)
    assert note.published_at == datetime.fromtimestamp(1_756_684_800, tz=UTC)
    assert note.published_at.tzinfo is UTC


def test_token_query_is_removed_from_persisted_note_url(
    search_record: dict[str, object], captured_at: datetime
) -> None:
    raw = {
        **search_record,
        "note_url": (
            "https://www.xiaohongshu.com/explore/note-001"
            "?xsec_token=secret&xsec_source=pc_search"
        ),
    }
    note = normalize_search_record(raw, captured_at)
    assert note.url == "https://www.xiaohongshu.com/explore/note-001"
    assert "secret" not in json.dumps(note.raw_payload)


@pytest.mark.parametrize("field", ["liked_count", "collected_count", "comment_count"])
def test_negative_engagement_is_rejected(
    search_record: dict[str, object], captured_at: datetime, field: str
) -> None:
    with pytest.raises(ValueError, match="negative"):
        normalize_search_record({**search_record, field: "-1"}, captured_at)


def test_comment_mapping_preserves_empty_content_and_parses_likes() -> None:
    empty, compact = _records("comments.anonymized.jsonl")[1:3]
    normalized_empty = normalize_comment_record(empty, "job-001")
    normalized_compact = normalize_comment_record(compact, "job-001")
    assert normalized_empty.content == ""
    assert normalized_empty.likes == 0
    assert normalized_empty.job_id == "job-001"
    assert normalized_compact.likes == 13_000
    assert normalized_compact.parent_comment_id is None

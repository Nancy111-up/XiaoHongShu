from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from src.crawler.adapter import CrawlExecution
from src.db.models import RefreshJob
from src.refresh.service import TwoPassRefreshCoordinator


class FakeAdapter:
    def __init__(
        self,
        now: datetime,
        failed_keywords: set[str] | None = None,
        detail_fails: bool = False,
    ) -> None:
        self.now = now
        self.failed_keywords = failed_keywords or set()
        self.detail_fails = detail_fails
        self.search_calls: list[str] = []
        self.detail_calls: list[list[str]] = []

    async def run_search(self, keyword: str, raw_path: Path) -> CrawlExecution:
        self.search_calls.append(keyword)
        if keyword in self.failed_keywords:
            return CrawlExecution(self.now, self.now, 1, raw_path, "fixture failure")
        raw_path.mkdir(parents=True)
        records = []
        for index in range(25):
            published = self.now - (timedelta(days=8) if index == 24 else timedelta(days=1))
            records.append(
                {
                    "note_id": f"{keyword}-{index:02d}",
                    "title": f"{keyword} {index}",
                    "desc": "fixture",
                    "time": int(published.timestamp() * 1000),
                    "liked_count": index,
                    "source_keyword": keyword,
                    "note_url": f"https://www.xiaohongshu.com/explore/{keyword}-{index:02d}",
                }
            )
        _write_jsonl(raw_path / "search.jsonl", records)
        return _execution(raw_path, self.now)

    async def run_detail(self, note_ids: list[str], raw_path: Path) -> CrawlExecution:
        self.detail_calls.append(note_ids)
        if self.detail_fails:
            return CrawlExecution(self.now, self.now, 1, raw_path, "fixture detail failure")
        raw_path.mkdir(parents=True)
        details = [
            {
                "note_id": note_id,
                "title": f"detail {note_id}",
                "desc": "detail fixture",
                "time": int((self.now - timedelta(days=1)).timestamp() * 1000),
                "liked_count": 10,
                "note_url": f"https://www.xiaohongshu.com/explore/{note_id}",
            }
            for note_id in note_ids
        ]
        comments = [
            {
                "comment_id": f"comment-{index}",
                "note_id": note_id,
                "content": "fixture comment",
                "like_count": 1,
                "last_modify_ts": int(self.now.timestamp() * 1000),
                "parent_comment_id": "",
            }
            for index, note_id in enumerate(note_ids)
        ]
        _write_jsonl(raw_path / "detail.jsonl", details)
        _write_jsonl(raw_path / "comments.jsonl", comments)
        return _execution(raw_path, self.now)


class CapturingNoteRepository:
    def __init__(self) -> None:
        self.notes = []
        self.comments = []

    async def upsert_refresh_data(self, job, notes, comments=()) -> None:
        self.notes.extend(notes)
        self.comments.extend(comments)


class CapturingStatusRepository:
    def __init__(self, job: RefreshJob) -> None:
        self.job = job
        self.transitions: list[str] = []
        self.keyword_results: tuple[list[str], list[str]] | None = None

    async def transition(self, job_id: str, status: str, now: datetime) -> RefreshJob:
        assert job_id == self.job.id
        self.transitions.append(status)
        self.job.status = status
        self.job.updated_at = now
        return self.job

    async def record_keyword_results(
        self, job_id: str, successful: list[str], failed: list[str], now: datetime
    ) -> RefreshJob:
        assert job_id == self.job.id
        self.keyword_results = (successful, failed)
        return self.job


class RepresentativeResolver:
    def __init__(self) -> None:
        self.received = []

    async def resolve_representatives(self, notes, max_per_topic: int):
        self.received = list(notes)
        assert max_per_topic == 5
        return [note.note_id for note in notes[:5]]


@pytest.mark.asyncio
async def test_two_pass_refresh_limits_search_then_details_only_representatives(
    tmp_path: Path,
) -> None:
    now = datetime(2025, 9, 6, 12, tzinfo=UTC)
    job = RefreshJob(id="job-two-pass", mode="manual", status="queued", updated_at=now)
    adapter = FakeAdapter(now)
    notes = CapturingNoteRepository()
    statuses = CapturingStatusRepository(job)
    resolver = RepresentativeResolver()
    coordinator = TwoPassRefreshCoordinator(adapter, notes, statuses, resolver)
    keywords = ["校园足球", "足球装备", "大学生体育", "夜跑", "轻户外", "运动恢复"]

    result = await coordinator.run(job, keywords, tmp_path, now)

    assert adapter.search_calls == keywords
    search_notes = [note for note in notes.notes if note.keyword is not None]
    assert len(search_notes) == 120
    assert all(
        note.published_at and note.published_at >= now - timedelta(days=7)
        for note in search_notes
    )
    assert adapter.detail_calls == [[note.note_id for note in search_notes[:5]]]
    assert len(resolver.received) == 120
    assert len(notes.comments) == 5
    assert statuses.keyword_results == (keywords, [])
    assert statuses.transitions == [
        "collecting_search",
        "normalizing",
        "clustering",
        "collecting_detail",
        "completed",
    ]
    assert result.status == "completed"


@pytest.mark.asyncio
async def test_two_pass_refresh_continues_after_keyword_failure(tmp_path: Path) -> None:
    now = datetime(2025, 9, 6, 12, tzinfo=UTC)
    job = RefreshJob(id="job-partial", mode="scheduled", status="queued", updated_at=now)
    adapter = FakeAdapter(now, {"足球装备"})
    notes = CapturingNoteRepository()
    statuses = CapturingStatusRepository(job)
    coordinator = TwoPassRefreshCoordinator(adapter, notes, statuses, RepresentativeResolver())

    result = await coordinator.run(job, ["校园足球", "足球装备", "夜跑"], tmp_path, now)

    assert adapter.search_calls == ["校园足球", "足球装备", "夜跑"]
    assert len([note for note in notes.notes if note.keyword is not None]) == 40
    assert statuses.keyword_results == (["校园足球", "夜跑"], ["足球装备"])
    assert result.status == "partial_success"


@pytest.mark.asyncio
async def test_two_pass_refresh_fails_without_detail_when_every_keyword_fails(
    tmp_path: Path,
) -> None:
    now = datetime(2025, 9, 6, 12, tzinfo=UTC)
    keywords = ["校园足球", "夜跑"]
    job = RefreshJob(id="job-failed", mode="scheduled", status="queued", updated_at=now)
    adapter = FakeAdapter(now, set(keywords))
    statuses = CapturingStatusRepository(job)
    coordinator = TwoPassRefreshCoordinator(
        adapter, CapturingNoteRepository(), statuses, RepresentativeResolver()
    )

    result = await coordinator.run(job, keywords, tmp_path, now)

    assert adapter.detail_calls == []
    assert result.status == "failed"


@pytest.mark.asyncio
async def test_two_pass_refresh_marks_partial_success_when_detail_collection_fails(
    tmp_path: Path,
) -> None:
    now = datetime(2025, 9, 6, 12, tzinfo=UTC)
    job = RefreshJob(id="job-detail-failure", mode="manual", status="queued", updated_at=now)
    adapter = FakeAdapter(now, detail_fails=True)
    statuses = CapturingStatusRepository(job)
    coordinator = TwoPassRefreshCoordinator(
        adapter, CapturingNoteRepository(), statuses, RepresentativeResolver()
    )

    result = await coordinator.run(job, ["校园足球"], tmp_path, now)

    assert result.status == "partial_success"


def _write_jsonl(path: Path, records: list[dict[str, object]]) -> None:
    content = "\n".join(json.dumps(record, ensure_ascii=False) for record in records)
    path.write_text(content, encoding="utf-8")


def _execution(raw_path: Path, now: datetime) -> CrawlExecution:
    return CrawlExecution(now, now, 0, raw_path, None)

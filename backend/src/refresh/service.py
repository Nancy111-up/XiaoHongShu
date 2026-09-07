from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Protocol

from src.crawler.adapter import CrawlExecution
from src.db.models import RefreshJob
from src.notes.normalizer import normalize_comment_record, normalize_search_record
from src.notes.schemas import NormalizedComment, NormalizedNote
from src.refresh.status import RefreshJobStore


class RefreshAlreadyRunning(Exception):  # noqa: N818 - public contract name
    code = "REFRESH_ALREADY_RUNNING"

    def __init__(self, running_job_id: str) -> None:
        super().__init__(f"refresh job {running_job_id} is already running")
        self.running_job_id = running_job_id


class RefreshService:
    def __init__(
        self, repository: RefreshJobStore, now: Callable[[], datetime] = lambda: datetime.now(UTC)
    ) -> None:
        self._repository = repository
        self._now = now

    async def start(self, mode: str) -> RefreshJob:
        running = await self._repository.active_job()
        if running is not None:
            raise RefreshAlreadyRunning(running.id)
        return await self._repository.create(status="queued", updated_at=self._now(), mode=mode)


class Crawler(Protocol):
    async def run_search(self, keyword: str, raw_path: Path) -> CrawlExecution: ...

    async def run_detail(self, note_ids: list[str], raw_path: Path) -> CrawlExecution: ...


class NoteStore(Protocol):
    async def upsert_refresh_data(
        self,
        job: RefreshJob,
        notes: list[NormalizedNote],
        comments: list[NormalizedComment] = ...,
    ) -> None: ...


class StatusStore(Protocol):
    async def transition(self, job_id: str, status: str, now: datetime) -> RefreshJob: ...

    async def record_keyword_results(
        self, job_id: str, successful: list[str], failed: list[str], now: datetime
    ) -> RefreshJob: ...


class TopicResolver(Protocol):
    async def resolve_representatives(
        self, notes: list[NormalizedNote], max_per_topic: int
    ) -> list[str]: ...


class TwoPassRefreshCoordinator:
    def __init__(
        self,
        crawler: Crawler,
        notes: NoteStore,
        statuses: StatusStore,
        topic_resolver: TopicResolver,
    ) -> None:
        self._crawler = crawler
        self._notes = notes
        self._statuses = statuses
        self._topic_resolver = topic_resolver

    async def run(
        self,
        job: RefreshJob,
        keywords: list[str],
        raw_root: Path,
        now: datetime,
    ) -> RefreshJob:
        job = await self._statuses.transition(job.id, "collecting_search", now)
        normalized_search: list[NormalizedNote] = []
        successful_keywords: list[str] = []
        failed_keywords: list[str] = []
        cutoff = now - timedelta(days=7)
        for keyword_index, keyword in enumerate(keywords):
            raw_path = raw_root / "search" / f"{keyword_index:02d}"
            execution = await self._crawler.run_search(keyword, raw_path)
            if execution.exit_code != 0:
                failed_keywords.append(keyword)
                continue
            successful_keywords.append(keyword)
            records = _read_jsonl(raw_path / "search.jsonl")
            accepted = []
            for record in records:
                record["source_keyword"] = keyword
                note = normalize_search_record(record, execution.finished_at)
                if note.published_at is not None and note.published_at >= cutoff:
                    accepted.append(note)
            for position, note in enumerate(accepted[:20], 1):
                normalized_search.append(replace(note, search_position=position))

        job = await self._statuses.record_keyword_results(
            job.id, successful_keywords, failed_keywords, now
        )
        if not successful_keywords:
            return await self._statuses.transition(job.id, "failed", now)

        job = await self._statuses.transition(job.id, "normalizing", now)
        await self._notes.upsert_refresh_data(job, normalized_search)
        job = await self._statuses.transition(job.id, "clustering", now)
        representative_ids = await self._topic_resolver.resolve_representatives(
            normalized_search, max_per_topic=5
        )
        job = await self._statuses.transition(job.id, "collecting_detail", now)
        detail_path = raw_root / "detail"
        execution = await self._crawler.run_detail(representative_ids, detail_path)
        if execution.exit_code != 0:
            return await self._statuses.transition(job.id, "partial_success", now)
        detail_notes = [
            normalize_search_record(record, execution.finished_at)
            for record in _read_jsonl(detail_path / "detail.jsonl")
        ]
        comments = [
            normalize_comment_record(record, job.id)
            for record in _read_jsonl(detail_path / "comments.jsonl")
        ]
        await self._notes.upsert_refresh_data(job, detail_notes, comments)
        final_status = "partial_success" if failed_keywords else "completed"
        return await self._statuses.transition(job.id, final_status, now)


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

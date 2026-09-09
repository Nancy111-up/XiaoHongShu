from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.crawler.adapter import MediaCrawlerAdapter
from src.crawler.settings import MediaCrawlerSettings
from src.db.models import BrandProfile, RefreshJob
from src.llm.factory import build_llm_service
from src.notes.repository import NoteRepository
from src.notes.schemas import NormalizedNote
from src.opportunities.pipeline import OpportunityPipeline
from src.refresh.service import TwoPassRefreshCoordinator
from src.refresh.status import RefreshRepository


class RefreshCoordinator(Protocol):
    async def run(
        self, job: RefreshJob, keywords: list[str], raw_root: Path, now: datetime
    ) -> RefreshJob: ...


class KeywordProvider(Protocol):
    async def load(self) -> list[str]: ...


class BrandKeywordProvider:
    """Read stable, user-configured search terms from the latest brand profile."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def load(self) -> list[str]:
        async with self._sessions() as session:
            profile = await session.scalar(
                select(BrandProfile).order_by(BrandProfile.version.desc()).limit(1)
            )
        if profile is None:
            return []
        payload = json.loads(profile.profile_json)
        terms = [
            payload.get("positioning", ""),
            *payload.get("audiences", []),
            *payload.get("scenes", []),
            *(product.get("name", "") for product in payload.get("products", [])),
            *(product.get("category", "") for product in payload.get("products", [])),
            *(product.get("scene", "") for product in payload.get("products", [])),
        ]
        normalized_terms = (
            term.strip() for term in terms if isinstance(term, str) and term.strip()
        )
        return list(dict.fromkeys(normalized_terms))


class RepresentativeResolver:
    """Choose a bounded set of collected notes for the detail pass."""

    async def resolve_representatives(
        self, notes: list[NormalizedNote], max_per_topic: int
    ) -> list[str]:
        ranked = sorted(
            notes,
            key=lambda note: (note.likes or 0) + (note.collects or 0) + (note.comments or 0),
            reverse=True,
        )
        return list(dict.fromkeys(note.note_id for note in ranked))[:max_per_topic]


class RefreshRunner:
    def __init__(
        self,
        repository: RefreshRepository,
        coordinator: RefreshCoordinator,
        keywords: KeywordProvider,
        raw_root: Path,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
        verify_checkout: Callable[[], None] = lambda: None,
        pipeline: OpportunityPipeline | None = None,
    ) -> None:
        self._repository = repository
        self._coordinator = coordinator
        self._keywords = keywords
        self._raw_root = raw_root
        self._now = now
        self._verify_checkout = verify_checkout
        self._pipeline = pipeline

    async def start(self, job_id: str) -> None:
        job = await self._repository.get(job_id)
        if job is None:
            return
        try:
            self._verify_checkout()
            keywords = await self._keywords.load()
            collected = await self._coordinator.run(
                job, keywords, self._raw_root / job.id, self._now()
            )
        except Exception as error:
            await self._repository.fail(job.id, _safe_failure_summary(error), self._now())
            return
        if self._pipeline is None or collected.status in {"failed", "interrupted"}:
            return
        try:
            await self._pipeline.build(job.id)
        except Exception:
            summary = "AI 分析不可用，请检查 AI 配置后重试；已保留采集结果。"
            if collected.error_summary:
                summary = f"{collected.error_summary} {summary}"
            await self._repository.record_error_summary(job.id, summary[:300], self._now())
            await self._repository.transition(job.id, "partial_success", self._now())
            return
        final = (
            "partial_success"
            if (collected.status == "partial_success" or collected.error_summary)
            else "completed"
        )
        await self._repository.transition(job.id, final, self._now())


def _safe_failure_summary(_: Exception) -> str:
    return "刷新失败，请检查采集配置后重试。"


def build_refresh_runner(sessions: async_sessionmaker[AsyncSession]) -> RefreshRunner:
    project_root = Path(__file__).resolve().parents[3]
    settings = MediaCrawlerSettings.from_yaml(project_root / "config" / "mediacrawler.yaml")
    repository = RefreshRepository(sessions)
    coordinator = TwoPassRefreshCoordinator(
        MediaCrawlerAdapter(settings),
        NoteRepository(sessions),
        repository,
        RepresentativeResolver(),
        finalize=False,
    )
    return RefreshRunner(
        repository,
        coordinator,
        BrandKeywordProvider(sessions),
        project_root / "data" / "raw",
        verify_checkout=settings.verify_checkout,
        pipeline=OpportunityPipeline(sessions, build_llm_service(sessions)),
    )

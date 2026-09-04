from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from src.crawler.settings import MediaCrawlerSettings

_SENSITIVE_QUOTED_VALUE = re.compile(
    r"(?i)([\"']?\b(?:set-cookie|cookies?|authorization|xsec_token)[\"']?\s*[:=]\s*)"
    r"([\"'])(?:\\.|(?!\2).)*\2"
)
_SENSITIVE_UNQUOTED_VALUE = re.compile(
    r"(?i)([\"']?\b(?:set-cookie|cookies?|authorization|xsec_token)[\"']?\s*[:=]\s*)"
    r"(?![\"'])([^\r\n,}]+)"
)
_STDERR_SUMMARY_LIMIT = 4_000


@dataclass(frozen=True)
class CrawlExecution:
    started_at: datetime
    finished_at: datetime
    exit_code: int
    raw_path: Path
    stderr_summary: str | None


class MediaCrawlerAdapter:
    """Construct and execute the pinned MediaCrawler CLI as a subprocess."""

    def __init__(self, settings: MediaCrawlerSettings) -> None:
        self.settings = settings

    def build_search_command(self, keyword: str, raw_path: Path) -> list[str]:
        if not keyword.strip():
            raise ValueError("search keyword must not be empty")
        return [
            *self._base_command(raw_path),
            "--type",
            "search",
            "--keywords",
            keyword,
            "--get_comment",
            "false",
            "--get_sub_comment",
            "false",
            "--crawler_max_notes_count",
            str(self.settings.search_max_notes),
        ]

    def build_detail_command(self, note_ids: list[str], raw_path: Path) -> list[str]:
        normalized_ids = [note_id.strip() for note_id in note_ids if note_id.strip()]
        if not normalized_ids:
            raise ValueError("detail crawl requires at least one note")
        if len(set(normalized_ids)) != len(normalized_ids):
            raise ValueError("detail crawl note IDs must be unique")
        return [
            *self._base_command(raw_path),
            "--type",
            "detail",
            "--specified_id",
            ",".join(normalized_ids),
            "--get_comment",
            "true",
            "--get_sub_comment",
            "false",
            "--max_comments_count_singlenotes",
            str(self.settings.detail_max_comments_per_note),
        ]

    async def run_search(self, keyword: str, raw_path: Path) -> CrawlExecution:
        return await self._run(self.build_search_command(keyword, raw_path), raw_path)

    async def run_detail(self, note_ids: list[str], raw_path: Path) -> CrawlExecution:
        return await self._run(self.build_detail_command(note_ids, raw_path), raw_path)

    def _base_command(self, raw_path: Path) -> list[str]:
        return [
            self.settings.python_executable,
            *self.settings.runner_args,
            "--platform",
            self.settings.platform,
            "--lt",
            self.settings.login_type,
            "--save_data_option",
            self.settings.save_data_option,
            "--save_data_path",
            str(raw_path.resolve()),
            "--max_concurrency_num",
            str(self.settings.max_concurrency),
            "--headless",
            str(self.settings.headless).lower(),
        ]

    async def _run(self, command: list[str], raw_path: Path) -> CrawlExecution:
        resolved_raw_path = raw_path.resolve()
        resolved_raw_path.mkdir(parents=True, exist_ok=True)
        started_at = datetime.now(UTC)
        process = await asyncio.create_subprocess_exec(
            *command,
            cwd=self.settings.checkout_path,
            # MediaCrawler progress (and accidental cookie output) must not leak
            # into the Brand Agent's ordinary process logs.
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await process.communicate()
        finished_at = datetime.now(UTC)
        return CrawlExecution(
            started_at=started_at,
            finished_at=finished_at,
            exit_code=process.returncode,
            raw_path=resolved_raw_path,
            stderr_summary=_summarize_stderr(stderr),
        )


def _summarize_stderr(stderr: bytes) -> str | None:
    decoded = stderr.decode("utf-8", errors="replace").strip()
    if not decoded:
        return None
    redacted = redact_sensitive_text(decoded)
    return redacted[-_STDERR_SUMMARY_LIMIT:]


def redact_sensitive_text(value: str) -> str:
    """Redact secret-bearing fields from a diagnostic string."""

    redacted = _SENSITIVE_QUOTED_VALUE.sub(r"\1\2[REDACTED]\2", value)
    return _SENSITIVE_UNQUOTED_VALUE.sub(r"\1[REDACTED]", redacted)

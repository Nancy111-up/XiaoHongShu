from __future__ import annotations

import importlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import func, select

from alembic import command
from src.db.models import (
    Comment,
    Note,
    NoteSearchSnapshot,
    NoteSnapshot,
    RefreshJob,
)
from src.db.session import create_session_factory
from src.notes.normalizer import normalize_comment_record, normalize_search_record

BACKEND_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = BACKEND_ROOT.parent / "tests" / "fixtures" / "mediacrawler"


def _records(name: str) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in (FIXTURE_ROOT / name).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


@pytest.mark.asyncio
async def test_fixture_import_is_transactional_idempotent_and_preserves_missing_metrics(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "fixture.sqlite3"
    sync_url = f"sqlite:///{database_path.as_posix()}"
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", sync_url)
    command.upgrade(config, "head")
    factory = create_session_factory(f"sqlite+aiosqlite:///{database_path.as_posix()}")
    captured_at = datetime(2026, 9, 6, 10, 0, tzinfo=UTC)
    detail_by_id = {
        record["note_id"]: record
        for record in _records("detail_notes.anonymized.jsonl")
    }
    notes = []
    for position, search_record in enumerate(_records("search_notes.anonymized.jsonl"), 1):
        detail = detail_by_id.get(search_record["note_id"], {})
        merged = {
            **search_record,
            **detail,
            "source_keyword": search_record["source_keyword"],
            "_search_position": position,
        }
        notes.append(normalize_search_record(merged, captured_at))
    comments = [
        normalize_comment_record(record, "job-001")
        for record in _records("comments.anonymized.jsonl")
    ]
    job = RefreshJob(
        id="job-001",
        mode="manual",
        status="normalizing",
        updated_at=captured_at,
    )
    repository_module = importlib.import_module("src.notes.repository")
    repository = repository_module.NoteRepository(factory)

    await repository.upsert_refresh_data(job, notes, comments)
    await repository.upsert_refresh_data(job, notes, comments)

    async with factory() as session:
        assert await session.scalar(select(func.count()).select_from(Note)) == 4
        assert await session.scalar(select(func.count()).select_from(NoteSnapshot)) == 4
        assert await session.scalar(select(func.count()).select_from(NoteSearchSnapshot)) == 4
        assert await session.scalar(select(func.count()).select_from(Comment)) == 4
        missing_snapshot = await session.scalar(
            select(NoteSnapshot).where(NoteSnapshot.note_id == "note-004")
        )
        assert missing_snapshot is not None
        assert missing_snapshot.likes == 0
        assert missing_snapshot.collects is None
        assert missing_snapshot.comments is None
        positions = list(
            await session.scalars(
                select(NoteSearchSnapshot.search_position).order_by(
                    NoteSearchSnapshot.search_position
                )
            )
        )
        assert positions == [1, 2, 3, 4]

    await factory.kw["bind"].dispose()

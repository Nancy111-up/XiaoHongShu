from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.db.models import Comment, Note, NoteSearchSnapshot, NoteSnapshot, RefreshJob
from src.notes.schemas import NormalizedComment, NormalizedNote


def _json(value: dict[str, object]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class NoteRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def upsert_refresh_data(
        self,
        job: RefreshJob,
        notes: Sequence[NormalizedNote],
        comments: Sequence[NormalizedComment] = (),
    ) -> None:
        async with self._session_factory() as session, session.begin():
            await self._upsert_job(session, job)
            for note in notes:
                await self._upsert_note(session, job.id, note)
            for comment in comments:
                await self._upsert_comment(session, job, comment)

    @staticmethod
    async def _upsert_job(session: AsyncSession, source: RefreshJob) -> None:
        existing = await session.get(RefreshJob, source.id)
        if existing is None:
            session.add(source)
            await session.flush()
            return
        for field in (
            "mode",
            "status",
            "started_at",
            "finished_at",
            "updated_at",
            "successful_keywords",
            "failed_keywords",
            "error_code",
            "error_summary",
        ):
            setattr(existing, field, getattr(source, field))

    @staticmethod
    async def _upsert_note(session: AsyncSession, job_id: str, source: NormalizedNote) -> None:
        note = await session.get(Note, source.note_id)
        if note is None:
            note = Note(
                note_id=source.note_id,
                first_seen_at=source.captured_at,
                last_seen_at=source.captured_at,
                title=source.title,
                body=source.body,
                author_id=source.author_id,
                author_name=source.author_name,
                published_at=source.published_at,
                url=source.url,
                raw_payload_json=_json(source.raw_payload),
            )
            session.add(note)
            await session.flush()
        else:
            note.title = source.title
            note.body = source.body
            note.author_id = source.author_id
            note.author_name = source.author_name
            note.published_at = source.published_at
            note.url = source.url
            note.last_seen_at = max(_as_utc(note.last_seen_at), _as_utc(source.captured_at))
            note.raw_payload_json = _json(source.raw_payload)

        snapshot = await session.scalar(
            select(NoteSnapshot).where(
                NoteSnapshot.job_id == job_id,
                NoteSnapshot.note_id == source.note_id,
            )
        )
        values = {
            "captured_at": source.captured_at,
            "likes": source.likes,
            "collects": source.collects,
            "comments": source.comments,
            "shares": source.shares,
            "data_completeness": source.data_completeness,
        }
        if snapshot is None:
            session.add(NoteSnapshot(job_id=job_id, note_id=source.note_id, **values))
        else:
            for field, value in values.items():
                setattr(snapshot, field, value)

        if source.keyword is None or source.search_position is None:
            return
        search_snapshot = await session.scalar(
            select(NoteSearchSnapshot).where(
                NoteSearchSnapshot.job_id == job_id,
                NoteSearchSnapshot.note_id == source.note_id,
                NoteSearchSnapshot.keyword == source.keyword,
            )
        )
        if search_snapshot is None:
            session.add(
                NoteSearchSnapshot(
                    job_id=job_id,
                    note_id=source.note_id,
                    keyword=source.keyword,
                    search_position=source.search_position,
                    captured_at=source.captured_at,
                )
            )
        else:
            search_snapshot.search_position = source.search_position
            search_snapshot.captured_at = source.captured_at

    @staticmethod
    async def _upsert_comment(
        session: AsyncSession, job: RefreshJob, source: NormalizedComment
    ) -> None:
        comment = await session.scalar(
            select(Comment).where(
                Comment.job_id == job.id,
                Comment.comment_id == source.comment_id,
            )
        )
        captured_at = source.captured_at or job.updated_at
        if comment is None:
            session.add(
                Comment(
                    comment_id=source.comment_id,
                    note_id=source.note_id,
                    job_id=job.id,
                    content=source.content,
                    likes=source.likes,
                    captured_at=captured_at,
                )
            )
        else:
            comment.note_id = source.note_id
            comment.content = source.content
            comment.likes = source.likes
            comment.captured_at = captured_at

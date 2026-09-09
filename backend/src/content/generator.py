from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.content.repository import ContentRepository
from src.content.schemas import CopyPreview, FullDraftContent
from src.content.service import ContentService
from src.db.models import BrandProfile, Comment, Note, Opportunity, TopicSnapshotNote
from src.llm.factory import build_llm_service
from src.llm.schemas import CopyPreview as LLMCopyPreview
from src.llm.service import LLMService


class LLMContentGenerator:
    def __init__(
        self, llm: LLMService, sessions: async_sessionmaker[AsyncSession] | None = None
    ) -> None:
        self._llm = llm
        self._sessions = sessions

    @staticmethod
    def _context(opportunity: Opportunity) -> dict[str, object]:
        return {
            "job_id": opportunity.job_id,
            "topic_id": opportunity.topic_id,
            "opportunity_title": opportunity.title,
            "reasons": json.loads(opportunity.reasons_json),
        }

    async def generate_preview(self, opportunity: Opportunity) -> CopyPreview:
        generated = await self._llm.generate_copy_preview(**self._context(opportunity))
        return copy_preview_from_llm(generated, opportunity.title, generated.hook)

    async def generate_full_copy(self, opportunity: Opportunity) -> FullDraftContent:
        context = self._context(opportunity)
        if self._sessions is not None:
            context.update(await self._grounding_context(opportunity))
        generated = await self._llm.generate_full_copy(**context)
        preview = json.loads(opportunity.copy_preview_json or "{}")
        return FullDraftContent(
            titles=_title_options(generated.title, opportunity.title),
            body=generated.body,
            tags=generated.hashtags,
            cta=preview.get("cta") or preview.get("call_to_action"),
            cover_text=generated.title,
            image_count=0,
            image_advice=[],
            product_connection=json.loads(opportunity.reasons_json).get("product_connection"),
            risk_check={"status": "pending_review"},
            prompt_version="full_copy_v1",
        )

    async def _grounding_context(self, opportunity: Opportunity) -> dict[str, object]:
        assert self._sessions is not None
        async with self._sessions() as session:
            brand = await session.scalar(
                select(BrandProfile).where(
                    BrandProfile.version == opportunity.brand_profile_version
                )
            )
            if brand is None:
                raise LookupError("opportunity brand profile version not found")
            notes = list(
                await session.scalars(
                    select(Note)
                    .join(TopicSnapshotNote, TopicSnapshotNote.note_id == Note.note_id)
                    .where(TopicSnapshotNote.topic_snapshot_id == opportunity.topic_snapshot_id)
                    .order_by(Note.note_id)
                )
            )
            note_ids = [note.note_id for note in notes]
            comments = list(
                await session.scalars(
                    select(Comment)
                    .where(Comment.job_id == opportunity.job_id, Comment.note_id.in_(note_ids))
                    .order_by(Comment.comment_id)
                )
            )
        return {
            "brand_profile": json.loads(brand.profile_json),
            "note_ids": note_ids,
            "notes": [
                {"note_id": note.note_id, "title": note.title, "body": note.body, "url": note.url}
                for note in notes
            ],
            "comment_ids": [comment.comment_id for comment in comments],
            "comments": [
                {
                    "comment_id": comment.comment_id,
                    "note_id": comment.note_id,
                    "content": comment.content,
                }
                for comment in comments
            ],
        }


def copy_preview_from_llm(generated: LLMCopyPreview, topic: str, angle: str) -> CopyPreview:
    body = "\n".join([generated.hook, *generated.outline])
    if len(body) < 80:
        body += (
            f"\n围绕{topic}，"
            "结合真实趋势证据提供清晰、可执行的运动建议与产品选择思路，"
            "同时说明适用人群、使用场景、选择标准与注意事项，避免夸大效果。"
        )
    if len(body) < 80:
        body += "。" * (80 - len(body))
    return CopyPreview(
        titles=_title_options(generated.title, topic),
        angle=angle,
        body=body[:150],
        format="图文",
        tags=[],
        cover_direction=generated.title,
        product_connection="自然关联品牌产品与使用场景",
        cost="low",
        cta=generated.call_to_action,
    )


def _title_options(title: str, topic: str) -> list[str]:
    return [title, f"{topic}｜{title}", f"{title}｜实用指南"]


def build_content_service(
    sessions: async_sessionmaker[AsyncSession], llm: LLMService | None = None
) -> ContentService:
    configured = llm if llm is not None else build_llm_service(sessions)
    generator = LLMContentGenerator(configured, sessions) if configured is not None else None
    return ContentService(ContentRepository(sessions), generator)

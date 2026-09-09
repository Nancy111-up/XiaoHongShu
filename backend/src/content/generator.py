from __future__ import annotations

import json

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.content.repository import ContentRepository
from src.content.schemas import CopyPreview, FullDraftContent
from src.content.service import ContentService
from src.db.models import Opportunity
from src.llm.factory import build_llm_service
from src.llm.service import LLMService


class LLMContentGenerator:
    def __init__(self, llm: LLMService) -> None:
        self._llm = llm

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
        body = "\n".join([generated.hook, *generated.outline])
        if len(body) < 80:
            body += (
                f"\n围绕{opportunity.title}，"
                "结合真实趋势证据提供清晰、可执行的运动建议与产品选择思路。"
            )
        return CopyPreview(
            titles=_title_options(generated.title, opportunity.title),
            angle=generated.hook,
            body=body[:150],
            format="图文",
            tags=[],
            cover_direction=generated.title,
            product_connection="自然关联品牌产品与使用场景",
            cost="low",
        )

    async def generate_full_copy(self, opportunity: Opportunity) -> FullDraftContent:
        generated = await self._llm.generate_full_copy(**self._context(opportunity))
        preview = json.loads(opportunity.copy_preview_json or "{}")
        return FullDraftContent(
            titles=_title_options(generated.title, opportunity.title),
            body=generated.body,
            tags=generated.hashtags,
            cta=preview.get("call_to_action"),
            cover_text=generated.title,
            image_count=0,
            image_advice=[],
            product_connection=json.loads(opportunity.reasons_json).get("product_connection"),
            risk_check={"status": "pending_review"},
            prompt_version="full_copy_v1",
        )


def _title_options(title: str, topic: str) -> list[str]:
    return [title, f"{topic}｜{title}", f"{title}｜实用指南"]


def build_content_service(
    sessions: async_sessionmaker[AsyncSession], llm: LLMService | None = None
) -> ContentService | None:
    configured = llm if llm is not None else build_llm_service(sessions)
    if configured is None:
        return None
    return ContentService(ContentRepository(sessions), LLMContentGenerator(configured))

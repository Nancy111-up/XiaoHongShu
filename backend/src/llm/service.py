from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Protocol, TypeVar, cast

from pydantic import BaseModel, ValidationError

from src.llm.schemas import (
    CommentAnalysis,
    ContentGap,
    CopyPreview,
    FullCopy,
    OpportunityExplanation,
    ScoredEvidence,
    TopicClusters,
    TopicResolution,
)


class LLMClient(Protocol):
    async def complete(self, **kwargs: object) -> str: ...


class LLMRunStore(Protocol):
    async def save(self, **values: object) -> None: ...


class LLMAnalysisUnavailableError(RuntimeError):
    pass


LLMAnalysisUnavailable = LLMAnalysisUnavailableError
ResponseT = TypeVar("ResponseT", bound=BaseModel)


class LLMService:
    def __init__(self, client: LLMClient, runs: LLMRunStore, prompts: Path, model: str) -> None:
        self._client, self._runs, self._prompts, self._model = client, runs, prompts, model

    async def _call(
        self,
        *,
        task_type: str,
        prompt_version: str,
        schema: type[ResponseT],
        payload: object,
        job_id: str | None = None,
        topic_id: str | None = None,
        allowed_note_ids: set[str] | None = None,
        allowed_comment_ids: set[str] | None = None,
        comment_content_aliases: dict[str, str] | None = None,
    ) -> ResponseT:
        prompt = (self._prompts / f"{prompt_version}.md").read_text(encoding="utf-8")
        input_json = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        trace = {
            "task_type": task_type,
            "job_id": job_id,
            "topic_id": topic_id,
            "model": self._model,
            "prompt_version": prompt_version,
            "schema_version": prompt_version,
            "temperature": 0,
            "input_hash": hashlib.sha256(input_json.encode()).hexdigest(),
            "input_json": input_json,
        }
        last_raw = last_error = ""
        for _ in range(2):
            try:
                last_raw = await self._client.complete(
                    model=self._model,
                    prompt=prompt,
                    input=input_json,
                    temperature=0,
                    json_schema=schema.model_json_schema(),
                )
            except Exception:
                await self._runs.save(
                    **trace,
                    status="failed",
                    raw_response=None,
                    parsed_response=None,
                    error="AI provider request failed",
                )
                raise LLMAnalysisUnavailableError("AI provider request failed") from None
            try:
                parsed = schema.model_validate_json(last_raw)
                parsed = cast(
                    ResponseT,
                    _replace_comment_content_aliases(parsed, comment_content_aliases),
                )
                self._validate_evidence(parsed, allowed_note_ids, allowed_comment_ids)
            except (ValidationError, ValueError) as exc:
                last_error = str(exc)
                continue
            await self._runs.save(
                **trace,
                status="completed",
                raw_response=last_raw,
                parsed_response=parsed.model_dump_json(),
                error=None,
            )
            return parsed
        await self._runs.save(
            **trace, status="failed", raw_response=last_raw, parsed_response=None, error=last_error
        )
        raise LLMAnalysisUnavailableError(f"{task_type} returned invalid structured output")

    @staticmethod
    def _validate_evidence(
        parsed: BaseModel, allowed_note_ids: set[str] | None, allowed_comment_ids: set[str] | None
    ) -> None:
        data = parsed.model_dump()
        note_ids = set(data.get("evidence_note_ids", []))
        for cluster in data.get("clusters", []):
            note_ids.update(cluster.get("note_ids", []))
        comment_ids = set(data.get("evidence_comment_ids", []))
        categories = data.get("categories")
        if isinstance(categories, dict):
            comment_ids.update(value for values in categories.values() for value in values)
        if allowed_note_ids is not None and not note_ids <= allowed_note_ids:
            raise ValueError("response contains invented note evidence IDs")
        if allowed_comment_ids is not None and not comment_ids <= allowed_comment_ids:
            raise ValueError("response contains invented comment evidence IDs")

    async def cluster_topics(self, *, job_id: str, notes: list[dict[str, object]]) -> TopicClusters:
        return await self._call(
            task_type="cluster_topics",
            prompt_version="topic_cluster_v1",
            schema=TopicClusters,
            payload=notes,
            job_id=job_id,
            allowed_note_ids={str(x["note_id"]) for x in notes if "note_id" in x},
        )

    async def resolve_topic_identity(
        self, *, job_id: str, topic_id: str | None, context: dict[str, object]
    ) -> TopicResolution:
        return await self._call(
            task_type="resolve_topic_identity",
            prompt_version="topic_resolution_v1",
            schema=TopicResolution,
            payload=context,
            job_id=job_id,
            topic_id=topic_id,
        )

    async def analyze_comments(
        self, *, job_id: str, topic_id: str | None, comments: list[dict[str, object]]
    ) -> CommentAnalysis:
        return await self._call(
            task_type="analyze_comments",
            prompt_version="comment_analysis_v1",
            schema=CommentAnalysis,
            payload=comments,
            job_id=job_id,
            topic_id=topic_id,
            allowed_comment_ids={str(x["comment_id"]) for x in comments if "comment_id" in x},
            comment_content_aliases=_unique_comment_content_aliases(comments),
        )

    async def score_brand_relevance(self, **context: object) -> ScoredEvidence:
        return await self._scored("score_brand_relevance", context)

    async def score_audience_relevance(self, **context: object) -> ScoredEvidence:
        return await self._scored("score_audience_relevance", context)

    async def score_product_fit(self, **context: object) -> ScoredEvidence:
        return await self._scored("score_product_fit", context)

    async def _scored(self, task_type: str, context: dict[str, object]) -> ScoredEvidence:
        return await self._evidence_call(
            task_type, "opportunity_scoring_v1", ScoredEvidence, context
        )

    async def analyze_content_gap(self, **context: object) -> ContentGap:
        return await self._evidence_call(
            "analyze_content_gap", "content_gap_v1", ContentGap, context
        )

    async def generate_opportunity_explanation(self, **context: object) -> OpportunityExplanation:
        return await self._evidence_call(
            "generate_opportunity_explanation",
            "opportunity_explanation_v1",
            OpportunityExplanation,
            context,
        )

    async def generate_copy_preview(self, **context: object) -> CopyPreview:
        return await self._evidence_call(
            "generate_copy_preview", "copy_preview_v1", CopyPreview, context
        )

    async def generate_full_copy(self, **context: object) -> FullCopy:
        return await self._evidence_call("generate_full_copy", "full_copy_v1", FullCopy, context)

    async def _evidence_call(
        self,
        task_type: str,
        prompt_version: str,
        schema: type[ResponseT],
        context: dict[str, object],
    ) -> ResponseT:
        return await self._call(
            task_type=task_type,
            prompt_version=prompt_version,
            schema=schema,
            payload={"task_type": task_type, **context},
            job_id=str(context["job_id"]) if context.get("job_id") else None,
            topic_id=str(context["topic_id"]) if context.get("topic_id") else None,
            allowed_note_ids=_ids(context, "note_ids"),
            allowed_comment_ids=_ids(context, "comment_ids"),
        )


def _ids(context: dict[str, object], key: str) -> set[str] | None:
    value = context.get(key)
    return (
        None
        if value is None
        else {str(item) for item in value}
        if isinstance(value, list)
        else set()
    )


def _unique_comment_content_aliases(comments: list[dict[str, object]]) -> dict[str, str]:
    ids_by_content: dict[str, list[str]] = {}
    for comment in comments:
        comment_id = comment.get("comment_id")
        content = comment.get("content")
        if isinstance(comment_id, str) and isinstance(content, str) and content:
            ids_by_content.setdefault(content, []).append(comment_id)
    return {
        content: ids[0]
        for content, ids in ids_by_content.items()
        if len(ids) == 1
    }


def _replace_comment_content_aliases(
    parsed: BaseModel, aliases: dict[str, str] | None
) -> BaseModel:
    if not aliases or not isinstance(parsed, CommentAnalysis):
        return parsed
    payload = parsed.model_dump()
    categories = payload["categories"]
    for category, values in categories.items():
        categories[category] = [aliases.get(value, value) for value in values]
    return CommentAnalysis.model_validate(payload)

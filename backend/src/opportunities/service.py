from __future__ import annotations

import json
from typing import Protocol

from src.db.models import Opportunity
from src.opportunities.gates import EligibilityContext, evaluate_eligibility
from src.opportunities.schemas import OpportunityAnalysisInput, OpportunityResult
from src.opportunities.scoring import (
    OpportunityDimensions,
    content_goals,
    decision,
    opportunity_score,
    trend_timing,
)


class OpportunityStore(Protocol):
    async def save(self, opportunity: Opportunity, llm_run_ids: list[str]) -> Opportunity: ...


class OpportunityService:
    def __init__(self, repository: OpportunityStore) -> None:
        self._repository = repository

    async def analyze_topic(self, context: OpportunityAnalysisInput) -> OpportunityResult:
        gate = evaluate_eligibility(
            EligibilityContext(
                risk=context.risk,
                lifecycle=context.lifecycle,
                brand_relevance=context.brand_relevance,
                product_fit=context.product_fit,
                recent_duplicate=context.recent_duplicate,
            )
        )
        mandatory = (
            context.brand_relevance,
            context.audience_relevance,
            context.content_opportunity,
            context.product_fit,
        )
        score = None
        goals: list[str] = []
        timing = trend_timing(context.current_heat, context.trend_score, context.lifecycle)
        if all(value is not None for value in mandatory):
            dimensions = OpportunityDimensions(
                brand_relevance=context.brand_relevance or 0,
                audience_relevance=context.audience_relevance or 0,
                trend_timing=timing,
                content_opportunity=context.content_opportunity or 0,
                product_fit=context.product_fit or 0,
            )
            score = opportunity_score(dimensions)
            goals = content_goals(dimensions)
        final_decision = (
            decision(score or 0, gate.status)
            if score is not None
            else ("Filtered" if gate.status == "filtered" else "Unavailable")
        )
        breakdown = {
            "brand_relevance": context.brand_relevance,
            "audience_relevance": context.audience_relevance,
            "trend_timing": timing,
            "content_opportunity": context.content_opportunity,
            "product_fit": context.product_fit,
        }
        saved = await self._repository.save(
            Opportunity(
                topic_id=context.topic_id,
                topic_snapshot_id=context.topic_snapshot_id,
                job_id=context.job_id,
                brand_profile_version=context.brand_profile_version,
                title=context.title,
                score=score,
                decision=final_decision,
                eligibility=gate.status,
                risk=context.risk,
                confidence=context.confidence,
                goal=" + ".join(goals) or None,
                score_breakdown_json=json.dumps(breakdown, ensure_ascii=False),
                reasons_json=json.dumps(context.reasons, ensure_ascii=False),
                recommended_angle=context.recommended_angle,
                product_connection=context.product_connection,
                copy_preview_json=(
                    json.dumps(context.copy_preview, ensure_ascii=False)
                    if context.copy_preview is not None
                    else None
                ),
            ),
            context.llm_run_ids,
        )
        return OpportunityResult(
            id=saved.id, score=score, decision=final_decision, eligibility=gate.status, goals=goals
        )

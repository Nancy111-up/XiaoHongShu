from pathlib import Path

import pytest

from src.llm.service import LLMAnalysisUnavailable, LLMService


class FakeClient:
    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.call_count = 0

    async def complete(self, **kwargs) -> str:
        response = self.responses[self.call_count]
        self.call_count += 1
        return response


class FakeRuns:
    def __init__(self) -> None:
        self.saved = []

    async def save(self, **values) -> None:
        self.saved.append(values)


@pytest.mark.asyncio
async def test_schema_failure_retries_once_and_records_failure(tmp_path) -> None:
    (tmp_path / "comment_analysis_v1.md").write_text("Analyze comments", encoding="utf-8")
    client = FakeClient(["not-json", '{"still":"invalid"}'])
    runs = FakeRuns()
    service = LLMService(client, runs, tmp_path, model="test-model")

    with pytest.raises(LLMAnalysisUnavailable):
        await service.analyze_comments(job_id="j1", topic_id="t1", comments=[])

    assert client.call_count == 2
    assert runs.saved[-1]["status"] == "failed"
    assert runs.saved[-1]["prompt_version"] == "comment_analysis_v1"
    assert runs.saved[-1]["schema_version"] == "comment_analysis_v1"
    assert runs.saved[-1]["temperature"] == 0
    assert runs.saved[-1]["input_json"] == "[]"
    assert len(runs.saved[-1]["input_hash"]) == 64


@pytest.mark.asyncio
async def test_comment_analysis_rejects_invented_evidence_ids(tmp_path: Path) -> None:
    (tmp_path / "comment_analysis_v1.md").write_text("Analyze comments", encoding="utf-8")
    client = FakeClient(
        [
            '{"analyzed_comment_count":1,"categories":{"question":["invented"],'
            '"pain_point":[],"request":[],"purchase_intent":[],"experience":[],"other":[]}}',
            '{"analyzed_comment_count":1,"categories":{"question":["c1"],'
            '"pain_point":[],"request":[],"purchase_intent":[],"experience":[],"other":[]}}',
        ]
    )
    runs = FakeRuns()
    service = LLMService(client=client, runs=runs, prompts=tmp_path, model="test-model")

    result = await service.analyze_comments(
        job_id="j1", topic_id="t1", comments=[{"comment_id": "c1", "content": "怎么买？"}]
    )

    assert result.categories.question == ["c1"]
    assert client.call_count == 2
    assert runs.saved[-1]["status"] == "completed"
    assert runs.saved[-1]["parsed_response"] is not None


def test_service_exposes_all_contract_operations() -> None:
    expected = {
        "cluster_topics",
        "resolve_topic_identity",
        "analyze_comments",
        "score_brand_relevance",
        "score_audience_relevance",
        "analyze_content_gap",
        "score_product_fit",
        "generate_opportunity_explanation",
        "generate_copy_preview",
        "generate_full_copy",
    }
    assert expected <= set(dir(LLMService))

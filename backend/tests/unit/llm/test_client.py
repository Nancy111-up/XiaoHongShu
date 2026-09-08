import json

import httpx
import pytest
from pydantic import SecretStr


@pytest.mark.asyncio
async def test_configured_transport_posts_schema_and_returns_model_content(monkeypatch) -> None:
    from src.llm.client import OpenAICompatibleTransport, StructuredLLMClient

    def respond(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://provider.example/v1/chat/completions"
        assert request.headers["authorization"] == "Bearer test-key"
        payload = json.loads(request.content)
        assert payload["model"] == "test-model" and payload["temperature"] == 0
        assert payload["response_format"] == {"type": "json_object"}
        assert '"score"' in payload["messages"][0]["content"]
        assert payload["messages"][1]["content"] == '{"note_ids":["n1"]}'
        return httpx.Response(200, json={"choices": [{"message": {"content": '{"score":80}'}}]})

    original = httpx.AsyncClient
    monkeypatch.setattr(
        "src.llm.client.httpx.AsyncClient",
        lambda **kwargs: original(**kwargs, transport=httpx.MockTransport(respond)),
    )
    client = StructuredLLMClient(
        OpenAICompatibleTransport(
            api_key=SecretStr("test-key"), base_url="https://provider.example/v1/"
        )
    )
    response = await client.complete(
        model="test-model",
        prompt="Evaluate evidence as JSON.",
        input='{"note_ids":["n1"]}',
        temperature=0,
        json_schema={"properties": {"score": {"type": "number"}}},
    )
    assert json.loads(response) == {"score": 80}


def test_llm_configuration_reads_environment_and_masks_credentials(monkeypatch) -> None:
    from src.core.config import Settings

    monkeypatch.setenv("DASHSCOPE_API_KEY", "fixture-config-secret")
    monkeypatch.setenv("LLM_MODEL", "configured-model")
    monkeypatch.setenv("LLM_BASE_URL", "https://provider.example/v1")
    settings = Settings(_env_file=None)
    assert settings.llm_api_key.get_secret_value() == "fixture-config-secret"
    assert settings.llm_model == "configured-model"
    assert settings.llm_base_url == "https://provider.example/v1"
    assert "fixture-config-secret" not in repr(settings)

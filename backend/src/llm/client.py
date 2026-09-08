from __future__ import annotations

import json
from typing import Protocol

import httpx
from pydantic import SecretStr


class ProviderTransport(Protocol):
    async def complete(self, **kwargs: object) -> str: ...


class StructuredLLMClient:
    """The only application boundary allowed to call an LLM provider transport."""

    def __init__(self, transport: ProviderTransport) -> None:
        self._transport = transport

    async def complete(self, **kwargs: object) -> str:
        return await self._transport.complete(**kwargs)


class OpenAICompatibleTransport:
    """Small HTTP boundary for the configured DashScope-compatible chat endpoint."""

    def __init__(self, *, api_key: SecretStr, base_url: str) -> None:
        self._api_key = api_key
        self._url = base_url.rstrip("/") + "/chat/completions"

    async def complete(self, **kwargs: object) -> str:
        schema = json.dumps(kwargs["json_schema"], ensure_ascii=False)
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                self._url,
                headers={"Authorization": f"Bearer {self._api_key.get_secret_value()}"},
                json={
                    "model": kwargs["model"],
                    "temperature": kwargs["temperature"],
                    "response_format": {"type": "json_object"},
                    "messages": [
                        {"role": "system", "content": f"{kwargs['prompt']}\nJSON Schema: {schema}"},
                        {"role": "user", "content": kwargs["input"]},
                    ],
                },
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
        if not isinstance(content, str):
            raise ValueError("Model returned no text content")
        return content

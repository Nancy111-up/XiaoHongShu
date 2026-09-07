from __future__ import annotations

from typing import Protocol


class ProviderTransport(Protocol):
    async def complete(self, **kwargs: object) -> str: ...


class StructuredLLMClient:
    """The only application boundary allowed to call an LLM provider transport."""

    def __init__(self, transport: ProviderTransport) -> None:
        self._transport = transport

    async def complete(self, **kwargs: object) -> str:
        return await self._transport.complete(**kwargs)

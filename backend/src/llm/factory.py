from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.config import Settings
from src.llm.client import OpenAICompatibleTransport, StructuredLLMClient
from src.llm.repository import LLMRunRepository
from src.llm.service import LLMService


def build_llm_service(
    sessions: async_sessionmaker[AsyncSession], settings: Settings | None = None
) -> LLMService | None:
    configured = settings or Settings()
    if configured.llm_api_key is None or not configured.llm_api_key.get_secret_value().strip():
        return None
    backend_root = Path(__file__).resolve().parents[2]
    return LLMService(
        StructuredLLMClient(
            OpenAICompatibleTransport(
                api_key=configured.llm_api_key, base_url=configured.llm_base_url
            )
        ),
        LLMRunRepository(sessions),
        backend_root / "prompts",
        configured.llm_model,
    )

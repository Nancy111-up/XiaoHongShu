from __future__ import annotations

import tomllib
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


# ====== 明牌：config.toml 业务参数 ======
class _LLM(BaseModel):
    model: str = "qwen-plus"
    temperature: float = 0.7
    max_tokens: int = 2048
    base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"


class _Agent(BaseModel):
    search_timeout: int = 30
    max_search_results: int = 5
    max_revision_rounds: int = 5


class _BusinessConfig(BaseModel):
    """Pydantic 自动将 TOML dict 嵌套转换为 _LLM / _Agent 实例"""
    model_config = {"extra": "ignore"}
    llm: _LLM = _LLM()
    agent: _Agent = _Agent()


# ====== 暗牌：.env 密钥 ======
class _Secrets(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    dashscope_api_key: str = ""
    tavily_api_key: str = ""
    langsmith_api_key: str = ""
    xhs_env: str = "dev"


# ====== 融合体 ======
class Settings:
    def __init__(self) -> None:
        self.secrets = _Secrets()
        self.business = _load_toml()

    @property
    def llm_model(self) -> str: return self.business.llm.model
    @property
    def llm_temperature(self) -> float: return self.business.llm.temperature
    @property
    def llm_max_tokens(self) -> int: return self.business.llm.max_tokens
    @property
    def llm_base_url(self) -> str: return self.business.llm.base_url
    @property
    def dashscope_api_key(self) -> str: return self.secrets.dashscope_api_key
    @property
    def tavily_api_key(self) -> str: return self.secrets.tavily_api_key
    @property
    def langsmith_api_key(self) -> str: return self.secrets.langsmith_api_key
    @property
    def search_timeout(self) -> int: return self.business.agent.search_timeout
    @property
    def max_search_results(self) -> int: return self.business.agent.max_search_results
    @property
    def max_revision_rounds(self) -> int: return self.business.agent.max_revision_rounds
    @property
    def is_prod(self) -> bool: return self.secrets.xhs_env == "prod"
    @property
    def assets_dir(self) -> Path: return Path(__file__).parent / "assets"


def _load_toml() -> _BusinessConfig:
    path = Path(__file__).parent.parent / "config.toml"
    if not path.exists():
        return _BusinessConfig()
    return _BusinessConfig(**tomllib.loads(path.read_text(encoding="utf-8")))


@lru_cache
def get_settings() -> Settings:
    return Settings()

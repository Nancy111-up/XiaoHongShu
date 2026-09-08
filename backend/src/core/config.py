from pathlib import Path

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env", extra="ignore"
    )
    service_name: str = "sports-brand-agent"
    llm_api_key: SecretStr | None = Field(
        default=None, validation_alias=AliasChoices("DASHSCOPE_API_KEY", "LLM_API_KEY")
    )
    llm_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    llm_model: str = "qwen-plus"

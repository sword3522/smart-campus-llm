import os
from dataclasses import dataclass


@dataclass
class Settings:
    llm_provider: str = os.getenv("LLM_PROVIDER", "mock").lower()  # deepseek | openai | mock
    api_key: str | None = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
    api_base: str | None = os.getenv("LLM_API_BASE")  # e.g. https://api.deepseek.com or custom openai-compatible
    model: str = os.getenv("LLM_MODEL", "deepseek-chat")
    timeout_seconds: int = int(os.getenv("LLM_TIMEOUT_SECONDS", "60"))
    max_retries: int = int(os.getenv("LLM_MAX_RETRIES", "5"))
    temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.2"))
    seed: int = int(os.getenv("SEED", "42"))


def get_settings() -> Settings:
    return Settings()



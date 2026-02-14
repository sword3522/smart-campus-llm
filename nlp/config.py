import os
from dataclasses import dataclass


@dataclass
class Settings:
    llm_provider: str = os.getenv("LLM_PROVIDER", "local").lower()  # deepseek | openai | local | mock
    api_key: str | None = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
    api_base: str | None = os.getenv("LLM_API_BASE")  # e.g. https://api.deepseek.com or custom openai-compatible
    model: str = os.getenv("LLM_MODEL", "deepseek-chat")
    timeout_seconds: int = int(os.getenv("LLM_TIMEOUT_SECONDS", "120"))  # 增加默认超时时间
    max_retries: int = int(os.getenv("LLM_MAX_RETRIES", "5"))
    temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.2"))
    seed: int = int(os.getenv("SEED", "42"))

    # 本地模型配置
    local_model_path: str = os.getenv("LOCAL_MODEL_PATH", "/root/autodl-tmp/qwen/Qwen2.5-7B-Instruct/")
    local_lora_path: str = os.getenv("LOCAL_LORA_PATH", "/root/NLP/lora/output/Qwen2.5_smart_campus/checkpoint-237")


def get_settings() -> Settings:
    return Settings()



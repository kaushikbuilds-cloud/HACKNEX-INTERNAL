import os
from dataclasses import dataclass


@dataclass
class Settings:
    llm_backend: str = os.environ.get("SWE_AGENT_LLM_BACKEND", "ollama")
    ollama_host: str = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    ollama_model: str = os.environ.get("OLLAMA_MODEL", "qwen2.5-coder:7b")
    workdir: str = os.environ.get("SWE_AGENT_WORKDIR", "./workdir")
    max_retry_attempts: int = int(os.environ.get("SWE_AGENT_MAX_RETRIES", "3"))


settings = Settings()

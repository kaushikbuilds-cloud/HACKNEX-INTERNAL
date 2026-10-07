"""LLM client abstraction. Default backend talks to a local Ollama server
(e.g. a quantized coder model running on a laptop GPU), so the whole
pipeline works with no API key."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import requests

from backend.core.config import settings


@dataclass
class Message:
    role: str  # "system" | "user" | "assistant"
    content: str


class LLMClient(ABC):
    @abstractmethod
    def chat(self, messages: list[Message], temperature: float = 0.2) -> str:
        """Send a chat conversation, return the assistant's text reply."""


class OllamaClient(LLMClient):
    """Talks to a local Ollama server (default http://localhost:11434).

    Point OLLAMA_MODEL at whatever you've pulled, e.g.:
        ollama pull qwen2.5-coder:7b
        export OLLAMA_MODEL=qwen2.5-coder:7b
    """

    def __init__(self, model: str | None = None, host: str | None = None, timeout: int = 300):
        self.model = model or settings.ollama_model
        self.host = host or settings.ollama_host
        self.timeout = timeout

    def chat(self, messages: list[Message], temperature: float = 0.2) -> str:
        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
            "options": {"temperature": temperature},
        }
        resp = requests.post(f"{self.host}/api/chat", json=payload, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()["message"]["content"]


class EchoClient(LLMClient):
    """No-op fallback used in tests / when no local model is reachable yet."""

    def chat(self, messages: list[Message], temperature: float = 0.2) -> str:
        return messages[-1].content


def get_default_client() -> LLMClient:
    if settings.llm_backend == "ollama":
        return OllamaClient()
    if settings.llm_backend == "echo":
        return EchoClient()
    raise ValueError(f"Unknown LLM backend: {settings.llm_backend}")

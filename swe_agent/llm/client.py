"""LLM client abstraction. Default backend talks to a local Ollama server
(e.g. a quantized coder model running on a laptop GPU), so the whole
pipeline works with no API key."""

from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass

import requests


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

    def __init__(
        self,
        model: str | None = None,
        host: str | None = None,
        timeout: int = 300,
    ):
        self.model = model or os.environ.get("OLLAMA_MODEL", "qwen2.5-coder:7b")
        self.host = host or os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        self.timeout = timeout

    def chat(self, messages: list[Message], temperature: float = 0.2) -> str:
        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
            "options": {"temperature": temperature},
        }
        resp = requests.post(
            f"{self.host}/api/chat", json=payload, timeout=self.timeout
        )
        resp.raise_for_status()
        data = resp.json()
        return data["message"]["content"]


class EchoClient(LLMClient):
    """No-op fallback used in tests / when no local model is reachable yet."""

    def chat(self, messages: list[Message], temperature: float = 0.2) -> str:
        return messages[-1].content


def get_default_client() -> LLMClient:
    backend = os.environ.get("SWE_AGENT_LLM_BACKEND", "ollama")
    if backend == "ollama":
        return OllamaClient()
    if backend == "echo":
        return EchoClient()
    raise ValueError(f"Unknown LLM backend: {backend}")


def extract_json(text: str) -> dict:
    """LLMs wrap JSON in prose/fences sometimes; pull out the first {...} block."""
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError(f"No JSON object found in LLM output: {text[:200]!r}")
    return json.loads(text[start : end + 1])

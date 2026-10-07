"""Diagram step 4: Retrieve Relevant Files — semantic search over the
vector store, collapsed to a ranked, deduplicated file list plus an
LLM-ready context block."""

from __future__ import annotations

from .vectorstore import VectorStore


def relevant_files(store: VectorStore, request: str, top_k: int = 8) -> list[str]:
    seen: list[str] = []
    for chunk, _score in store.search(request, top_k=top_k * 3):
        if chunk.file not in seen:
            seen.append(chunk.file)
        if len(seen) >= top_k:
            break
    return seen


def build_context(store: VectorStore, request: str, top_k: int = 8, max_chars: int = 12000) -> str:
    parts = []
    budget = max_chars
    for chunk, score in store.search(request, top_k=top_k):
        block = f"### {chunk.file}  ({chunk.kind} {chunk.name}, lines {chunk.start_line}-{chunk.end_line}, score={score:.2f})\n```\n{chunk.text}\n```\n"
        if len(block) > budget:
            break
        parts.append(block)
        budget -= len(block)
    return "\n".join(parts)

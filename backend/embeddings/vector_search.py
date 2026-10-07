"""Build the Code Knowledge Base (parse -> chunk -> embed -> store) and
retrieve relevant files / context for a natural-language request."""

from __future__ import annotations

from pathlib import Path

from backend.embeddings.chromadb_manager import ChromaDBManager
from backend.repository.parser import Chunk, chunk_file, iter_source_files


def build_index(root: Path) -> ChromaDBManager:
    store = ChromaDBManager()
    for path in iter_source_files(root):
        for chunk in chunk_file(path, root):
            store.add(chunk)
    return store


def relevant_files(store: ChromaDBManager, request: str, top_k: int = 8) -> list[str]:
    seen: list[str] = []
    for chunk, _score in store.search(request, top_k=top_k * 3):
        if chunk.file not in seen:
            seen.append(chunk.file)
        if len(seen) >= top_k:
            break
    return seen


def best_chunk_in_file(store: ChromaDBManager, file: str, query: str) -> Chunk | None:
    """Of the chunks belonging to `file`, return the one most relevant to
    `query` — used to target a single function/class for large-file edits."""
    for chunk, _score in store.search(query, top_k=max(len(store), 1)):
        if chunk.file == file:
            return chunk
    return None


def build_context(
    store: ChromaDBManager, request: str, top_k: int = 8, max_chars: int = 12000
) -> str:
    parts = []
    budget = max_chars
    for chunk, score in store.search(request, top_k=top_k):
        block = (
            f"### {chunk.file}  ({chunk.kind} {chunk.name}, "
            f"lines {chunk.start_line}-{chunk.end_line}, score={score:.2f})\n"
            f"```\n{chunk.text}\n```\n"
        )
        if len(block) > budget:
            break
        parts.append(block)
        budget -= len(block)
    return "\n".join(parts)

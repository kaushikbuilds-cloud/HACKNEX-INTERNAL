"""Retrieve Relevant Files step: semantic search over the vector store,
collapsed to a ranked, deduplicated file list the planner can draw from."""

from __future__ import annotations

from backend.embeddings.chromadb_manager import ChromaDBManager
from backend.embeddings.vector_search import relevant_files


def select_candidate_files(store: ChromaDBManager, request: str, top_k: int = 8) -> list[str]:
    return relevant_files(store, request, top_k=top_k)

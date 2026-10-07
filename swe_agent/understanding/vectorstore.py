"""Workflow 1, step 3 (store) + Workflow 1 step 4 / diagram's "Retrieve
Relevant Files" (search). Pure-python in-memory store with optional JSON
persistence — avoids a ChromaDB/FAISS dependency so indexing works with
zero setup; same interface can be backed by Chroma later if desired."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .chunker import Chunk, chunk_file, iter_source_files
from .embeddings import cosine, embed


class VectorStore:
    def __init__(self):
        self._chunks: list[Chunk] = []
        self._vectors: list[list[float]] = []

    def add(self, chunk: Chunk) -> None:
        self._chunks.append(chunk)
        self._vectors.append(embed(f"{chunk.name}\n{chunk.text}"))

    def search(self, query: str, top_k: int = 8) -> list[tuple[Chunk, float]]:
        qvec = embed(query)
        scored = [
            (chunk, cosine(qvec, vec))
            for chunk, vec in zip(self._chunks, self._vectors)
        ]
        scored.sort(key=lambda cs: cs[1], reverse=True)
        return scored[:top_k]

    def save(self, path: Path) -> None:
        payload = {
            "chunks": [asdict(c) for c in self._chunks],
            "vectors": self._vectors,
        }
        Path(path).write_text(json.dumps(payload))

    @classmethod
    def load(cls, path: Path) -> "VectorStore":
        data = json.loads(Path(path).read_text())
        store = cls()
        store._chunks = [Chunk(**c) for c in data["chunks"]]
        store._vectors = data["vectors"]
        return store

    def __len__(self) -> int:
        return len(self._chunks)


def build_index(root: Path) -> VectorStore:
    """Workflow 1: parse every source file, chunk it, embed and store."""
    store = VectorStore()
    for path in iter_source_files(root):
        for chunk in chunk_file(path, root):
            store.add(chunk)
    return store

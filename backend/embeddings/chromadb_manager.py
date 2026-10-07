"""Vector store backing the Code Knowledge Base. Default implementation is a
pure-python in-memory/JSON-persisted store — zero extra dependencies, works
fully offline on a laptop. Swap this for a real ChromaDB-backed manager by
keeping the same `add` / `search` / `save` / `load` interface if/when the
project wants persistent ANN search at larger scale."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from backend.embeddings.embedder import cosine, embed
from backend.repository.parser import Chunk


class ChromaDBManager:
    def __init__(self):
        self._chunks: list[Chunk] = []
        self._vectors: list[list[float]] = []

    def add(self, chunk: Chunk) -> None:
        self._chunks.append(chunk)
        self._vectors.append(embed(f"{chunk.file} {chunk.name}\n{chunk.text}"))

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
    def load(cls, path: Path) -> "ChromaDBManager":
        data = json.loads(Path(path).read_text())
        store = cls()
        store._chunks = [Chunk(**c) for c in data["chunks"]]
        store._vectors = data["vectors"]
        return store

    def __len__(self) -> int:
        return len(self._chunks)

"""Lightweight, dependency-free embeddings so semantic search works fully
offline on a laptop with no model downloads. Hashing bag-of-words vectorizer
(a la the hashing trick) over identifier-aware tokens. Swap in a real
sentence-transformers model later by implementing the same `embed` signature."""

from __future__ import annotations

import hashlib
import math
import re
from collections import Counter

DIM = 512
TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*|[0-9]+")


def tokenize(text: str) -> list[str]:
    tokens = []
    for raw in TOKEN_RE.findall(text):
        tokens.append(raw.lower())
        # split camelCase / snake_case into sub-tokens too
        parts = re.findall(r"[A-Z]?[a-z0-9]+|[A-Z]+(?![a-z])", raw)
        if len(parts) > 1:
            tokens.extend(p.lower() for p in parts)
    return tokens


def _hash_index(token: str) -> int:
    h = hashlib.md5(token.encode("utf-8")).digest()
    return int.from_bytes(h[:4], "little") % DIM


def embed(text: str) -> list[float]:
    tokens = tokenize(text)
    if not tokens:
        return [0.0] * DIM
    counts = Counter(tokens)
    vec = [0.0] * DIM
    for tok, c in counts.items():
        idx = _hash_index(tok)
        vec[idx] += c * (1.0 + math.log(len(tok)))
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))

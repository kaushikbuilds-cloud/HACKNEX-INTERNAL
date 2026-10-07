"""Break source files into function/class-sized chunks the agent can index
and retrieve. Uses Python's `ast` for accurate Python chunking; other
languages fall back to a line-window chunker so the pipeline still works
on JS/TS/Go/etc. without native parser binaries."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from backend.core.constants import CODE_EXTS, IGNORE_DIRS
from backend.utils.file_utils import safe_read_text

FALLBACK_WINDOW = 60
FALLBACK_OVERLAP = 10


@dataclass
class Chunk:
    file: str
    name: str
    kind: str  # "function" | "class" | "module" | "block"
    start_line: int
    end_line: int
    text: str


def iter_source_files(root: Path):
    root = Path(root)
    for p in root.rglob("*"):
        if p.suffix in CODE_EXTS and p.is_file() and not any(
            part in IGNORE_DIRS for part in p.parts
        ):
            yield p


def chunk_file(path: Path, root: Path) -> list[Chunk]:
    rel = str(path.relative_to(root))
    source = safe_read_text(path)
    if not source:
        return []

    if path.suffix == ".py":
        chunks = _chunk_python(rel, source)
        if chunks:
            return chunks

    return _chunk_fallback(rel, source)


def _chunk_python(rel: str, source: str) -> list[Chunk]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    lines = source.splitlines()
    chunks: list[Chunk] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            start = node.lineno
            end = getattr(node, "end_lineno", start)
            kind = "class" if isinstance(node, ast.ClassDef) else "function"
            text = "\n".join(lines[start - 1 : end])
            chunks.append(Chunk(rel, node.name, kind, start, end, text))

    if not chunks and lines:
        chunks.append(Chunk(rel, Path(rel).stem, "module", 1, len(lines), source))

    return chunks


def _chunk_fallback(rel: str, source: str) -> list[Chunk]:
    lines = source.splitlines()
    if not lines:
        return []
    chunks = []
    step = FALLBACK_WINDOW - FALLBACK_OVERLAP
    for i in range(0, len(lines), step):
        window = lines[i : i + FALLBACK_WINDOW]
        if not window:
            continue
        chunks.append(
            Chunk(
                rel,
                f"{Path(rel).stem}:{i + 1}",
                "block",
                i + 1,
                i + len(window),
                "\n".join(window),
            )
        )
    return chunks

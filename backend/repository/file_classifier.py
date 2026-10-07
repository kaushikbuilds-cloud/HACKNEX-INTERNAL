"""Classify each file's role (source / test / config / doc / other) so the
rest of the pipeline can reason about "existing tests" vs. "code to change"
separately."""

from __future__ import annotations

from pathlib import Path

from backend.core.constants import CODE_EXTS, CONFIG_FILENAMES, DOC_EXTS, TEST_PATH_HINTS


def classify_file(rel_path: str) -> str:
    p = Path(rel_path)
    parts_lower = [part.lower() for part in p.parts]
    name_lower = p.name.lower()

    if p.name in CONFIG_FILENAMES or name_lower.startswith(".env"):
        return "config"
    if p.suffix in DOC_EXTS:
        return "doc"
    if any(hint in parts_lower for hint in TEST_PATH_HINTS) or name_lower.startswith(
        "test_"
    ) or name_lower.endswith("_test.py") or name_lower.endswith(".test.js") or name_lower.endswith(
        ".spec.ts"
    ):
        return "test"
    if p.suffix in CODE_EXTS:
        return "source"
    return "other"


def classify_repo(root: Path) -> dict[str, list[str]]:
    from backend.utils.file_utils import walk_files

    buckets: dict[str, list[str]] = {"source": [], "test": [], "config": [], "doc": [], "other": []}
    for f in walk_files(root):
        rel = str(f.relative_to(root))
        buckets[classify_file(rel)].append(rel)
    return buckets

"""Find documentation files, so planning/explanation can reference or
update docs when a change affects documented behavior."""

from __future__ import annotations

from pathlib import Path

from backend.core.constants import DOC_EXTS
from backend.utils.file_utils import walk_files


def analyze_docs(root: Path) -> list[str]:
    root = Path(root)
    return sorted(
        str(p.relative_to(root)) for p in walk_files(root) if p.suffix in DOC_EXTS
    )

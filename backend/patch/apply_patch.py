"""Apply a set of FileEdits to disk, on the agent's work branch."""

from __future__ import annotations

from pathlib import Path

from backend.llm.code_generator import FileEdit
from backend.patch.git_manager import ensure_branch


def apply_edits(root: Path, edits: list[FileEdit], branch: str) -> list[str]:
    """Create/checkout `branch`, write changed files, return list of
    modified relative paths."""
    ensure_branch(root, branch)

    modified = []
    for edit in edits:
        if not edit.changed:
            continue
        full_path = Path(root) / edit.path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(edit.new)
        modified.append(edit.path)

    return modified

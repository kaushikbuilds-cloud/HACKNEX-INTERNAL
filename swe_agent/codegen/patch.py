"""Diagram step 6-7: turn FileEdits into a unified diff, create a branch,
and apply the changes to disk."""

from __future__ import annotations

import difflib
from pathlib import Path

import git

from .generator import FileEdit


def unified_diff(edit: FileEdit) -> str:
    return "".join(
        difflib.unified_diff(
            edit.original.splitlines(keepends=True),
            edit.new.splitlines(keepends=True),
            fromfile=f"a/{edit.path}",
            tofile=f"b/{edit.path}",
        )
    )


def full_diff(edits: list[FileEdit]) -> str:
    return "\n".join(unified_diff(e) for e in edits if e.changed)


def apply_edits(root: Path, edits: list[FileEdit], branch: str) -> list[str]:
    """Create/checkout `branch`, write changed files, return list of
    modified relative paths."""
    repo = git.Repo(root)
    if branch in repo.heads:
        repo.heads[branch].checkout()
    else:
        repo.git.checkout("-b", branch)

    modified = []
    for edit in edits:
        if not edit.changed:
            continue
        full_path = Path(root) / edit.path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(edit.new)
        modified.append(edit.path)

    return modified

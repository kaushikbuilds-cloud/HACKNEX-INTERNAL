"""Turn FileEdits into a unified diff."""

from __future__ import annotations

import difflib

from backend.llm.code_generator import FileEdit


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

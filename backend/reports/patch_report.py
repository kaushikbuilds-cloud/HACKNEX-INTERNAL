from __future__ import annotations

from backend.llm.code_generator import FileEdit
from backend.patch.diff_generator import full_diff


def render_patch_report(edits: list[FileEdit]) -> dict:
    changed = [e.path for e in edits if e.changed]
    return {
        "files_changed": changed,
        "diff": full_diff(edits),
    }

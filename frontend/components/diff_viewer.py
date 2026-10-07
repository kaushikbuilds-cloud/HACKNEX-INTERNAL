"""Render the diff from the last agent run, split per file, with a toggle
between the raw unified diff and a side-by-side before/after view."""

from __future__ import annotations

import re
from pathlib import Path

import streamlit as st

from frontend.services.api_client import get_patch

FILE_HEADER_RE = re.compile(r"^--- a/(.+)$", re.MULTILINE)

_EXT_LANG = {
    ".py": "python", ".js": "javascript", ".jsx": "javascript",
    ".ts": "typescript", ".tsx": "typescript", ".go": "go",
    ".java": "java", ".rb": "ruby", ".php": "php", ".rs": "rust",
    ".c": "c", ".cpp": "cpp", ".cs": "csharp", ".html": "html",
    ".css": "css", ".json": "json", ".md": "markdown",
}


def _lang_for(path: str) -> str:
    return _EXT_LANG.get(Path(path).suffix, "text")


def _split_per_file(diff: str) -> list[tuple[str, str]]:
    """Split a concatenated unified diff into (filename, hunk_text) pairs."""
    if not diff.strip():
        return []
    chunks = []
    matches = list(FILE_HEADER_RE.finditer(diff))
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(diff)
        chunks.append((m.group(1), diff[start:end].rstrip()))
    return chunks


def render_diff_viewer() -> None:
    st.subheader("Patch diff")

    session_id = st.session_state.get("session_id")
    if not session_id or not st.session_state.get("last_plan"):
        st.info("No diff yet — run the agent on the **Chat Panel** page first.")
        return

    try:
        patch = get_patch(session_id)
    except Exception as exc:  # noqa: BLE001
        st.error(f"Could not fetch patch: {exc}")
        return

    diff = patch.get("diff", "")
    files = patch.get("files", [])
    st.session_state["last_diff"] = diff
    st.session_state["last_files_changed"] = patch.get("files_changed", [])

    if not diff.strip():
        st.info("The agent made no changes.")
        return

    view_mode = st.radio("View", ["Side-by-side", "Unified diff"], horizontal=True)

    if view_mode == "Unified diff":
        for filename, hunk in _split_per_file(diff):
            with st.expander(filename, expanded=True):
                st.code(hunk, language="diff")
        return

    for f in files:
        with st.expander(f["path"], expanded=True):
            lang = _lang_for(f["path"])
            left, right = st.columns(2)
            with left:
                st.caption("Before")
                st.code(f["original"], language=lang)
            with right:
                st.caption("After")
                st.code(f["new"], language=lang)

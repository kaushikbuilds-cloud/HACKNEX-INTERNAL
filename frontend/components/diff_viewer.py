"""Render the unified diff from the last agent run, split per file."""

from __future__ import annotations

import re

import streamlit as st

FILE_HEADER_RE = re.compile(r"^--- a/(.+)$", re.MULTILINE)


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

    diff = st.session_state.get("last_diff")
    if not diff:
        st.info("No diff yet — run the agent on the **Chat Panel** page first.")
        return

    for filename, hunk in _split_per_file(diff):
        with st.expander(filename, expanded=True):
            st.code(hunk, language="diff")

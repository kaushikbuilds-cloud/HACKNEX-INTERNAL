"""Render a RepositoryProfile summary (languages, build/test tooling,
file counts, top-level structure)."""

from __future__ import annotations

import streamlit as st


def render_repository_profile(profile: dict) -> None:
    if not profile:
        st.info("No repository loaded yet.")
        return

    cols = st.columns(4)
    cols[0].metric("Files", profile.get("file_count", 0))
    cols[1].metric("Languages", ", ".join(profile.get("languages", [])) or "—")
    cols[2].metric("Build tool", profile.get("build_tool") or "—")
    cols[3].metric("Test framework", profile.get("test_framework") or "—")

    if profile.get("test_command"):
        st.caption(f"Test command: `{profile['test_command']}`")

    structure = profile.get("structure") or {}
    if structure:
        st.write("**Top-level structure**")
        st.table(
            {"path": list(structure.keys()), "files": list(structure.values())}
        )

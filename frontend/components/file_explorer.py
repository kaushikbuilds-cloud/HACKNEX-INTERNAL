"""Simple top-level file/folder breakdown of the loaded repository."""

from __future__ import annotations

import streamlit as st


def render_file_explorer() -> None:
    st.subheader("Repository structure")

    profile = st.session_state.get("repo_profile")
    if not profile:
        st.info("Load a repository first on the **Repository Loader** page.")
        return

    structure = profile.get("structure") or {}
    if not structure:
        st.write("No files found.")
        return

    for top, count in sorted(structure.items(), key=lambda kv: -kv[1]):
        st.write(f"📁 `{top}` — {count} file(s)")

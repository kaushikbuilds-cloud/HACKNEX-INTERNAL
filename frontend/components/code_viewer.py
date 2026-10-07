"""List of files the agent touched in its last run. Full before/after
content lives in the diff viewer; this is the quick summary."""

from __future__ import annotations

import streamlit as st

from frontend.services.api_client import get_patch


def render_code_viewer() -> None:
    st.subheader("Files changed")

    session_id = st.session_state.get("session_id")
    if not session_id or not st.session_state.get("last_plan"):
        st.info("Run the agent on the **Chat Panel** page first.")
        return

    try:
        patch = get_patch(session_id)
    except Exception as exc:  # noqa: BLE001
        st.error(f"Could not fetch patch: {exc}")
        return

    files = patch.get("files_changed") or []
    st.session_state["last_diff"] = patch.get("diff", "")
    st.session_state["last_files_changed"] = files

    if not files:
        st.write("No files were changed.")
        return

    for f in files:
        st.write(f"✏️ `{f}`")

    st.caption("See the **Code and Diff Viewer** page's diff panel for the full unified diff.")

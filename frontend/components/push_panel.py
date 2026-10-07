"""Explicit, two-step confirmation before pushing the agent's committed
fix to GitHub. The agent never pushes on its own — this is the only path
that calls the push endpoint, and it only fires after the user clicks
"Yes, push it" on a second, separate confirmation step."""

from __future__ import annotations

import streamlit as st

from frontend.services.api_client import push_patch


def render_push_panel() -> None:
    if not st.session_state.get("last_success"):
        return  # nothing validated+committed to push yet

    branch = st.session_state.get("last_branch")
    if not branch:
        return

    st.divider()
    st.subheader("Push to GitHub")
    st.write(
        f"The fix passed validation and was committed locally on branch `{branch}`. "
        "It has **not** been pushed to GitHub yet."
    )

    if not st.session_state.get("push_confirm_armed"):
        if st.button("Push to GitHub", type="primary"):
            st.session_state["push_confirm_armed"] = True
            st.rerun()
        return

    st.warning(f"Really push branch `{branch}` to the `origin` remote on GitHub?")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Yes, push it", type="primary"):
            try:
                result = push_patch(st.session_state["session_id"], branch, confirm=True)
            except Exception as exc:  # noqa: BLE001
                st.error(f"Push failed: {exc}")
            else:
                st.success(result["message"])
            st.session_state["push_confirm_armed"] = False
    with col2:
        if st.button("Cancel"):
            st.session_state["push_confirm_armed"] = False
            st.rerun()

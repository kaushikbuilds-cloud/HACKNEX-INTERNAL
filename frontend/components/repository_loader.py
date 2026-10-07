"""Form for loading a repository (git URL or local path) and starting a session."""

from __future__ import annotations

import time

import streamlit as st

from frontend.services.api_client import load_repository


def render_repository_loader() -> None:
    st.subheader("Load a repository")
    source = st.text_input(
        "Git URL or local path",
        placeholder="https://github.com/owner/repo or /path/to/repo",
    )
    if st.button("Load repository", type="primary", disabled=not source):
        with st.spinner("Cloning, scanning, and indexing the repository..."):
            try:
                result = load_repository(source)
            except Exception as exc:  # noqa: BLE001 — surface any backend error to the user
                st.error(f"Failed to load repository: {exc}")
                return

        st.session_state["session_id"] = result["session_id"]
        st.session_state["repo_profile"] = result["profile"]
        st.session_state["baseline_tests_passed"] = result["baseline_tests_passed"]
        st.success(f"Repository loaded. Session: {result['session_id']}")

        if not result["baseline_tests_passed"]:
            st.warning(
                "Baseline tests are currently failing — that's expected if you're about "
                "to point the agent at a bug to fix."
            )

        st.info("Taking you to the Chat Panel...")
        time.sleep(1.2)
        st.switch_page("pages/2_Chat_Panel.py")

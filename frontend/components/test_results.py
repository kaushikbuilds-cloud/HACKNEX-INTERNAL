"""Render the baseline-vs-final test report for the current session."""

from __future__ import annotations

import streamlit as st

from frontend.services.api_client import get_test_report


def render_test_results() -> None:
    st.subheader("Test results")

    session_id = st.session_state.get("session_id")
    if not session_id or not st.session_state.get("last_plan"):
        st.info("Run the agent on the **Chat Panel** page first.")
        return

    try:
        data = get_test_report(session_id)
    except Exception as exc:  # noqa: BLE001
        st.error(f"Could not fetch test report: {exc}")
        return

    st.code(data["report"], language="text")

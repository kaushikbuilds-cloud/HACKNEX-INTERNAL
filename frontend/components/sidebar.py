"""Shared sidebar: current session status, quick nav context."""

from __future__ import annotations

import streamlit as st

from frontend.components.theme import apply_theme
from frontend.state.session_state import has_loaded_repo


def render_sidebar() -> None:
    apply_theme()
    with st.sidebar:
        st.markdown("### AI Software Engineering Agent")
        if has_loaded_repo():
            st.success(f"Session: `{st.session_state['session_id']}`")
            if st.session_state.get("baseline_tests_passed") is False:
                st.caption("⚠️ Baseline tests were failing when loaded")
            elif st.session_state.get("baseline_tests_passed"):
                st.caption("✅ Baseline tests were passing when loaded")
        else:
            st.info("No repository loaded — start on **Repository Loader**.")

        if st.session_state.get("last_confidence") is not None:
            st.metric("Last change confidence", f"{st.session_state['last_confidence']:.0%}")

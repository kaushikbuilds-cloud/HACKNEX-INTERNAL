"""Central place for the keys we keep in st.session_state, so pages don't
reach into raw dict keys scattered across the app."""

from __future__ import annotations

import streamlit as st

DEFAULTS = {
    "session_id": None,
    "repo_profile": None,
    "baseline_tests_passed": None,
    "last_plan": None,
    "last_explanation": None,
    "last_confidence": None,
    "last_diff": None,
    "last_files_changed": None,
}


def init_state() -> None:
    for key, default in DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = default


def has_loaded_repo() -> bool:
    return st.session_state.get("session_id") is not None


def reset_state() -> None:
    for key, default in DEFAULTS.items():
        st.session_state[key] = default

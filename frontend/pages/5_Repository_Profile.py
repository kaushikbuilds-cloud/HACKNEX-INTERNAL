import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from frontend.components.repository_profile import render_repository_profile
from frontend.components.sidebar import render_sidebar
from frontend.components.theme import page_header
from frontend.services.api_client import get_impact_report
from frontend.state.session_state import init_state

st.set_page_config(page_title="Repository Profile", page_icon="🗂️")
init_state()
render_sidebar()
page_header("🗂️ Repository Profile", "Repo summary, plus the impact analysis of the last change.")

render_repository_profile(st.session_state.get("repo_profile"))

if st.session_state.get("last_plan"):
    st.divider()
    st.subheader("Impact of the last change")
    try:
        impact = get_impact_report(st.session_state["session_id"])
    except Exception as exc:  # noqa: BLE001
        st.error(f"Could not fetch impact report: {exc}")
    else:
        st.write("**Files directly changed**")
        st.write(impact["files_directly_changed"] or "(none)")

        st.write("**Modules that import the changed files** (what else could be affected)")
        st.write(impact["modules_that_import_changed_files"] or "(none found)")

        st.write("**Risks the planner flagged**")
        st.write(impact["risks"] or "(none)")

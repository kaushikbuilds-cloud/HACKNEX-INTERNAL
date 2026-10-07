import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from frontend.components.sidebar import render_sidebar
from frontend.state.session_state import init_state

st.set_page_config(page_title="AI Software Engineering Agent", page_icon="🤖")
init_state()
render_sidebar()

st.title("AI Software Engineering Agent")
st.write(
    "Point this at a public repository, describe a bug or feature in plain "
    "English, and it will find the right files, make the change, and run "
    "the existing tests to confirm nothing broke."
)

st.markdown(
    """
**Workflow:**
1. **Repository Loader** — load a repo (git URL or local path); it's scanned and indexed.
2. **Chat Panel** — describe the change; the agent plans, edits, and validates it.
3. **Code and Diff Viewer** — see exactly what changed.
4. **Test Results** — see the before/after test run.
5. **Repository Profile** — repo summary and the change's impact analysis.
"""
)

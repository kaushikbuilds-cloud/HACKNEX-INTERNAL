import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from frontend.components.sidebar import render_sidebar
from frontend.components.theme import page_header
from frontend.state.session_state import init_state

st.set_page_config(page_title="AI Software Engineering Agent", page_icon="🤖")
init_state()
render_sidebar()

page_header(
    "🤖 AI Software Engineering Agent",
    "Reads a codebase, understands it, fixes a bug or adds a feature, and verifies nothing broke.",
)

st.write(
    "Point this at a public repository, describe a bug or feature in plain "
    "English, and it will find the right files, make the change, and run "
    "the existing tests to confirm nothing broke."
)

col1, col2, col3 = st.columns(3)
col1.markdown("**1. Repository Loader**\n\nLoad a repo; it's scanned and indexed.")
col2.markdown("**2. Chat Panel**\n\nDescribe the change; the agent plans, edits, and validates it.")
col3.markdown("**3. Review**\n\nDiff, test results, and impact analysis.")

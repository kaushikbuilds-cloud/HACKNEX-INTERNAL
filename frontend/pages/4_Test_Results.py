import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from frontend.components.sidebar import render_sidebar
from frontend.components.test_results import render_test_results
from frontend.state.session_state import init_state

st.set_page_config(page_title="Test Results", page_icon="✅")
init_state()
render_sidebar()

render_test_results()

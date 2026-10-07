import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from frontend.components.code_viewer import render_code_viewer
from frontend.components.diff_viewer import render_diff_viewer
from frontend.components.file_explorer import render_file_explorer
from frontend.components.push_panel import render_push_panel
from frontend.components.sidebar import render_sidebar
from frontend.components.theme import page_header
from frontend.state.session_state import init_state

st.set_page_config(page_title="Code and Diff Viewer", page_icon="🧾", layout="wide")
init_state()
render_sidebar()
page_header("🧾 Code and Diff Viewer", "Exactly what the agent changed, before vs. after.")

left, right = st.columns([1, 2])
with left:
    render_file_explorer()
    st.divider()
    render_code_viewer()
with right:
    render_diff_viewer()

render_push_panel()

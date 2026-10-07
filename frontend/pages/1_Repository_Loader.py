import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from frontend.components.repository_loader import render_repository_loader
from frontend.components.repository_profile import render_repository_profile
from frontend.components.sidebar import render_sidebar
from frontend.state.session_state import init_state

st.set_page_config(page_title="Repository Loader", page_icon="📂")
init_state()
render_sidebar()

render_repository_loader()
st.divider()
render_repository_profile(st.session_state.get("repo_profile"))

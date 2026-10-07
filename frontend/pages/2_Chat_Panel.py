import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from frontend.components.chat_panel import render_chat_panel
from frontend.components.sidebar import render_sidebar
from frontend.components.theme import page_header
from frontend.state.session_state import init_state

st.set_page_config(page_title="Chat Panel", page_icon="💬")
init_state()
render_sidebar()
page_header("💬 Chat Panel", "Describe the bug or feature; the agent plans, edits, and validates it.")

render_chat_panel()

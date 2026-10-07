"""Shared visual styling applied to every page — call once per page,
alongside init_state()/render_sidebar()."""

from __future__ import annotations

import streamlit as st

_CSS = """
<style>
:root {
    --accent: #4F46E5;
    --accent-light: #EEF2FF;
    --success: #16A34A;
    --danger: #DC2626;
}

/* App header banner */
.swe-header {
    background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%);
    padding: 1.5rem 2rem;
    border-radius: 12px;
    color: white;
    margin-bottom: 1.5rem;
}
.swe-header h1 {
    color: white;
    margin: 0;
    font-size: 1.6rem;
}
.swe-header p {
    color: #E0E7FF;
    margin: 0.3rem 0 0 0;
    font-size: 0.95rem;
}

/* Card-style containers for metrics/sections */
.swe-card {
    background: var(--accent-light);
    border: 1px solid #C7D2FE;
    border-radius: 10px;
    padding: 1rem 1.25rem;
    margin-bottom: 1rem;
}

/* Status pills */
.swe-pill {
    display: inline-block;
    padding: 0.2rem 0.7rem;
    border-radius: 999px;
    font-size: 0.8rem;
    font-weight: 600;
}
.swe-pill-success { background: #DCFCE7; color: #166534; }
.swe-pill-danger { background: #FEE2E2; color: #991B1B; }
.swe-pill-warning { background: #FEF3C7; color: #92400E; }

/* Tighter sidebar spacing */
section[data-testid="stSidebar"] .block-container {
    padding-top: 1.5rem;
}

/* Buttons: rounded, accent color */
.stButton > button {
    border-radius: 8px;
    font-weight: 600;
}
.stButton > button[kind="primary"] {
    background-color: var(--accent);
    border-color: var(--accent);
}
</style>
"""


def apply_theme() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


def page_header(title: str, subtitle: str = "") -> None:
    sub_html = f"<p>{subtitle}</p>" if subtitle else ""
    st.markdown(
        f'<div class="swe-header"><h1>{title}</h1>{sub_html}</div>',
        unsafe_allow_html=True,
    )


def status_pill(text: str, kind: str = "success") -> str:
    return f'<span class="swe-pill swe-pill-{kind}">{text}</span>'

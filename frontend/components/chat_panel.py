"""The core interaction: describe the bug/feature in natural language, run
the agent, and show what it understood + whether it worked."""

from __future__ import annotations

import time

import streamlit as st

from frontend.services.api_client import send_chat
from frontend.state.session_state import has_loaded_repo


def render_chat_panel() -> None:
    st.subheader("Describe the change")

    if not has_loaded_repo():
        st.info("Load a repository first on the **Repository Loader** page.")
        return

    message = st.text_area(
        "What should the agent do?",
        placeholder="e.g. Fix the bug in mathlib.ops.add: it should add, not subtract.",
        height=100,
    )
    branch = st.text_input("Branch name", value="swe-agent/auto-fix")

    if st.button("Run agent", type="primary", disabled=not message):
        with st.status("Running the agent...", expanded=True) as status:
            st.write("🔍 Retrieving relevant code from the index")
            st.write("🧠 Planning the change")
            st.write("✍️ Generating code")
            st.write("✅ Validating (tests, static analysis, security scan)")
            st.caption("This is a single request to the backend — steps above run in order "
                       "on the server and can take a while on a local model.")
            try:
                result = send_chat(st.session_state["session_id"], message, branch)
            except Exception as exc:  # noqa: BLE001
                status.update(label="Agent run failed", state="error", expanded=True)
                st.error(f"Agent run failed: {exc}")
                return

            status.update(
                label="Done — validation passed" if result["success"] else "Done — validation failed",
                state="complete" if result["success"] else "error",
                expanded=False,
            )

        st.session_state["last_plan"] = result["plan"]
        st.session_state["last_explanation"] = result["explanation"]
        st.session_state["last_confidence"] = result["confidence"]

        if result["success"]:
            st.success(f"Change succeeded after {result['attempts']} attempt(s).")
        else:
            st.error(f"Change did not pass validation after {result['attempts']} attempt(s).")

        st.markdown("**Explanation**")
        st.text(result["explanation"])
        st.caption(f"Confidence: {result['confidence']:.0%}")

        st.markdown("**Plan**")
        st.json(result["plan"])

        st.info("Taking you to the Code and Diff Viewer...")
        time.sleep(1.2)
        st.switch_page("pages/3_Code_and_Diff_Viewer.py")

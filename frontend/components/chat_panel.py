"""The core interaction: describe the bug/feature in natural language, run
the agent, and show what it understood + whether it worked.

Two distinct modes, kept deliberately separate so they can't blur
together: "Fix" plans, edits, validates, and commits; "Find bugs" only
ever reads the repo and reports findings — it calls a completely
different backend endpoint that has no access to patch/git code at all."""

from __future__ import annotations

import time

import streamlit as st

from frontend.components.theme import status_pill
from frontend.services.api_client import analyze_repo, send_chat
from frontend.state.session_state import has_loaded_repo

_MERGE_STATUS_PILL_KIND = {
    "READY": "success",
    "REVIEW_RECOMMENDED": "warning",
    "BLOCKED": "danger",
}
_MERGE_STATUS_LABEL = {
    "READY": "Ready to merge",
    "REVIEW_RECOMMENDED": "Review recommended",
    "BLOCKED": "Blocked",
}
_SEVERITY_PILL_KIND = {"high": "danger", "medium": "warning", "low": "success"}


def render_chat_panel() -> None:
    st.subheader("Describe the change")

    if not has_loaded_repo():
        st.info("Load a repository first on the **Repository Loader** page.")
        return

    mode = st.radio(
        "What do you want the agent to do?",
        ["Fix a specific issue", "Find bugs (read-only)"],
        horizontal=True,
    )

    if mode == "Find bugs (read-only)":
        _render_analyze_mode()
    else:
        _render_fix_mode()


def _render_fix_mode() -> None:
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
        st.session_state["last_branch"] = branch
        st.session_state["last_success"] = result["success"]

        if result["success"]:
            st.success(f"Change succeeded after {result['attempts']} attempt(s).")
        else:
            st.error(f"Change did not pass validation after {result['attempts']} attempt(s).")

        st.markdown("**Explanation**")
        st.text(result["explanation"])
        st.caption(f"Confidence: {result['confidence']:.0%}")

        ms = result.get("merge_status")
        if ms:
            kind = _MERGE_STATUS_PILL_KIND.get(ms["status"], "warning")
            label = _MERGE_STATUS_LABEL.get(ms["status"], ms["status"])
            st.markdown(f"**Merge status:** {status_pill(label, kind)}", unsafe_allow_html=True)
            if ms["reasons"]:
                st.markdown("Reasons:\n" + "\n".join(f"- {r}" for r in ms["reasons"]))
            if ms["suggested_actions"]:
                st.markdown("Suggested actions:\n" + "\n".join(f"- {a}" for a in ms["suggested_actions"]))
            st.caption(
                "This is advisory — you decide whether to push regardless of status."
            )

        st.markdown("**Plan**")
        st.json(result["plan"])

        st.info("Taking you to the Code and Diff Viewer...")
        time.sleep(1.2)
        st.switch_page("pages/3_Code_and_Diff_Viewer.py")


def _render_analyze_mode() -> None:
    st.caption(
        "Read-only: scans the repo for bugs and reports them. Never edits, "
        "commits, or pushes anything."
    )
    message = st.text_area(
        "Anything specific to focus on? (optional)",
        placeholder="e.g. focus on the authentication code",
        height=80,
    )

    if st.button("Find bugs", type="primary"):
        with st.spinner("Scanning for bugs (static analysis, security scan, and LLM review)..."):
            try:
                result = analyze_repo(st.session_state["session_id"], message)
            except Exception as exc:  # noqa: BLE001
                st.error(f"Analysis failed: {exc}")
                return

        if not result.get("llm_available", True):
            st.info(
                "The local LLM wasn't reachable, so these are deterministic static-analysis "
                "and security-scan findings only (no false negatives from that scan, but no "
                "LLM-reasoned logic bugs either). Start Ollama and re-run to also get those."
            )

        findings = result.get("findings", [])
        if not findings:
            st.success("No bugs found in the reviewed code.")
        else:
            st.warning(f"{len(findings)} finding(s):")
            for f in findings:
                kind = _SEVERITY_PILL_KIND.get(f["severity"], "warning")
                location = f"{f['file']}:{f['line']}" if f.get("line") else f["file"]
                st.markdown(
                    f"{status_pill(f['severity'].upper(), kind)} **{location}** "
                    f"<span style='color:#888'>({f.get('source', 'llm')})</span>",
                    unsafe_allow_html=True,
                )
                st.write(f["description"])
                st.divider()

        with st.expander("Static analysis summary"):
            st.text(result.get("static_summary", ""))
        with st.expander("Security scan summary"):
            st.text(result.get("security_summary", ""))

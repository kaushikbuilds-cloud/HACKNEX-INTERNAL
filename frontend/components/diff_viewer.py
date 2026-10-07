"""Render the diff from the last agent run, split per file, with a toggle
between the raw unified diff and a real line-level side-by-side view
(added/removed/changed lines colored, not just two full-file dumps)."""

from __future__ import annotations

import difflib
import html
import re
from pathlib import Path

import streamlit as st

from frontend.services.api_client import get_patch

FILE_HEADER_RE = re.compile(r"^--- a/(.+)$", re.MULTILINE)

_EXT_LANG = {
    ".py": "python", ".js": "javascript", ".jsx": "javascript",
    ".ts": "typescript", ".tsx": "typescript", ".go": "go",
    ".java": "java", ".rb": "ruby", ".php": "php", ".rs": "rust",
    ".c": "c", ".cpp": "cpp", ".cs": "csharp", ".html": "html",
    ".css": "css", ".json": "json", ".md": "markdown",
}

_DIFF_CSS = """
<style>
.swe-diff-table { width: 100%; border-collapse: collapse; font-family: "SF Mono", Monaco, Consolas, monospace;
                   font-size: 0.82rem; table-layout: fixed; border: 1px solid #E5E7EB; border-radius: 8px;
                   overflow: hidden; margin-bottom: 0.5rem; }
.swe-diff-table col.gutter { width: 44px; }
.swe-diff-table col.code { width: 50%; }
.swe-diff-table td { padding: 1px 8px; vertical-align: top; white-space: pre-wrap; word-break: break-word; }
.swe-diff-table td.gutter { color: #9CA3AF; text-align: right; user-select: none; background: #FAFAFA;
                             border-right: 1px solid #F0F0F0; }
.swe-diff-row-equal td.code { background: #FFFFFF; }
.swe-diff-row-del td.code.left { background: #FEE2E2; }
.swe-diff-row-add td.code.right { background: #DCFCE7; }
.swe-diff-row-rep td.code.left { background: #FEF3C7; }
.swe-diff-row-rep td.code.right { background: #FEF9E7; }
.swe-diff-empty td.code { background: #FAFAFA; }
.swe-diff-stats { font-size: 0.85rem; color: #4B5563; margin-bottom: 0.35rem; }
.swe-diff-stats .add { color: #166534; font-weight: 600; }
.swe-diff-stats .del { color: #991B1B; font-weight: 600; }
</style>
"""


def _lang_for(path: str) -> str:
    return _EXT_LANG.get(Path(path).suffix, "text")


def _split_per_file(diff: str) -> list[tuple[str, str]]:
    """Split a concatenated unified diff into (filename, hunk_text) pairs."""
    if not diff.strip():
        return []
    chunks = []
    matches = list(FILE_HEADER_RE.finditer(diff))
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(diff)
        chunks.append((m.group(1), diff[start:end].rstrip()))
    return chunks


def _esc(line: str) -> str:
    return html.escape(line) if line else "&nbsp;"


def _diff_stats(original: str, new: str) -> tuple[int, int]:
    """(added, removed) line counts, computed the same way git would."""
    orig_lines = original.splitlines()
    new_lines = new.splitlines()
    sm = difflib.SequenceMatcher(None, orig_lines, new_lines)
    added = removed = 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "replace":
            removed += i2 - i1
            added += j2 - j1
        elif tag == "delete":
            removed += i2 - i1
        elif tag == "insert":
            added += j2 - j1
    return added, removed


def _render_line_diff_table(original: str, new: str) -> str:
    """GitHub-style split diff: equal lines side by side, deletions
    highlighted on the left, insertions on the right, replaced lines
    highlighted on both sides — built with difflib so it reflects the
    actual line-level change, not just two unrelated full-file dumps."""
    orig_lines = original.splitlines()
    new_lines = new.splitlines()
    sm = difflib.SequenceMatcher(None, orig_lines, new_lines)

    rows = ['<table class="swe-diff-table"><colgroup>'
            '<col class="gutter"><col class="code"><col class="gutter"><col class="code">'
            '</colgroup><tbody>']

    def row(row_cls: str, lno_l, text_l, side_l_cls, lno_r, text_r, side_r_cls):
        rows.append(
            f'<tr class="{row_cls}">'
            f'<td class="gutter">{lno_l if lno_l is not None else ""}</td>'
            f'<td class="code {side_l_cls}">{text_l}</td>'
            f'<td class="gutter">{lno_r if lno_r is not None else ""}</td>'
            f'<td class="code {side_r_cls}">{text_r}</td>'
            f'</tr>'
        )

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k, (li, lj) in enumerate(zip(range(i1, i2), range(j1, j2))):
                row("swe-diff-row-equal", li + 1, _esc(orig_lines[li]), "left",
                    lj + 1, _esc(new_lines[lj]), "right")
        elif tag == "replace":
            span = max(i2 - i1, j2 - j1)
            for k in range(span):
                li, lj = i1 + k, j1 + k
                left = (li + 1, _esc(orig_lines[li]), "left") if li < i2 else (None, "&nbsp;", "")
                right = (lj + 1, _esc(new_lines[lj]), "right") if lj < j2 else (None, "&nbsp;", "")
                row("swe-diff-row-rep", left[0], left[1], left[2], right[0], right[1], right[2])
        elif tag == "delete":
            for li in range(i1, i2):
                row("swe-diff-row-del", li + 1, _esc(orig_lines[li]), "left", None, "&nbsp;", "")
        elif tag == "insert":
            for lj in range(j1, j2):
                row("swe-diff-row-add", None, "&nbsp;", "", lj + 1, _esc(new_lines[lj]), "right")

    rows.append("</tbody></table>")
    return "".join(rows)


def render_diff_viewer() -> None:
    st.subheader("Patch diff")
    st.markdown(_DIFF_CSS, unsafe_allow_html=True)

    session_id = st.session_state.get("session_id")
    if not session_id or not st.session_state.get("last_plan"):
        st.info("No diff yet — run the agent on the **Chat Panel** page first.")
        return

    try:
        patch = get_patch(session_id)
    except Exception as exc:  # noqa: BLE001
        st.error(f"Could not fetch patch: {exc}")
        return

    diff = patch.get("diff", "")
    files = patch.get("files", [])
    st.session_state["last_diff"] = diff
    st.session_state["last_files_changed"] = patch.get("files_changed", [])

    if not diff.strip():
        st.info("The agent made no changes.")
        return

    total_added = total_removed = 0
    stats_by_file = {}
    for f in files:
        added, removed = _diff_stats(f["original"], f["new"])
        stats_by_file[f["path"]] = (added, removed)
        total_added += added
        total_removed += removed

    st.caption(
        f"{len(files)} file(s) changed · "
        f"<span class='add' style='color:#166534;font-weight:600'>+{total_added}</span> "
        f"<span class='del' style='color:#991B1B;font-weight:600'>-{total_removed}</span>",
        unsafe_allow_html=True,
    )

    view_mode = st.radio("View", ["Side-by-side", "Unified diff"], horizontal=True)

    if view_mode == "Unified diff":
        for filename, hunk in _split_per_file(diff):
            with st.expander(filename, expanded=True):
                st.code(hunk, language="diff", wrap_lines=True, line_numbers=True)
        return

    for f in files:
        added, removed = stats_by_file.get(f["path"], (0, 0))
        label = f"{f['path']}  (+{added} / -{removed})"
        with st.expander(label, expanded=True):
            if f["original"] == f["new"]:
                st.caption("No textual change.")
                continue
            table_html = _render_line_diff_table(f["original"], f["new"])
            st.markdown(table_html, unsafe_allow_html=True)

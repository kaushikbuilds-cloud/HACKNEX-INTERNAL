"""Diff viewer endpoint: the unified diff produced by the last chat turn."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.core.sessions import get_session

router = APIRouter(prefix="/patch", tags=["patch"])


@router.get("/{session_id}")
def get_patch(session_id: str):
    session = get_session(session_id)
    if session is None:
        raise HTTPException(404, "session not found")
    if session.heal is None:
        raise HTTPException(400, "no change has been generated yet")

    return {
        "diff": session.diff,
        "files_changed": [e.path for e in session.heal.edits if e.changed],
        "files": [
            {"path": e.path, "original": e.original, "new": e.new}
            for e in session.heal.edits
            if e.changed
        ],
    }

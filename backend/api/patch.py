"""Diff viewer endpoint: the unified diff produced by the last chat turn,
plus the explicitly user-confirmed push-to-GitHub step."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.core.sessions import get_session
from backend.patch.git_manager import push_branch

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


class PushRequest(BaseModel):
    session_id: str
    branch: str
    confirm: bool  # must be explicitly true — this is the user's "yes, push it"


@router.post("/push")
def push_patch(req: PushRequest):
    if not req.confirm:
        raise HTTPException(400, "Push requires explicit confirmation (confirm=true).")

    session = get_session(req.session_id)
    if session is None or session.root is None:
        raise HTTPException(404, "session not found")
    if session.heal is None or not session.heal.report.passed:
        raise HTTPException(400, "No successful, validated change to push yet.")

    try:
        result = push_branch(session.root, req.branch)
    except RuntimeError as exc:
        raise HTTPException(400, str(exc))

    return {"pushed": True, "message": result}

"""Repository Loader endpoint: clone/scan/index a repo, start a session."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.core.config import settings
from backend.core.sessions import create_session, get_session
from backend.embeddings.vector_search import build_index
from backend.reports.repository_summary import render_repository_summary
from backend.repository.clone_repo import resolve_target
from backend.repository.scanner import scan_repo
from backend.testing.validator import run_validation

router = APIRouter(prefix="/repository", tags=["repository"])


class LoadRepoRequest(BaseModel):
    source: str  # git URL or local path


@router.post("/load")
def load_repository(req: LoadRepoRequest):
    session = create_session()
    root = resolve_target(req.source, Path(settings.workdir))
    profile = scan_repo(root)
    baseline = run_validation(root, profile)
    store = build_index(root)

    session.root = root
    session.profile = profile
    session.store = store
    session.baseline = baseline

    return {
        "session_id": session.id,
        "profile": render_repository_summary(profile),
        "baseline_tests_passed": baseline.passed,
    }


@router.get("/{session_id}/profile")
def get_profile(session_id: str):
    session = get_session(session_id)
    if session is None or session.profile is None:
        raise HTTPException(404, "session not found")
    return render_repository_summary(session.profile)

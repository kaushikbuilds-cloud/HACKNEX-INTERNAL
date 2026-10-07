"""Repository Loader endpoint: clone/scan/index a repo, start a session."""

from __future__ import annotations

from pathlib import Path

import git
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.core.config import settings
from backend.core.sessions import create_session, get_session
from backend.embeddings.vector_search import build_index
from backend.reports.repository_summary import render_repository_summary
from backend.repository.clone_repo import resolve_target
from backend.repository.scanner import scan_repo
from backend.sandbox.venv_manager import build_sandbox
from backend.testing.validator import run_validation

router = APIRouter(prefix="/repository", tags=["repository"])


class LoadRepoRequest(BaseModel):
    source: str  # git URL or local path


@router.post("/load")
def load_repository(req: LoadRepoRequest):
    session = create_session()
    root = resolve_target(req.source, Path(settings.workdir))
    profile = scan_repo(root)

    # Isolated venv for *this repo's own* dependencies, so a missing package
    # (e.g. a target repo's python-jose) never crashes against the host's
    # environment and never leaks between sessions loading different repos.
    # Best-effort: falls back to the host interpreter on any failure, so a
    # sandbox problem never blocks loading the repo.
    sandbox_dir = Path(settings.workdir) / ".sandboxes" / session.id
    session.sandbox = build_sandbox(root, sandbox_dir)

    baseline = run_validation(root, profile, python_executable=session.python_executable)
    store = build_index(root)

    session.root = root
    session.profile = profile
    session.store = store
    session.baseline = baseline
    try:
        session.base_ref = git.Repo(root).active_branch.name
    except (git.InvalidGitRepositoryError, TypeError):
        session.base_ref = None  # not a git repo, or detached HEAD — can't roll back later

    return {
        "session_id": session.id,
        "profile": render_repository_summary(profile),
        "baseline_tests_passed": baseline.passed,
        "sandbox": {
            "isolated": session.sandbox.isolated,
            "warnings": session.sandbox.warnings,
        },
    }


@router.get("/{session_id}/profile")
def get_profile(session_id: str):
    session = get_session(session_id)
    if session is None or session.profile is None:
        raise HTTPException(404, "session not found")
    return render_repository_summary(session.profile)

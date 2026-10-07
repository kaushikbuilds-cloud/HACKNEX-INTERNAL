"""If validation never converges after all retry attempts, undo the
agent's changes rather than leaving a broken branch behind."""

from __future__ import annotations

from pathlib import Path

import git


def rollback_to(root: Path, base_ref: str, work_branch: str | None = None) -> None:
    """Switch back to `base_ref` (the branch/ref the repo was on before the
    agent touched anything) and delete `work_branch` if it was created for
    this attempt, so nothing broken is left lying around."""
    repo = git.Repo(root)

    # Discard any uncommitted edits on the current (work) branch first, so
    # checkout doesn't refuse to switch over local changes.
    repo.git.checkout("--", ".")
    repo.git.clean("-fd")

    repo.git.checkout(base_ref)

    if work_branch and work_branch != base_ref and work_branch in repo.heads:
        repo.git.branch("-D", work_branch)

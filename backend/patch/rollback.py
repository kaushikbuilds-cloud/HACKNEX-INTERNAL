"""If validation never converges, undo the agent's changes rather than
leaving a broken working tree behind."""

from __future__ import annotations

from pathlib import Path

import git


def rollback_to(root: Path, ref: str) -> None:
    """Hard-reset the current branch's working tree back to `ref`
    (e.g. the branch we started from) and discard untracked agent edits."""
    repo = git.Repo(root)
    repo.git.checkout(ref, "--", ".")
    repo.git.clean("-fd")

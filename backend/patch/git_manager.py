"""Git branch management for the agent's changes: create/checkout the work
branch, and report which branch we're on."""

from __future__ import annotations

from pathlib import Path

import git


def ensure_branch(root: Path, branch: str) -> git.Repo:
    repo = git.Repo(root)
    if branch in repo.heads:
        repo.heads[branch].checkout()
    else:
        repo.git.checkout("-b", branch)
    return repo


def current_branch(root: Path) -> str:
    return git.Repo(root).active_branch.name


def commit_all(root: Path, message: str) -> None:
    repo = git.Repo(root)
    repo.git.add(A=True)
    if repo.is_dirty():
        repo.index.commit(message)

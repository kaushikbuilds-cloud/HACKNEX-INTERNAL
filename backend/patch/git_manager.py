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


def has_remote(root: Path, remote: str = "origin") -> bool:
    repo = git.Repo(root)
    return remote in [r.name for r in repo.remotes]


def push_branch(root: Path, branch: str, remote: str = "origin") -> str:
    """Push `branch` to `remote`. Never called automatically — the caller
    (the API layer) only invokes this after the user has explicitly
    confirmed they want to push. Returns a short human-readable result."""
    repo = git.Repo(root)
    if not has_remote(root, remote):
        raise RuntimeError(f"No '{remote}' remote configured for this repo.")

    remote_obj = repo.remote(remote)
    push_info = remote_obj.push(refspec=f"{branch}:{branch}", set_upstream=True)

    for info in push_info:
        if info.flags & info.ERROR:
            raise RuntimeError(f"Push failed: {info.summary}")

    return f"Pushed '{branch}' to '{remote}'."

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


def checkout(root: Path, ref: str) -> None:
    git.Repo(root).git.checkout(ref)

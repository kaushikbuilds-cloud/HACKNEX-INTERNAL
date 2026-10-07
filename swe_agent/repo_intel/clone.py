"""Workflow 1, step 1-2: get a repository onto disk."""

from __future__ import annotations

from pathlib import Path

import git


def clone_repo(url: str, dest: Path, ref: str | None = None) -> Path:
    """Clone a public repo into dest. If dest already has a .git dir, reuse it
    (fetch + checkout) instead of re-cloning."""
    dest = Path(dest)
    if (dest / ".git").exists():
        repo = git.Repo(dest)
        repo.remotes.origin.fetch()
    else:
        dest.parent.mkdir(parents=True, exist_ok=True)
        repo = git.Repo.clone_from(url, dest)

    if ref:
        repo.git.checkout(ref)

    return dest


def resolve_target(source: str, workdir: Path) -> Path:
    """`source` is either a local path or a git URL. Returns a local path
    the rest of the pipeline can read/write."""
    p = Path(source)
    if p.exists():
        return p
    name = source.rstrip("/").rsplit("/", 1)[-1].removesuffix(".git")
    return clone_repo(source, workdir / name)

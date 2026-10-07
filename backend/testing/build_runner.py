from __future__ import annotations

from pathlib import Path

from backend.repository.repository_profile import RepositoryProfile


def run_build(root: Path, profile: RepositoryProfile, python_executable: str | None = None):
    from backend.testing.validator import CommandResult, run_command

    if not profile.build_command:
        return None
    return run_command(profile.build_command, root, python_executable=python_executable)

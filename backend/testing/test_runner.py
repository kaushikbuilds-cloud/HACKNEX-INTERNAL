from __future__ import annotations

from pathlib import Path

from backend.repository.repository_profile import RepositoryProfile


def run_tests(root: Path, profile: RepositoryProfile):
    from backend.testing.validator import run_command

    if not profile.test_command:
        return None
    return run_command(profile.test_command, root)

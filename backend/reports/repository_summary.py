from __future__ import annotations

from backend.repository.repository_profile import RepositoryProfile


def render_repository_summary(profile: RepositoryProfile) -> dict:
    return {
        "languages": profile.languages,
        "build_tool": profile.build_tool,
        "test_framework": profile.test_framework,
        "test_command": profile.test_command,
        "file_count": profile.file_count,
        "structure": profile.structure,
    }

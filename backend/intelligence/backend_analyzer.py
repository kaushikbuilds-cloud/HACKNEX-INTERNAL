"""Detect which backend framework a repo uses, from import/dependency
signatures — informs how the planner reasons about routes, models, etc."""

from __future__ import annotations

from pathlib import Path

from backend.utils.file_utils import safe_read_text

FRAMEWORK_MARKERS = {
    "fastapi": ["fastapi"],
    "flask": ["flask"],
    "django": ["django"],
    "express": ["express"],
    "nestjs": ["@nestjs/core"],
    "spring": ["spring-boot-starter"],
}


def analyze_backend(root: Path) -> dict:
    root = Path(root)
    req = safe_read_text(root / "requirements.txt").lower()
    pyproject = safe_read_text(root / "pyproject.toml").lower()
    pkg = safe_read_text(root / "package.json").lower()
    haystack = req + pyproject + pkg

    frameworks = [name for name, markers in FRAMEWORK_MARKERS.items() if any(m in haystack for m in markers)]
    return {
        "frameworks": frameworks,
        "has_backend_dir": (root / "backend").is_dir(),
    }

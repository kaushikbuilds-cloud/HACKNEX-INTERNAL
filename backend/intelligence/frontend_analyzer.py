"""Detect which frontend framework a repo uses."""

from __future__ import annotations

import json
from pathlib import Path

from backend.utils.file_utils import safe_read_text

FRONTEND_DEPS = {
    "react": "react",
    "vue": "vue",
    "angular": "@angular/core",
    "svelte": "svelte",
    "nextjs": "next",
    "streamlit": None,  # detected via python import, not package.json
}


def analyze_frontend(root: Path) -> dict:
    root = Path(root)
    frameworks: list[str] = []

    pkg_text = safe_read_text(root / "package.json")
    if pkg_text:
        try:
            data = json.loads(pkg_text)
            deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
            frameworks.extend(name for name, dep in FRONTEND_DEPS.items() if dep and dep in deps)
        except json.JSONDecodeError:
            pass

    req_text = safe_read_text(root / "requirements.txt")
    if "streamlit" in req_text.lower():
        frameworks.append("streamlit")

    return {
        "frameworks": frameworks,
        "has_frontend_dir": (root / "frontend").is_dir(),
    }

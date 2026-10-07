"""Surface the config/env files present, so the planner knows what's
build/deploy config vs. application code."""

from __future__ import annotations

from pathlib import Path

from backend.core.constants import CONFIG_FILENAMES


def analyze_config(root: Path) -> list[str]:
    root = Path(root)
    return sorted(
        str(p.relative_to(root))
        for p in root.iterdir()
        if p.is_file() and (p.name in CONFIG_FILENAMES or p.name.startswith(".env"))
    )

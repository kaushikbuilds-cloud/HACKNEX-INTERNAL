from __future__ import annotations

from pathlib import Path

from backend.core.constants import IGNORE_DIRS


def safe_read_text(path: Path) -> str:
    try:
        return path.read_text(errors="ignore")
    except OSError:
        return ""


def walk_files(root: Path):
    root = Path(root)
    for p in root.rglob("*"):
        if p.is_file() and not any(part in IGNORE_DIRS for part in p.parts):
            yield p

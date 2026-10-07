"""Detect ORM / database usage so schema-touching changes get flagged."""

from __future__ import annotations

from pathlib import Path

from backend.utils.file_utils import safe_read_text

DB_MARKERS = {
    "sqlalchemy": ["sqlalchemy"],
    "django-orm": ["django.db"],
    "mongoose": ["mongoose"],
    "prisma": ["prisma"],
    "sqlite": ["sqlite3", ".db"],
}


def analyze_database(root: Path) -> dict:
    root = Path(root)
    req = safe_read_text(root / "requirements.txt").lower()
    pkg = safe_read_text(root / "package.json").lower()
    haystack = req + pkg

    systems = [name for name, markers in DB_MARKERS.items() if any(m in haystack for m in markers)]
    has_migrations = (root / "migrations").is_dir() or (root / "alembic").is_dir()

    return {"systems": systems, "has_migrations_dir": has_migrations}

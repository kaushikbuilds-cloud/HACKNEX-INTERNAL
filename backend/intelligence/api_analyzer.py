"""Find HTTP route definitions (FastAPI/Flask-style decorators) so the
planner knows which files define the public API surface."""

from __future__ import annotations

import re
from pathlib import Path

from backend.repository.parser import iter_source_files
from backend.utils.file_utils import safe_read_text

ROUTE_RE = re.compile(
    r'@\w+\.(get|post|put|patch|delete)\(\s*["\']([^"\']+)'
)


def analyze_api(root: Path) -> list[dict]:
    root = Path(root)
    routes = []
    for path in iter_source_files(root):
        if path.suffix != ".py":
            continue
        source = safe_read_text(path)
        for match in ROUTE_RE.finditer(source):
            routes.append(
                {
                    "file": str(path.relative_to(root)),
                    "method": match.group(1).upper(),
                    "path": match.group(2),
                }
            )
    return routes

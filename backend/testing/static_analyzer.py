"""Layer 3 (always-on): static analysis via ast.parse() + pyflakes.
Catches syntax errors, undefined names, and unused imports without
executing any code — safe to run on any repo, including ones we don't
trust, and cheap enough to run on every validation pass."""

from __future__ import annotations

import ast
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from backend.repository.parser import iter_source_files
from backend.utils.file_utils import safe_read_text

PYFLAKES_LINE_RE = re.compile(r"^(?P<file>[^:]+):(?P<line>\d+):\d*:?\s*(?P<message>.+)$")


@dataclass
class StaticIssue:
    file: str
    line: int
    severity: str  # "error" | "warning"
    code: str  # "syntax-error" | "pyflakes"
    message: str


@dataclass
class StaticReport:
    issues: list[StaticIssue] = field(default_factory=list)
    files_checked: int = 0
    syntax_errors: int = 0

    @property
    def passed(self) -> bool:
        return self.syntax_errors == 0

    def summary(self) -> str:
        if not self.issues:
            return f"static analysis: OK ({self.files_checked} files checked)"
        lines = [f"static analysis: {len(self.issues)} issue(s) in {self.files_checked} files"]
        for issue in self.issues[:20]:
            lines.append(f"  {issue.file}:{issue.line} [{issue.severity}] {issue.message}")
        if len(self.issues) > 20:
            lines.append(f"  ... and {len(self.issues) - 20} more")
        return "\n".join(lines)


def run_ast_check(path: str, content: str) -> list[StaticIssue]:
    try:
        ast.parse(content)
    except SyntaxError as exc:
        return [
            StaticIssue(
                file=path,
                line=exc.lineno or 1,
                severity="error",
                code="syntax-error",
                message=str(exc.msg),
            )
        ]
    return []


def run_pyflakes_check(root: Path) -> list[StaticIssue]:
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pyflakes", "."],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []  # pyflakes not installed or too slow — skip gracefully

    issues = []
    for line in (proc.stdout or "").splitlines():
        m = PYFLAKES_LINE_RE.match(line)
        if not m:
            continue
        issues.append(
            StaticIssue(
                file=m.group("file").lstrip("./"),
                line=int(m.group("line")),
                severity="warning",
                code="pyflakes",
                message=m.group("message"),
            )
        )
    return issues


def run_static_analysis(root: Path) -> StaticReport:
    root = Path(root)
    issues: list[StaticIssue] = []
    files_checked = 0

    for path in iter_source_files(root):
        if path.suffix != ".py":
            continue
        files_checked += 1
        rel = str(path.relative_to(root))
        content = safe_read_text(path)
        issues.extend(run_ast_check(rel, content))

    issues.extend(run_pyflakes_check(root))

    syntax_errors = sum(1 for i in issues if i.code == "syntax-error")
    return StaticReport(issues=issues, files_checked=files_checked, syntax_errors=syntax_errors)

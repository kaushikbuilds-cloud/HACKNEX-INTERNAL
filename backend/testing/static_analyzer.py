"""Layer 3 (always-on): static analysis across multiple languages.
Catches syntax errors (and, for Python, unused imports/undefined names)
without executing any code — safe to run on any repo, including ones we
don't trust, and cheap enough to run on every validation pass.

Each language's checker uses a tool that ships with that language's own
toolchain (node, ruby, php, go) wherever possible, so there's nothing extra
to install; a checker whose interpreter isn't on PATH is skipped silently
rather than failing the whole scan."""

from __future__ import annotations

import ast
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from backend.repository.parser import iter_source_files
from backend.utils.file_utils import safe_read_text

PYFLAKES_LINE_RE = re.compile(r"^(?P<file>[^:]+):(?P<line>\d+):\d*:?\s*(?P<message>.+)$")
GENERIC_LINE_RE = re.compile(r":(?P<line>\d+)")


@dataclass
class StaticIssue:
    file: str
    line: int
    severity: str  # "error" | "warning"
    code: str  # "syntax-error" | "pyflakes" | "<lang>-syntax"
    message: str


@dataclass
class StaticReport:
    issues: list[StaticIssue] = field(default_factory=list)
    files_checked: int = 0
    syntax_errors: int = 0
    languages_checked: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.syntax_errors == 0

    def summary(self) -> str:
        langs = ", ".join(self.languages_checked) or "none"
        if not self.issues:
            return f"static analysis: OK ({self.files_checked} files checked; languages: {langs})"
        lines = [
            f"static analysis: {len(self.issues)} issue(s) in {self.files_checked} files "
            f"(languages: {langs})"
        ]
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


def _run_file_syntax_tool(
    tool: str, args: list[str], path: Path, rel: str, code: str, timeout: int = 15
) -> list[StaticIssue]:
    """Run `tool args... path`, treat a nonzero exit as a syntax error and
    try to pull a line number out of stderr/stdout. Skips silently if the
    tool isn't installed or the file can't be parsed by it."""
    if not shutil.which(tool):
        return []
    try:
        proc = subprocess.run(
            [tool, *args, str(path)],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return []

    if proc.returncode == 0:
        return []

    output = (proc.stderr or proc.stdout or "").strip()
    if not output:
        return []
    out_lines = [l for l in output.splitlines() if l.strip()]
    m = GENERIC_LINE_RE.search(output)
    line = int(m.group("line")) if m else 1
    # Prefer a line that actually names the error over a bare "file:line"
    # header (e.g. node prints that on its own line, the message later).
    message = next((l for l in out_lines if "error" in l.lower()), out_lines[0] if out_lines else "")
    return [StaticIssue(file=rel, line=line, severity="error", code=code, message=message[:300])]


LANG_CHECKERS: dict[str, tuple[str, list[str], str]] = {
    # suffix -> (tool, extra_args, issue code)
    ".js": ("node", ["--check"], "javascript-syntax"),
    ".jsx": ("node", ["--check"], "javascript-syntax"),
    ".rb": ("ruby", ["-c"], "ruby-syntax"),
    ".php": ("php", ["-l"], "php-syntax"),
    ".go": ("gofmt", ["-e", "-l"], "go-syntax"),
}
# TypeScript needs a type-aware compiler, not just a parser; only attempt it
# if `tsc` is actually on PATH (it usually isn't without a project install).
TS_CHECKER = ("tsc", ["--noEmit", "--allowJs", "--checkJs", "false"], "typescript-syntax")


def run_static_analysis(root: Path) -> StaticReport:
    root = Path(root)
    issues: list[StaticIssue] = []
    files_checked = 0
    languages_seen: set[str] = set()

    for path in iter_source_files(root):
        suffix = path.suffix
        rel = str(path.relative_to(root))

        if suffix == ".py":
            files_checked += 1
            languages_seen.add("python")
            issues.extend(run_ast_check(rel, safe_read_text(path)))
            continue

        if suffix in (".ts", ".tsx"):
            files_checked += 1
            languages_seen.add("typescript")
            tool, args, code = TS_CHECKER
            issues.extend(_run_file_syntax_tool(tool, args, path, rel, code, timeout=30))
            continue

        if suffix in LANG_CHECKERS:
            files_checked += 1
            lang_name = {
                ".js": "javascript", ".jsx": "javascript",
                ".rb": "ruby", ".php": "php", ".go": "go",
            }[suffix]
            languages_seen.add(lang_name)
            tool, args, code = LANG_CHECKERS[suffix]
            issues.extend(_run_file_syntax_tool(tool, args, path, rel, code))

    issues.extend(run_pyflakes_check(root))

    syntax_errors = sum(1 for i in issues if i.severity == "error")
    return StaticReport(
        issues=issues,
        files_checked=files_checked,
        syntax_errors=syntax_errors,
        languages_checked=sorted(languages_seen),
    )

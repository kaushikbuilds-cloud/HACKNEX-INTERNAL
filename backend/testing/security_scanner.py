"""Alt 4: security scanning. Bandit covers Python with real AST-based
rules. For other languages, a small set of conservative regex patterns
catches the same handful of high-signal issues bandit looks for (eval,
shell injection, hardcoded secrets, string-built SQL). These are marked
confidence="LOW" (pattern-match, not AST-verified) so a report reader can
tell them apart from bandit's AST-backed findings — both run on source
text only, never executing target code, so this stays safe on any public repo.
Custom auth/JWT-specific rules are deliberately NOT included yet: they'd
be guesses about a repo's structure until verified against a real repo,
and a wrong guess there is a false security finding, which is worse than
no finding."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from backend.repository.parser import iter_source_files
from backend.utils.file_utils import safe_read_text


@dataclass
class SecurityIssue:
    file: str
    line: int
    severity: str  # "HIGH" | "MEDIUM" | "LOW"
    confidence: str
    test_id: str
    description: str

    def key(self) -> tuple:
        return (self.file, self.line, self.test_id)


@dataclass
class SecurityReport:
    issues: list[SecurityIssue] = field(default_factory=list)
    high_severity_count: int = 0
    medium_severity_count: int = 0
    ran: bool = True  # False if bandit isn't installed — never block on that

    @property
    def passed(self) -> bool:
        return self.high_severity_count == 0

    def summary(self) -> str:
        if not self.ran:
            return "security scan: skipped (bandit not installed)"
        if not self.issues:
            return "security scan: OK (no issues found)"
        lines = [
            f"security scan: {self.high_severity_count} high, "
            f"{self.medium_severity_count} medium severity issue(s)"
        ]
        for issue in self.issues[:20]:
            lines.append(f"  {issue.file}:{issue.line} [{issue.severity}] {issue.description}")
        if len(self.issues) > 20:
            lines.append(f"  ... and {len(self.issues) - 20} more")
        return "\n".join(lines)


def run_bandit(root: Path) -> SecurityReport:
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "bandit", "-r", ".", "-f", "json", "--quiet"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=180,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return SecurityReport(ran=False)

    if not proc.stdout.strip():
        return SecurityReport(ran=False)

    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return SecurityReport(ran=False)

    issues = []
    for result in data.get("results", []):
        issues.append(
            SecurityIssue(
                file=result.get("filename", "").lstrip("./"),
                line=result.get("line_number", 0),
                severity=result.get("issue_severity", "LOW"),
                confidence=result.get("issue_confidence", "LOW"),
                test_id=result.get("test_id", ""),
                description=result.get("issue_text", ""),
            )
        )

    high = sum(1 for i in issues if i.severity == "HIGH")
    medium = sum(1 for i in issues if i.severity == "MEDIUM")
    return SecurityReport(issues=issues, high_severity_count=high, medium_severity_count=medium)


# suffix -> language label, for the small set of applicable rules below
_GENERIC_LANGS = {
    ".js": "javascript", ".jsx": "javascript", ".ts": "typescript", ".tsx": "typescript",
    ".go": "go", ".rb": "ruby", ".php": "php", ".java": "java",
}

# Conservative, high-signal-only patterns. Each: (test_id, severity, regex, description)
_GENERIC_RULES: list[tuple[str, str, "re.Pattern", str]] = [
    (
        "GEN-EVAL",
        "HIGH",
        re.compile(r"\beval\s*\("),
        "Use of eval() on dynamic input — arbitrary code execution risk (CWE-95).",
    ),
    (
        "GEN-SHELL",
        "HIGH",
        re.compile(
            r"\b(shell_exec|system|passthru|exec)\s*\(\s*[\"'].*\$|"
            r"child_process\.(exec|execSync)\s*\(\s*`|"
            r"exec\.Command\s*\(\s*\"sh\"\s*,\s*\"-c\""
        ),
        "Shell command built from interpolated/dynamic input — command injection risk (CWE-78).",
    ),
    (
        "GEN-SECRET",
        "MEDIUM",
        re.compile(
            r"(?i)\b(password|secret|api[_-]?key|token)\b\s*[:=]\s*[\"'][^\"'\s]{4,}[\"']"
        ),
        "Hardcoded credential-looking literal — should come from config/secrets store (CWE-798).",
    ),
    (
        "GEN-SQLI",
        "MEDIUM",
        re.compile(
            r"(?i)(select|insert|update|delete)\b[^\"'\n]{0,80}[\"'][^\"'\n]*"
            r"(\+|\$\{|#\{)"
        ),
        "SQL query built via string concatenation/interpolation — SQL injection risk (CWE-89).",
    ),
]


def generic_security_scan(root: Path) -> list[SecurityIssue]:
    """Pattern-based scan for the common non-Python languages (JS/TS, Go,
    Ruby, PHP, Java). Intentionally small and conservative."""
    issues: list[SecurityIssue] = []
    for path in iter_source_files(root):
        if path.suffix not in _GENERIC_LANGS:
            continue
        rel = str(path.relative_to(root))
        content = safe_read_text(path)
        for lineno, line in enumerate(content.splitlines(), start=1):
            for test_id, severity, pattern, description in _GENERIC_RULES:
                if pattern.search(line):
                    issues.append(
                        SecurityIssue(
                            file=rel,
                            line=lineno,
                            severity=severity,
                            confidence="LOW",  # pattern-match, not AST-verified
                            test_id=test_id,
                            description=description,
                        )
                    )
    return issues


def run_security_scan(root: Path) -> SecurityReport:
    root = Path(root)
    bandit_report = run_bandit(root)
    generic_issues = generic_security_scan(root)

    all_issues = list(bandit_report.issues) + generic_issues
    high = sum(1 for i in all_issues if i.severity == "HIGH")
    medium = sum(1 for i in all_issues if i.severity == "MEDIUM")

    return SecurityReport(
        issues=all_issues,
        high_severity_count=high,
        medium_severity_count=medium,
        # The generic pattern scan has no external dependency, so the
        # combined scan always produces a real result even if bandit itself
        # was skipped (e.g. not installed, or a non-Python repo).
        ran=True,
    )

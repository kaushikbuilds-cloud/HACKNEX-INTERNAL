"""Alt 4: security scanning via Bandit's static AST rules. Runs on source
only — never executes target code — so it's safe on any public repo.
Custom auth/JWT-specific rules are deliberately NOT included yet: they'd
be guesses about a repo's structure until verified against a real repo,
and a wrong guess there is a false security finding, which is worse than
no finding."""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path


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


def run_security_scan(root: Path) -> SecurityReport:
    return run_bandit(Path(root))

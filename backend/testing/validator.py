"""Run install/build/test commands and capture results."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from typing import TYPE_CHECKING

from backend.repository.repository_profile import RepositoryProfile

if TYPE_CHECKING:
    from backend.testing.security_scanner import SecurityReport
    from backend.testing.static_analyzer import StaticReport


@dataclass
class CommandResult:
    command: str
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0


@dataclass
class TestReport:
    install: CommandResult | None
    build: CommandResult | None
    test: CommandResult | None
    static_report: "StaticReport | None" = None
    security_report: "SecurityReport | None" = None
    no_test_suite: bool = False

    @property
    def passed(self) -> bool:
        # A missing test command (no_test_suite) must NOT count as failure —
        # otherwise a repo with no test suite (like our actual target may
        # have) can never report a successful fix, regardless of quality.
        # Static syntax errors always fail: valid Python going in must stay
        # valid Python going out, independent of any baseline. Security
        # findings are intentionally NOT part of pass/fail here — they're
        # scored as a confidence penalty (new issues vs. baseline) instead,
        # since gating the self-healing retry loop on them risks the LLM
        # retrying forever against findings it can't reliably resolve.
        test_ok = self.test is None or self.test.ok
        static_ok = self.static_report is None or self.static_report.passed
        return test_ok and static_ok

    def summary(self) -> str:
        lines = []
        for label, result in (("install", self.install), ("build", self.build), ("test", self.test)):
            if result is None:
                continue
            status = "OK" if result.ok else "FAILED"
            lines.append(f"{label}: {status} (`{result.command}`)")
        if self.no_test_suite:
            lines.append("test: no test command detected for this repo")
        if self.static_report is not None:
            lines.append(self.static_report.summary())
        if self.security_report is not None:
            lines.append(self.security_report.summary())
        return "\n".join(lines)


def run_command(
    command: str, cwd: Path, timeout: int = 600, python_executable: str | None = None
) -> CommandResult:
    # Commands from scanner.py use a "{python}" placeholder so install/test
    # runs with the session's isolated sandbox venv interpreter when one
    # exists, instead of whatever "pip"/"python" happens to be first on the
    # host's PATH (see backend/sandbox/venv_manager.py). Commands with no
    # placeholder (e.g. "npm install") are unaffected.
    resolved = command.format(python=python_executable or sys.executable) if "{python}" in command else command
    proc = subprocess.run(
        resolved, shell=True, cwd=cwd, capture_output=True, text=True, timeout=timeout
    )
    return CommandResult(resolved, proc.returncode, proc.stdout, proc.stderr)


def run_validation(
    root: Path,
    profile: RepositoryProfile,
    skip_install: bool = False,
    run_static: bool = True,
    python_executable: str | None = None,
) -> TestReport:
    from backend.testing.build_runner import run_build
    from backend.testing.test_runner import run_tests

    install_result = None
    if profile.install_command and not skip_install:
        install_result = run_command(profile.install_command, root, python_executable=python_executable)

    build_result = run_build(root, profile, python_executable=python_executable)
    test_result = run_tests(root, profile, python_executable=python_executable)

    static_report = None
    security_report = None
    if run_static:
        from backend.testing.security_scanner import run_security_scan
        from backend.testing.static_analyzer import run_static_analysis

        static_report = run_static_analysis(root)
        security_report = run_security_scan(root)

    return TestReport(
        install=install_result,
        build=build_result,
        test=test_result,
        static_report=static_report,
        security_report=security_report,
        no_test_suite=profile.test_command is None,
    )


def failure_excerpt(report: TestReport, max_chars: int = 4000) -> str:
    """Pull the most useful bit of output for feeding back into the retry loop."""
    for result in (report.test, report.build, report.install):
        if result is not None and not result.ok:
            tail = (result.stderr or result.stdout)[-max_chars:]
            return f"Command failed: {result.command}\n{tail}"
    return ""

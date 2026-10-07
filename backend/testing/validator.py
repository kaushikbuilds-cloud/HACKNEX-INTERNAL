"""Run install/build/test commands and capture results."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from backend.repository.repository_profile import RepositoryProfile


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

    @property
    def passed(self) -> bool:
        return self.test is not None and self.test.ok

    def summary(self) -> str:
        lines = []
        for label, result in (("install", self.install), ("build", self.build), ("test", self.test)):
            if result is None:
                continue
            status = "OK" if result.ok else "FAILED"
            lines.append(f"{label}: {status} (`{result.command}`)")
        return "\n".join(lines)


def run_command(command: str, cwd: Path, timeout: int = 600) -> CommandResult:
    proc = subprocess.run(
        command, shell=True, cwd=cwd, capture_output=True, text=True, timeout=timeout
    )
    return CommandResult(command, proc.returncode, proc.stdout, proc.stderr)


def run_validation(
    root: Path, profile: RepositoryProfile, skip_install: bool = False
) -> TestReport:
    from backend.testing.build_runner import run_build
    from backend.testing.test_runner import run_tests

    install_result = None
    if profile.install_command and not skip_install:
        install_result = run_command(profile.install_command, root)

    build_result = run_build(root, profile)
    test_result = run_tests(root, profile)

    return TestReport(install=install_result, build=build_result, test=test_result)


def failure_excerpt(report: TestReport, max_chars: int = 4000) -> str:
    """Pull the most useful bit of output for feeding back into the retry loop."""
    for result in (report.test, report.build, report.install):
        if result is not None and not result.ok:
            tail = (result.stderr or result.stdout)[-max_chars:]
            return f"Command failed: {result.command}\n{tail}"
    return ""

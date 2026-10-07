from __future__ import annotations

from backend.testing.validator import TestReport


def render_test_report(baseline: TestReport, final: TestReport, attempts: int) -> str:
    return (
        f"BASELINE (before change)\n{baseline.summary()}\n\n"
        f"FINAL (after change, attempt {attempts})\n{final.summary()}\n"
    )

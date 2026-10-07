"""Compares a baseline TestReport (before the agent touched anything) to
the final one, so confidence scoring only penalizes issues the agent's
change actually introduced — never issues that were already there. This
is the same principle the test-pass/fail baseline check already uses,
applied to the static-analysis and security signals too."""

from __future__ import annotations

from dataclasses import dataclass

from backend.testing.validator import TestReport


@dataclass
class ValidationDiff:
    new_security_high: int = 0
    new_security_medium: int = 0
    new_static_issues: int = 0


def _security_keys(report) -> set:
    if report is None:
        return set()
    return {issue.key() for issue in report.issues}


def _static_keys(report) -> set:
    if report is None:
        return set()
    return {(issue.file, issue.line, issue.code) for issue in report.issues}


def diff_reports(baseline: TestReport, final: TestReport) -> ValidationDiff:
    baseline_sec_keys = _security_keys(baseline.security_report)
    final_sec_issues = final.security_report.issues if final.security_report else []
    new_sec_issues = [i for i in final_sec_issues if i.key() not in baseline_sec_keys]

    baseline_static_keys = _static_keys(baseline.static_report)
    final_static_issues = final.static_report.issues if final.static_report else []
    new_static_issues = [
        i for i in final_static_issues if (i.file, i.line, i.code) not in baseline_static_keys
    ]

    return ValidationDiff(
        new_security_high=sum(1 for i in new_sec_issues if i.severity == "HIGH"),
        new_security_medium=sum(1 for i in new_sec_issues if i.severity == "MEDIUM"),
        new_static_issues=len(new_static_issues),
    )

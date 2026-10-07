"""Turns the plan + validation outcome into the human-readable explanation
the diagrams call for: what the bug/change was, what was touched, and
whether it's safe."""

from __future__ import annotations


def build_explanation(
    understanding: str,
    root_cause: str,
    files_changed: list[str],
    steps: list[str],
    test_strategy: str,
    success: bool,
    attempts: int,
    baseline_passed: bool,
) -> str:
    lines = [f"Understanding: {understanding}"]
    if root_cause:
        lines.append(f"Root cause: {root_cause}")
    lines.append(f"Files changed: {', '.join(files_changed) or '(none)'}")
    lines.append(f"Steps taken: {'; '.join(steps)}")
    lines.append(f"Test strategy: {test_strategy}")
    lines.append(
        f"Validation: {'PASSED' if success else 'FAILED'} after {attempts} attempt(s)."
    )
    lines.append(
        "Baseline tests before change: "
        + ("passed" if baseline_passed else "FAILED (already broken before our change)")
    )
    return "\n".join(lines)

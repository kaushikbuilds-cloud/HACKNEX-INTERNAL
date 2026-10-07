"""Heuristic confidence score for a completed change: how much should the
user trust this result before merging it. Pure arithmetic over signals we
already have (no extra LLM call), 0.0-1.0."""

from __future__ import annotations


def score_confidence(
    tests_passed: bool,
    attempts: int,
    max_attempts: int,
    num_risks: int,
    num_files_changed: int,
    baseline_passed: bool,
    new_security_high: int = 0,
    new_security_medium: int = 0,
    new_static_issues: int = 0,
    no_test_suite: bool = False,
) -> float:
    """Calculates a deterministic 0.0-1.0 confidence score.

    Hard failure gates (checked before any other scoring):
    1. Tests failed -> 0.0
    2. No files were actually changed -> 0.0 (the task wasn't done)
    3. A new HIGH severity security issue was introduced -> 0.0
    """
    # A failing baseline is normal and expected for a bug-fix task (that's
    # the bug) — it must NOT zero out confidence on its own. What matters
    # for "did we break anything" is whether the suite passes now.
    if not tests_passed:
        return 0.0

    if num_files_changed == 0:
        return 0.0

    if new_security_high > 0:
        return 0.0

    score = 1.0

    # No test suite means this fix was never dynamically verified — real,
    # but unverified, so confidence is capped rather than full.
    if no_test_suite:
        score -= 0.30

    # more retry attempts needed -> less confidence the fix is clean
    score -= 0.15 * (attempts - 1)
    # more named risks -> less confidence
    score -= 0.05 * min(num_risks, 4)
    # touching many files for what should be a minimal change -> less confidence
    if num_files_changed > 3:
        score -= 0.1 * (num_files_changed - 3)

    # Security/static penalties count only NEW issues (vs. the pre-change
    # baseline) — a repo's pre-existing problems are never this change's
    # fault, so they must never cap its confidence score.
    score -= 0.1 * min(new_security_medium, 3)
    score -= 0.1 * min(new_static_issues, 3)

    # Reward actually fixing a documented bug (baseline was red, now green)
    # — but only when tests, not just "nothing to run," confirmed it.
    if not baseline_passed and tests_passed and not no_test_suite:
        score += 0.10

    return max(0.0, min(1.0, round(score, 2)))

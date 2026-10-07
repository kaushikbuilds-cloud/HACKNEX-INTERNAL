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
) -> float:
    # A failing baseline is normal and expected for a bug-fix task (that's
    # the bug) — it must NOT zero out confidence on its own. What matters
    # for "did we break anything" is whether the suite passes now; we only
    # have whole-suite pass/fail here, not a per-test before/after diff.
    if not tests_passed:
        return 0.0

    score = 1.0
    # more retry attempts needed -> less confidence the fix is clean
    score -= 0.15 * (attempts - 1)
    # more named risks -> less confidence
    score -= 0.05 * min(num_risks, 4)
    # touching many files for what should be a minimal change -> less confidence
    if num_files_changed > 3:
        score -= 0.1 * (num_files_changed - 3)

    return max(0.0, min(1.0, score))

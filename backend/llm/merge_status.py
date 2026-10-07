"""Turns the same signals score_confidence() already uses into an
advisory merge recommendation: a status, the reasons behind it, and
concrete next steps. Advisory only — it never blocks the push action
itself, since the user is always the final decision-maker on whether to
push a given confidence level."""

from __future__ import annotations

from dataclasses import dataclass, field

READY = "READY"
REVIEW_RECOMMENDED = "REVIEW_RECOMMENDED"
BLOCKED = "BLOCKED"

# Below this count of other modules depending on the changed files, we
# don't call it a "large" blast radius.
LARGE_BLAST_RADIUS_THRESHOLD = 2


@dataclass
class MergeStatus:
    status: str  # READY | REVIEW_RECOMMENDED | BLOCKED
    confidence: float
    reasons: list[str] = field(default_factory=list)
    suggested_actions: list[str] = field(default_factory=list)


def determine_merge_status(
    confidence: float,
    no_test_suite: bool,
    attempts: int,
    num_risks: int,
    num_files_changed: int,
    blast_radius_count: int = 0,
    new_security_high: int = 0,
    new_security_medium: int = 0,
    new_static_issues: int = 0,
) -> MergeStatus:
    if confidence >= 0.8:
        status = READY
    elif confidence >= 0.5:
        status = REVIEW_RECOMMENDED
    else:
        status = BLOCKED

    reasons: list[str] = []
    actions: list[str] = []

    # READY means nothing here actually needs a human's attention — don't
    # list minor contributing factors (e.g. one named risk) that read like
    # blockers when the overall result is fine. Only REVIEW/BLOCKED get a
    # reasons breakdown.
    if status == READY:
        return MergeStatus(
            status=status,
            confidence=confidence,
            reasons=["Clean validated change"],
            suggested_actions=[],
        )

    if no_test_suite:
        reasons.append("No test suite")
        actions.append("Add or run unit tests to verify this change dynamically")

    if blast_radius_count > LARGE_BLAST_RADIUS_THRESHOLD:
        reasons.append(f"Large blast radius ({blast_radius_count} dependent module(s))")
        actions.append("Review affected modules manually")

    if attempts > 1:
        reasons.append(f"Multiple self-healing retries needed ({attempts} attempts)")
        actions.append("Review the diff carefully — the model needed several attempts to converge")

    if num_files_changed > 3:
        reasons.append(f"Change touches many files ({num_files_changed})")
        actions.append("Reduce the scope of the patch, or split it into smaller changes")

    if new_security_high > 0:
        reasons.append("New HIGH severity security issue introduced")
        actions.append("Fix the flagged security issue before merging")

    if new_security_medium > 0:
        reasons.append(f"New medium severity security issue(s) introduced ({new_security_medium})")
        actions.append("Review the flagged security findings")

    if new_static_issues > 0:
        reasons.append(f"New static analysis issue(s) introduced ({new_static_issues})")
        actions.append("Review the static analysis findings")

    if num_risks > 0:
        reasons.append(f"Planner flagged {num_risks} risk(s)")
        actions.append("Review the planner-identified risks manually")

    if not reasons:
        reasons.append("Clean validated change")

    return MergeStatus(
        status=status,
        confidence=confidence,
        reasons=reasons,
        suggested_actions=actions,
    )


def format_merge_status(ms: MergeStatus) -> str:
    lines = [
        f"Confidence: {ms.confidence}",
        "",
        "Merge Status:",
        ms.status,
        "",
        "Reason:",
    ]
    lines += [f"- {r}" for r in ms.reasons]
    if ms.suggested_actions:
        lines += ["", "Suggested Actions:"]
        lines += [f"- {a}" for a in ms.suggested_actions]
    return "\n".join(lines)

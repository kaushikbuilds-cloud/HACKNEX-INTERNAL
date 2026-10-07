"""Diagram's Self-Healing Retry Loop: if tests fail, read the error, feed it
back to the code-generation agent along with the plan, and retry up to a
fixed number of attempts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..codegen.generator import FileEdit, generate_file_edit
from ..codegen.patch import apply_edits
from ..llm.client import LLMClient
from ..planning.planner import Plan
from ..repo_intel.profile import RepoProfile
from .runner import TestReport, failure_excerpt, run_validation

MAX_ATTEMPTS = 3


@dataclass
class HealResult:
    report: TestReport
    edits: list[FileEdit]
    attempts: int
    healed: bool


def generate_and_validate(
    llm: LLMClient,
    root: Path,
    profile: RepoProfile,
    plan: Plan,
    request: str,
    related_context: str,
    branch: str,
) -> HealResult:
    attempt = 0
    last_report: TestReport | None = None
    edits: list[FileEdit] = []
    extra_note = ""

    while attempt < MAX_ATTEMPTS:
        attempt += 1
        edits = []
        for rel_path in plan.files_to_change:
            full_path = Path(root) / rel_path
            original = full_path.read_text() if full_path.exists() else ""
            plan_summary = "\n".join(plan.steps) + extra_note
            edit = generate_file_edit(
                llm,
                rel_path,
                original,
                plan_summary,
                request,
                related_context,
            )
            edits.append(edit)

        apply_edits(root, edits, branch)
        last_report = run_validation(root, profile, skip_install=attempt > 1)

        if last_report.passed:
            return HealResult(last_report, edits, attempt, healed=attempt > 1)

        excerpt = failure_excerpt(last_report)
        extra_note = f"\n\nThe previous attempt failed validation with this error — fix it:\n{excerpt}"

    return HealResult(last_report, edits, attempt, healed=False)

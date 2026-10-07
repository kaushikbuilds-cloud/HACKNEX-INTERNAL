"""Ties the whole pipeline together: Repository Analysis -> Code
Understanding -> Find Relevant Files -> Planning -> Generate Code Changes
-> Apply Patch -> Run Tests (with self-healing retry) -> Final Output."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import git

from backend.core.config import settings
from backend.embeddings.vector_search import build_context, build_index
from backend.llm.client import LLMClient, get_default_client
from backend.llm.confidence_score import score_confidence
from backend.llm.explanation import build_explanation
from backend.patch.rollback import rollback_to
from backend.planner.change_planner import Plan, make_plan
from backend.planner.file_selector import select_candidate_files
from backend.repository.clone_repo import resolve_target
from backend.repository.dependency_graph import build_blast_radius_summary
from backend.repository.scanner import scan_repo
from backend.testing.baseline_diff import diff_reports
from backend.testing.retry_agent import HealResult, generate_and_validate
from backend.testing.validator import TestReport, run_validation


@dataclass
class RunResult:
    root: Path
    branch: str
    plan: Plan
    baseline: TestReport
    heal: HealResult
    diff: str
    confidence: float
    rolled_back: bool = False

    @property
    def success(self) -> bool:
        return self.heal.report.passed

    def explanation(self) -> str:
        text = build_explanation(
            understanding=self.plan.understanding,
            root_cause=self.plan.root_cause,
            files_changed=self.plan.files_to_change,
            steps=self.plan.steps,
            test_strategy=self.plan.test_strategy,
            success=self.success,
            attempts=self.heal.attempts,
            baseline_passed=self.baseline.passed,
        )
        if self.rolled_back:
            text += "\nThe change did not pass validation after all retries, so it was rolled back — the repo is back to its original state."
        return text


def run_pipeline(
    source: str,
    request: str,
    workdir: Path,
    branch: str = "swe-agent/auto-fix",
    llm: LLMClient | None = None,
) -> RunResult:
    llm = llm or get_default_client()

    # Repository analysis
    root = resolve_target(source, workdir)
    profile = scan_repo(root)

    # Remember what branch/ref we started on, so a failed fix can be
    # rolled back cleanly instead of leaving a broken work branch behind.
    try:
        base_ref = git.Repo(root).active_branch.name
    except (git.InvalidGitRepositoryError, TypeError):
        base_ref = None  # not a git repo, or detached HEAD — can't roll back

    # Confirm the baseline: tests must already be green (or we note they
    # weren't) before we touch anything, so "did you break anything" is
    # judged fairly.
    baseline = run_validation(root, profile)

    # Code understanding: parse, chunk, embed, index
    store = build_index(root)

    # Retrieve relevant files
    candidate_files = select_candidate_files(store, request)
    context = build_context(store, request)
    dependency_info = build_blast_radius_summary(root, candidate_files)

    # Planning agent
    plan = make_plan(llm, request, context, profile.to_dict(), dependency_info)

    # Generate code changes, apply patch, run tests, self-heal on failure
    heal = generate_and_validate(
        llm, root, profile, plan, request, context, branch,
        max_attempts=settings.max_retry_attempts, store=store,
    )

    from backend.patch.diff_generator import full_diff

    diff = full_diff(heal.edits)
    vdiff = diff_reports(baseline, heal.report)
    confidence = score_confidence(
        tests_passed=heal.report.passed,
        attempts=heal.attempts,
        max_attempts=settings.max_retry_attempts,
        num_risks=len(plan.risks),
        num_files_changed=len([e for e in heal.edits if e.changed]),
        baseline_passed=baseline.passed,
        new_security_high=vdiff.new_security_high,
        new_security_medium=vdiff.new_security_medium,
        new_static_issues=vdiff.new_static_issues,
        no_test_suite=heal.report.no_test_suite,
    )

    # Self-healing exhausted every retry and never converged — don't leave
    # a broken branch sitting in the repo.
    rolled_back = False
    if not heal.report.passed and base_ref is not None:
        rollback_to(root, base_ref, work_branch=branch)
        rolled_back = True

    return RunResult(
        root=root, branch=branch, plan=plan, baseline=baseline,
        heal=heal, diff=diff, confidence=confidence, rolled_back=rolled_back,
    )

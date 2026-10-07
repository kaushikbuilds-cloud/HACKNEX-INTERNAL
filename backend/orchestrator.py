"""Ties the whole pipeline together: Repository Analysis -> Code
Understanding -> Find Relevant Files -> Planning -> Generate Code Changes
-> Apply Patch -> Run Tests (with self-healing retry) -> Final Output."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from backend.core.config import settings
from backend.embeddings.vector_search import build_context, build_index
from backend.llm.client import LLMClient, get_default_client
from backend.llm.confidence_score import score_confidence
from backend.llm.explanation import build_explanation
from backend.planner.change_planner import Plan, make_plan
from backend.planner.file_selector import select_candidate_files
from backend.repository.clone_repo import resolve_target
from backend.repository.scanner import scan_repo
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

    @property
    def success(self) -> bool:
        return self.heal.report.passed

    def explanation(self) -> str:
        return build_explanation(
            understanding=self.plan.understanding,
            root_cause=self.plan.root_cause,
            files_changed=self.plan.files_to_change,
            steps=self.plan.steps,
            test_strategy=self.plan.test_strategy,
            success=self.success,
            attempts=self.heal.attempts,
            baseline_passed=self.baseline.passed,
        )


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

    # Confirm the baseline: tests must already be green (or we note they
    # weren't) before we touch anything, so "did you break anything" is
    # judged fairly.
    baseline = run_validation(root, profile)

    # Code understanding: parse, chunk, embed, index
    store = build_index(root)

    # Retrieve relevant files
    _ = select_candidate_files(store, request)
    context = build_context(store, request)

    # Planning agent
    plan = make_plan(llm, request, context, profile.to_dict())

    # Generate code changes, apply patch, run tests, self-heal on failure
    heal = generate_and_validate(
        llm, root, profile, plan, request, context, branch,
        max_attempts=settings.max_retry_attempts,
    )

    from backend.patch.diff_generator import full_diff

    diff = full_diff(heal.edits)
    confidence = score_confidence(
        tests_passed=heal.report.passed,
        attempts=heal.attempts,
        max_attempts=settings.max_retry_attempts,
        num_risks=len(plan.risks),
        num_files_changed=len([e for e in heal.edits if e.changed]),
        baseline_passed=baseline.passed,
    )

    return RunResult(
        root=root, branch=branch, plan=plan, baseline=baseline,
        heal=heal, diff=diff, confidence=confidence,
    )

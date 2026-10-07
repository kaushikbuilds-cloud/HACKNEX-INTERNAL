"""Ties the whole pipeline together, matching the 8-step diagram:
User Request -> Repository Analysis -> Code Understanding -> Find Relevant
Files -> LLM Planning -> Generate Code Changes -> Apply Patch -> Run Tests
(with self-healing retry) -> Final Output."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .codegen.patch import full_diff
from .llm.client import LLMClient, get_default_client
from .planning.planner import Plan, make_plan
from .repo_intel.clone import resolve_target
from .repo_intel.scanner import scan_repo
from .understanding.retrieval import build_context, relevant_files
from .understanding.vectorstore import build_index
from .validation.retry import HealResult, generate_and_validate
from .validation.runner import TestReport, run_validation


@dataclass
class RunResult:
    root: Path
    branch: str
    plan: Plan
    baseline: TestReport
    heal: HealResult
    diff: str

    @property
    def success(self) -> bool:
        return self.heal.report.passed

    def explanation(self) -> str:
        files = ", ".join(self.plan.files_to_change) or "(none)"
        lines = [
            f"Understanding: {self.plan.understanding}",
        ]
        if self.plan.root_cause:
            lines.append(f"Root cause: {self.plan.root_cause}")
        lines.append(f"Files changed: {files}")
        lines.append(f"Steps taken: {'; '.join(self.plan.steps)}")
        lines.append(f"Test strategy: {self.plan.test_strategy}")
        lines.append(
            f"Validation: {'PASSED' if self.success else 'FAILED'} "
            f"after {self.heal.attempts} attempt(s)."
        )
        if self.baseline.test is not None:
            lines.append(
                f"Baseline tests before change: "
                f"{'passed' if self.baseline.passed else 'FAILED (already broken before our change)'}"
            )
        return "\n".join(lines)


def run_pipeline(
    source: str,
    request: str,
    workdir: Path,
    branch: str = "swe-agent/auto-fix",
    llm: LLMClient | None = None,
) -> RunResult:
    llm = llm or get_default_client()

    # 1-2. Repository analysis
    root = resolve_target(source, workdir)
    profile = scan_repo(root)

    # Confirm the baseline: tests must already be green (or we note they weren't)
    # before we touch anything, so "did you break anything" is judged fairly.
    baseline = run_validation(root, profile)

    # 3. Code understanding: parse, chunk, embed, index
    store = build_index(root)

    # 4. Retrieve relevant files
    _ = relevant_files(store, request)
    context = build_context(store, request)

    # 5. Planning agent
    plan = make_plan(llm, request, context, profile.to_dict())

    # 6-9. Generate code changes, apply patch, run tests, self-heal on failure
    heal = generate_and_validate(llm, root, profile, plan, request, context, branch)

    diff = full_diff(heal.edits)

    return RunResult(root=root, branch=branch, plan=plan, baseline=baseline, heal=heal, diff=diff)

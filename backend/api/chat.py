"""Chat Panel endpoint: take a natural-language request against an already
loaded session, and run planning -> codegen -> apply -> validate."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.core.config import settings
from backend.core.sessions import get_session
from backend.embeddings.vector_search import build_context
from backend.llm.client import get_default_client
from backend.llm.confidence_score import score_confidence
from backend.llm.explanation import build_explanation
from backend.llm.merge_status import determine_merge_status
from backend.patch.diff_generator import full_diff
from backend.patch.git_manager import commit_all
from backend.patch.rollback import rollback_to
from backend.planner.bug_finder import BUG_HUNT_QUERY, find_bugs
from backend.planner.change_planner import make_plan
from backend.planner.file_selector import select_candidate_files
from backend.reports.bug_report import render_bug_report
from backend.repository.dependency_graph import build_blast_radius
from backend.testing.baseline_diff import ValidationDiff, diff_reports
from backend.testing.retry_agent import generate_and_validate
from backend.testing.security_scanner import run_security_scan
from backend.testing.static_analyzer import run_static_analysis

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    session_id: str
    message: str
    branch: str = "swe-agent/auto-fix"


class AnalyzeRequest(BaseModel):
    session_id: str
    message: str = ""  # optional extra guidance (e.g. "focus on auth code")


@router.post("")
def chat(req: ChatRequest):
    session = get_session(req.session_id)
    if session is None or session.root is None:
        raise HTTPException(404, "session not found; load a repository first")

    llm = get_default_client()
    candidate_files = select_candidate_files(session.store, req.message)
    context = build_context(session.store, req.message)
    dependency_info, blast_radius_count = build_blast_radius(session.root, candidate_files)
    plan = make_plan(llm, req.message, context, session.profile.to_dict(), dependency_info)

    heal = generate_and_validate(
        llm, session.root, session.profile, plan, req.message, context, req.branch,
        max_attempts=settings.max_retry_attempts, store=session.store,
    )

    session.plan = plan
    session.heal = heal
    session.diff = full_diff(heal.edits)

    # Commit locally once the fix actually passes validation — never on a
    # failed/intermediate attempt, and never pushed anywhere yet. Pushing
    # to the remote is a separate, explicitly user-confirmed step.
    rolled_back = False
    if heal.report.passed:
        commit_message = f"swe-agent: {plan.understanding}".strip() or "swe-agent: automated change"
        commit_all(session.root, commit_message[:200])
    elif session.base_ref is not None:
        # Exhausted every retry and never converged — don't leave a broken
        # work branch sitting in the repo.
        rollback_to(session.root, session.base_ref, work_branch=req.branch)
        rolled_back = True

    vdiff = diff_reports(session.baseline, heal.report) if session.baseline else ValidationDiff()
    confidence = score_confidence(
        tests_passed=heal.report.passed,
        attempts=heal.attempts,
        max_attempts=settings.max_retry_attempts,
        num_risks=len(plan.risks),
        num_files_changed=len([e for e in heal.edits if e.changed]),
        baseline_passed=session.baseline.passed if session.baseline else False,
        new_security_high=vdiff.new_security_high,
        new_security_medium=vdiff.new_security_medium,
        new_static_issues=vdiff.new_static_issues,
        no_test_suite=heal.report.no_test_suite,
    )

    merge_status = determine_merge_status(
        confidence=confidence,
        no_test_suite=heal.report.no_test_suite,
        attempts=heal.attempts,
        num_risks=len(plan.risks),
        num_files_changed=len([e for e in heal.edits if e.changed]),
        blast_radius_count=blast_radius_count,
        new_security_high=vdiff.new_security_high,
        new_security_medium=vdiff.new_security_medium,
        new_static_issues=vdiff.new_static_issues,
    )

    explanation = build_explanation(
        understanding=plan.understanding,
        root_cause=plan.root_cause,
        files_changed=plan.files_to_change,
        steps=plan.steps,
        test_strategy=plan.test_strategy,
        success=heal.report.passed,
        attempts=heal.attempts,
        baseline_passed=session.baseline.passed if session.baseline else False,
    )
    if rolled_back:
        explanation += "\nThe change did not pass validation after all retries, so it was rolled back — the repo is back to its original state."

    return {
        "success": heal.report.passed,
        "rolled_back": rolled_back,
        "plan": plan.raw,
        "explanation": explanation,
        "confidence": confidence,
        "attempts": heal.attempts,
        "merge_status": {
            "status": merge_status.status,
            "reasons": merge_status.reasons,
            "suggested_actions": merge_status.suggested_actions,
        },
        "validation": {
            "no_test_suite": heal.report.no_test_suite,
            "new_security_high": vdiff.new_security_high,
            "new_security_medium": vdiff.new_security_medium,
            "new_static_issues": vdiff.new_static_issues,
            "summary": heal.report.summary(),
        },
    }


@router.post("/analyze")
def analyze(req: AnalyzeRequest):
    """Read-only bug-finding. Deliberately calls nothing from patch/,
    git_manager, or retry_agent — this endpoint cannot modify the repo,
    commit, or push, no matter what the request text says."""
    session = get_session(req.session_id)
    if session is None or session.root is None:
        raise HTTPException(404, "session not found; load a repository first")

    llm = get_default_client()
    query = req.message.strip() or BUG_HUNT_QUERY
    context = build_context(session.store, query)

    static_report = run_static_analysis(session.root)
    security_report = run_security_scan(session.root)

    findings = find_bugs(
        llm,
        context,
        session.profile.to_dict(),
        static_report.summary(),
        security_report.summary(),
    )

    return {
        "findings": [
            {"file": f.file, "line": f.line, "severity": f.severity, "description": f.description}
            for f in findings
        ],
        "report": render_bug_report(findings),
        "static_summary": static_report.summary(),
        "security_summary": security_report.summary(),
    }

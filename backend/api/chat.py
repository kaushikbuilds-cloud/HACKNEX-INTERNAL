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
from backend.patch.diff_generator import full_diff
from backend.planner.change_planner import make_plan
from backend.testing.retry_agent import generate_and_validate

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    session_id: str
    message: str
    branch: str = "swe-agent/auto-fix"


@router.post("")
def chat(req: ChatRequest):
    session = get_session(req.session_id)
    if session is None or session.root is None:
        raise HTTPException(404, "session not found; load a repository first")

    llm = get_default_client()
    context = build_context(session.store, req.message)
    plan = make_plan(llm, req.message, context, session.profile.to_dict())

    heal = generate_and_validate(
        llm, session.root, session.profile, plan, req.message, context, req.branch,
        max_attempts=settings.max_retry_attempts, store=session.store,
    )

    session.plan = plan
    session.heal = heal
    session.diff = full_diff(heal.edits)

    confidence = score_confidence(
        tests_passed=heal.report.passed,
        attempts=heal.attempts,
        max_attempts=settings.max_retry_attempts,
        num_risks=len(plan.risks),
        num_files_changed=len([e for e in heal.edits if e.changed]),
        baseline_passed=session.baseline.passed if session.baseline else False,
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

    return {
        "success": heal.report.passed,
        "plan": plan.raw,
        "explanation": explanation,
        "confidence": confidence,
        "attempts": heal.attempts,
    }

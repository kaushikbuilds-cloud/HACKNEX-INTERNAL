"""Test results / impact / repository-summary reports for a session."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.core.sessions import get_session
from backend.reports.impact_report import render_impact_report
from backend.reports.repository_summary import render_repository_summary
from backend.reports.test_report import render_test_report
from backend.repository.dependency_graph import build_dependency_graph
from backend.planner.impact_analysis import assess_impact

router = APIRouter(prefix="/report", tags=["report"])


@router.get("/{session_id}/tests")
def get_test_report(session_id: str):
    session = get_session(session_id)
    if session is None or session.heal is None or session.baseline is None:
        raise HTTPException(404, "no validated change for this session yet")
    return {"report": render_test_report(session.baseline, session.heal.report, session.heal.attempts)}


@router.get("/{session_id}/impact")
def get_impact_report(session_id: str):
    session = get_session(session_id)
    if session is None or session.plan is None:
        raise HTTPException(404, "no plan for this session yet")
    graph = build_dependency_graph(session.root)
    impact = assess_impact(session.plan, graph)
    return render_impact_report(session.plan, impact)


@router.get("/{session_id}/repository")
def get_repository_report(session_id: str):
    session = get_session(session_id)
    if session is None or session.profile is None:
        raise HTTPException(404, "session not found")
    return render_repository_summary(session.profile)

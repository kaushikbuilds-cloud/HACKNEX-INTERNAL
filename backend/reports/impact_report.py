from __future__ import annotations

from backend.planner.change_planner import Plan


def render_impact_report(plan: Plan, impact: dict) -> dict:
    return {
        "risks": plan.risks,
        "files_directly_changed": impact["files_directly_changed"],
        "modules_that_import_changed_files": impact["modules_that_import_changed_files"],
    }

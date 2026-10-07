"""View over a Plan: what the task actually is, in plain English."""

from __future__ import annotations

from backend.planner.change_planner import Plan


def describe_task(plan: Plan) -> str:
    if plan.root_cause:
        return f"{plan.understanding} Root cause: {plan.root_cause}"
    return plan.understanding

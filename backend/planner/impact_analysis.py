"""View over a Plan plus the dependency graph: what else could this change
affect, beyond the files it directly touches."""

from __future__ import annotations

from backend.planner.change_planner import Plan
from backend.repository.dependency_graph import dependents_of


def assess_impact(plan: Plan, dependency_graph: dict[str, list[str]]) -> dict:
    affected_modules: set[str] = set()
    for rel_path in plan.files_to_change:
        module = rel_path[:-3].replace("/", ".") if rel_path.endswith(".py") else rel_path
        affected_modules.update(dependents_of(dependency_graph, module))

    return {
        "stated_risks": plan.risks,
        "files_directly_changed": plan.files_to_change,
        "modules_that_import_changed_files": sorted(affected_modules),
    }

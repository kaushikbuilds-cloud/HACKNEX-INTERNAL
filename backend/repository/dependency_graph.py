"""Lightweight import-based dependency graph for Python files: which modules
import which, so the planner can see what else might be affected by a
change (a cheap stand-in for a full call graph)."""

from __future__ import annotations

import ast
from pathlib import Path

from backend.repository.parser import iter_source_files
from backend.utils.file_utils import safe_read_text


def _module_name(rel_path: str) -> str:
    return rel_path[:-3].replace("/", ".").removesuffix(".__init__")


def build_dependency_graph(root: Path) -> dict[str, list[str]]:
    """Returns {module: [imported_module, ...]} for every .py file, limited
    to imports that resolve to another module inside this repo."""
    root = Path(root)
    modules = {
        _module_name(str(p.relative_to(root))): p
        for p in iter_source_files(root)
        if p.suffix == ".py"
    }
    known = set(modules)

    graph: dict[str, list[str]] = {}
    for mod_name, path in modules.items():
        source = safe_read_text(path)
        try:
            tree = ast.parse(source)
        except SyntaxError:
            graph[mod_name] = []
            continue

        imports: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in known:
                        imports.add(alias.name)
            elif isinstance(node, ast.ImportFrom) and node.module:
                if node.module in known:
                    imports.add(node.module)
        graph[mod_name] = sorted(imports)

    return graph


def dependents_of(graph: dict[str, list[str]], module: str) -> list[str]:
    """Reverse lookup: which modules import `module` (what might break)."""
    return sorted(m for m, deps in graph.items() if module in deps)


def build_blast_radius_summary(root: Path, candidate_files: list[str]) -> str:
    """For each candidate file (a relative path), list which other modules
    import it — so the planner can see the blast radius of touching it
    BEFORE deciding to change it, not just after in an impact report."""
    graph = build_dependency_graph(root)
    lines = []
    for rel_path in candidate_files:
        if not rel_path.endswith(".py"):
            continue
        module = _module_name(rel_path)
        dependents = dependents_of(graph, module)
        if dependents:
            lines.append(f"- {rel_path}: imported by {', '.join(dependents)}")
        else:
            lines.append(f"- {rel_path}: no other module in this repo imports it")
    return "\n".join(lines)

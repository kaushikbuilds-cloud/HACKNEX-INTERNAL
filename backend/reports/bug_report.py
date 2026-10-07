from __future__ import annotations

from backend.planner.bug_finder import Finding

_SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def render_bug_report(findings: list[Finding]) -> str:
    if not findings:
        return "No bugs found in the reviewed code."

    ordered = sorted(findings, key=lambda f: _SEVERITY_ORDER.get(f.severity, 3))
    lines = [f"{len(findings)} finding(s):"]
    for f in ordered:
        location = f"{f.file}:{f.line}" if f.line else f.file
        lines.append(f"- [{f.severity.upper()}] {location} — {f.description}")
    return "\n".join(lines)

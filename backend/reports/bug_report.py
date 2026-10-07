from __future__ import annotations

from backend.planner.bug_finder import BugReport, Finding

_SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def render_bug_report(report: BugReport) -> str:
    findings: list[Finding] = report.findings
    if not findings:
        return "No bugs found in the reviewed code."

    ordered = sorted(findings, key=lambda f: _SEVERITY_ORDER.get(f.severity, 3))
    lines = [f"{len(findings)} finding(s):"]
    for f in ordered:
        location = f"{f.file}:{f.line}" if f.line else f.file
        lines.append(f"- [{f.severity.upper()}] ({f.source}) {location} — {f.description}")
    if not report.llm_available:
        lines.append(
            "\n(LLM was unreachable — these are deterministic static/security findings only; "
            "start Ollama and re-run to also get LLM-reviewed logic bugs.)"
        )
    return "\n".join(lines)

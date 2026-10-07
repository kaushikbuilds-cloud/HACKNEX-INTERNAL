"""Read-only bug-finding: reviews the repo and returns a findings list.
Architecturally separate from the Fix pipeline — this module never touches
patch/, git_manager, or retry_agent, so "find bugs" cannot accidentally
turn into an edit.

Tiered so a user is never left with an empty/misleading report:
  Tier 1 (deterministic): static analysis + security scan findings
    (including the framework-aware AST rules in security_scanner.py) are
    always available, with zero network dependency and zero hallucination
    risk — these are returned even if the LLM is completely unreachable.
  Tier 2 (LLM): when the LLM responds, it reviews the retrieved code with
    the Tier 1 findings already in its prompt, so it can explain
    business-logic impact and surface additional logic bugs the
    deterministic rules can't see (e.g. "why does this matter"), rather
    than re-discovering what Tier 1 already found.
If the LLM call fails or times out, Tier 2 is simply skipped — the
deterministic findings are still returned, not an error page."""

from __future__ import annotations

from dataclasses import dataclass, field

from backend.llm.client import LLMClient, Message
from backend.llm.prompt_builder import ANALYZE_SYSTEM_PROMPT, build_analyze_prompt
from backend.testing.security_scanner import SecurityReport
from backend.testing.static_analyzer import StaticReport
from backend.utils.helpers import extract_json

BUG_HUNT_QUERY = (
    "error handling exception edge case null check boundary condition "
    "off by one validation security auth password token"
)

_STATIC_TO_FINDING_SEVERITY = {"error": "high", "warning": "medium"}
_SECURITY_TO_FINDING_SEVERITY = {"HIGH": "high", "MEDIUM": "medium", "LOW": "low"}


@dataclass
class Finding:
    file: str
    line: int
    severity: str  # "high" | "medium" | "low"
    description: str
    source: str = "llm"  # "static" | "security" | "llm" — where this finding came from


@dataclass
class BugReport:
    findings: list[Finding] = field(default_factory=list)
    static_summary: str = ""
    security_summary: str = ""
    llm_available: bool = True


def deterministic_findings(static_report: StaticReport, security_report: SecurityReport) -> list[Finding]:
    """Tier 1: convert static analysis + security scan issues into findings.
    No LLM call, no network — always succeeds, so the report is never empty
    just because a local model wasn't running."""
    findings: list[Finding] = []
    for issue in static_report.issues:
        if issue.code == "pyflakes" and issue.severity != "error":
            continue  # pyflakes style/unused-import noise isn't a "bug" to report here
        findings.append(
            Finding(
                file=issue.file,
                line=issue.line,
                severity=_STATIC_TO_FINDING_SEVERITY.get(issue.severity, "low"),
                description=issue.message,
                source="static",
            )
        )
    for issue in security_report.issues:
        findings.append(
            Finding(
                file=issue.file,
                line=issue.line,
                severity=_SECURITY_TO_FINDING_SEVERITY.get(issue.severity, "low"),
                description=issue.description,
                source="security",
            )
        )
    return findings


def _llm_findings(
    llm: LLMClient,
    context: str,
    repo_profile: dict,
    static_summary: str,
    security_summary: str,
) -> list[Finding] | None:
    """Tier 2: ask the LLM for additional logic-level findings. Returns None
    (not an empty list) on any failure/timeout, so the caller can tell
    "LLM found nothing" apart from "LLM was unreachable"."""
    user_prompt = build_analyze_prompt(context, repo_profile, static_summary, security_summary)
    messages = [
        Message("system", ANALYZE_SYSTEM_PROMPT),
        Message("user", user_prompt),
    ]
    try:
        reply = llm.chat(messages, temperature=0.1)
    except Exception:
        # Ollama not running, connection refused, timeout, etc. — the
        # deterministic findings already computed stand on their own.
        return None

    try:
        data = extract_json(reply)
    except Exception:
        return None

    findings = []
    for item in data.get("findings", []):
        findings.append(
            Finding(
                file=item.get("file", ""),
                line=int(item.get("line", 0) or 0),
                severity=item.get("severity", "low"),
                description=item.get("description", ""),
                source="llm",
            )
        )
    return findings


def find_bugs(
    llm: LLMClient,
    context: str,
    repo_profile: dict,
    static_report: StaticReport,
    security_report: SecurityReport,
) -> BugReport:
    tier1 = deterministic_findings(static_report, security_report)

    tier2 = _llm_findings(
        llm, context, repo_profile, static_report.summary(), security_report.summary()
    )
    llm_available = tier2 is not None

    all_findings = tier1 + (tier2 or [])
    return BugReport(
        findings=all_findings,
        static_summary=static_report.summary(),
        security_summary=security_report.summary(),
        llm_available=llm_available,
    )

"""Read-only bug-finding: reviews the repo and returns a findings list.
Architecturally separate from the Fix pipeline — this module never touches
patch/, git_manager, or retry_agent, so "find bugs" cannot accidentally
turn into an edit."""

from __future__ import annotations

from dataclasses import dataclass, field

from backend.llm.client import LLMClient, Message
from backend.llm.prompt_builder import ANALYZE_SYSTEM_PROMPT, build_analyze_prompt
from backend.utils.helpers import extract_json

# A generic retrieval query biased toward the kinds of code most likely to
# hide real bugs, since the user's request itself ("find bugs") carries no
# useful signal for semantic search.
BUG_HUNT_QUERY = (
    "error handling exception edge case null check boundary condition "
    "off by one validation security auth password token"
)


@dataclass
class Finding:
    file: str
    line: int
    severity: str  # "high" | "medium" | "low"
    description: str


@dataclass
class BugReport:
    findings: list[Finding] = field(default_factory=list)
    static_summary: str = ""
    security_summary: str = ""


def find_bugs(
    llm: LLMClient,
    context: str,
    repo_profile: dict,
    static_summary: str,
    security_summary: str,
) -> list[Finding]:
    user_prompt = build_analyze_prompt(context, repo_profile, static_summary, security_summary)
    messages = [
        Message("system", ANALYZE_SYSTEM_PROMPT),
        Message("user", user_prompt),
    ]
    reply = llm.chat(messages, temperature=0.1)
    data = extract_json(reply)

    findings = []
    for item in data.get("findings", []):
        findings.append(
            Finding(
                file=item.get("file", ""),
                line=int(item.get("line", 0) or 0),
                severity=item.get("severity", "low"),
                description=item.get("description", ""),
            )
        )
    return findings

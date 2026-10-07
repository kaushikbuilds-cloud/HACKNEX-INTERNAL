"""Diagram step 5: Planning Agent — understand the task, pick the minimal
set of files to change, and produce a step-by-step plan + risk/test strategy."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..llm.client import LLMClient, Message, extract_json

PLAN_SYSTEM_PROMPT = """You are a senior software engineer planning a minimal, safe code change.

Rules:
- Only use real code, real APIs, and real imports that exist in the provided context. Never invent one.
- Prefer the smallest change that fixes the request.
- Never remove or rewrite code unrelated to the request.
- Identify exactly which existing tests are relevant, and whether new tests are needed.
- Respond with ONLY a JSON object, no prose, matching this schema:
{
  "understanding": "<1-3 sentences: what the bug/feature is and why>",
  "root_cause": "<if a bug, the concrete root cause; else empty string>",
  "files_to_change": ["path/one.py", "path/two.py"],
  "steps": ["step 1", "step 2", ...],
  "risks": ["risk 1", ...],
  "test_strategy": "<which existing tests must still pass, and what new test(s) to add>"
}
"""


@dataclass
class Plan:
    understanding: str
    root_cause: str
    files_to_change: list[str]
    steps: list[str]
    risks: list[str]
    test_strategy: str
    raw: dict = field(default_factory=dict)


def make_plan(
    llm: LLMClient,
    request: str,
    context: str,
    repo_profile: dict,
) -> Plan:
    user_prompt = f"""Repository profile:
{repo_profile}

Relevant code (retrieved by semantic search):
{context}

Task requested by the user:
{request}

Produce the JSON plan now."""

    messages = [
        Message("system", PLAN_SYSTEM_PROMPT),
        Message("user", user_prompt),
    ]
    reply = llm.chat(messages, temperature=0.1)
    data = extract_json(reply)

    return Plan(
        understanding=data.get("understanding", ""),
        root_cause=data.get("root_cause", ""),
        files_to_change=data.get("files_to_change", []),
        steps=data.get("steps", []),
        risks=data.get("risks", []),
        test_strategy=data.get("test_strategy", ""),
        raw=data,
    )

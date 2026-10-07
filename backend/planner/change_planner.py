"""Planning Agent: one LLM call that understands the task, selects the
minimal files to change, and produces a step-by-step plan with risks and a
test strategy. task_understanding.py, impact_analysis.py and
file_selector.py expose typed, single-purpose views over this same Plan so
each planning concern (understand / select files / assess risk) has its own
home, without paying for four separate LLM round-trips on a local model."""

from __future__ import annotations

from dataclasses import dataclass, field

from backend.llm.client import LLMClient, Message
from backend.llm.prompt_builder import PLAN_SYSTEM_PROMPT, build_plan_prompt
from backend.utils.helpers import extract_json


@dataclass
class Plan:
    understanding: str
    root_cause: str
    files_to_change: list[str]
    steps: list[str]
    risks: list[str]
    test_strategy: str
    raw: dict = field(default_factory=dict)


def make_plan(llm: LLMClient, request: str, context: str, repo_profile: dict) -> Plan:
    user_prompt = build_plan_prompt(request, context, repo_profile)
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

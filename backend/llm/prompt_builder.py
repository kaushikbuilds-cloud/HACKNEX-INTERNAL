"""Builds the system/user prompts for the planning and code-generation LLM
calls in one place, so prompt wording changes don't scatter across files."""

from __future__ import annotations

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

CODEGEN_SYSTEM_PROMPT = """You are a senior software engineer making a minimal, surgical code change to ONE file.

Rules:
- Output the COMPLETE new content of the file, nothing else: no markdown fences, no commentary, no explanations.
- Change only what the plan requires. Keep everything else byte-for-byte identical, including unrelated comments, formatting, and whitespace.
- Only use APIs, functions, and imports that already exist in this file or the provided context. Never invent one.
- Do not add unrelated refactors, comments, or cleanup.
- If the file does not need to change, output its content unchanged.
"""


def build_plan_prompt(request: str, context: str, repo_profile: dict) -> str:
    return f"""Repository profile:
{repo_profile}

Relevant code (retrieved by semantic search):
{context}

Task requested by the user:
{request}

Produce the JSON plan now."""


def build_codegen_prompt(
    path: str,
    original_content: str,
    plan_summary: str,
    request: str,
    related_context: str = "",
) -> str:
    return f"""File to edit: {path}

Current content:
```
{original_content}
```

Overall task: {request}

Plan for this change: {plan_summary}

Related code elsewhere in the repo, for context only (do not copy unless genuinely reusing it):
{related_context}

Output the complete new content of {path} now."""

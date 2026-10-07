"""Diagram step 6: Code Generation Agent. Asks the LLM to rewrite one file
at a time, given its full current content plus the plan — whole-file
rewrite is far more reliable than asking a small local model to produce
correct unified-diff hunks, and we diff it ourselves afterward."""

from __future__ import annotations

from dataclasses import dataclass

from ..llm.client import LLMClient, Message

CODEGEN_SYSTEM_PROMPT = """You are a senior software engineer making a minimal, surgical code change to ONE file.

Rules:
- Output the COMPLETE new content of the file, nothing else: no markdown fences, no commentary, no explanations.
- Change only what the plan requires. Keep everything else byte-for-byte identical, including unrelated comments, formatting, and whitespace.
- Only use APIs, functions, and imports that already exist in this file or the provided context. Never invent one.
- Do not add unrelated refactors, comments, or cleanup.
- If the file does not need to change, output its content unchanged.
"""


@dataclass
class FileEdit:
    path: str
    original: str
    new: str

    @property
    def changed(self) -> bool:
        return self.original != self.new


def generate_file_edit(
    llm: LLMClient,
    path: str,
    original_content: str,
    plan_summary: str,
    request: str,
    related_context: str = "",
) -> FileEdit:
    user_prompt = f"""File to edit: {path}

Current content:
```
{original_content}
```

Overall task: {request}

Plan for this change: {plan_summary}

Related code elsewhere in the repo, for context only (do not copy unless genuinely reusing it):
{related_context}

Output the complete new content of {path} now."""

    messages = [
        Message("system", CODEGEN_SYSTEM_PROMPT),
        Message("user", user_prompt),
    ]
    new_content = llm.chat(messages, temperature=0.1)
    new_content = _strip_fences(new_content)
    return FileEdit(path=path, original=original_content, new=new_content)


def _strip_fences(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines[-1].strip() == "```":
            lines = lines[1:-1]
        else:
            lines = lines[1:]
        return "\n".join(lines) + "\n"
    return text

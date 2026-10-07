from __future__ import annotations

import json


def extract_json(text: str) -> dict:
    """LLMs wrap JSON in prose/fences sometimes; pull out the first {...} block."""
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError(f"No JSON object found in LLM output: {text[:200]!r}")
    return json.loads(text[start : end + 1])


def strip_code_fences(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines[-1].strip() == "```":
            lines = lines[1:-1]
        else:
            lines = lines[1:]
        return "\n".join(lines) + "\n"
    return text

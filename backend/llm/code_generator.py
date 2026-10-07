"""Code Generation Agent: asks the LLM to rewrite one file at a time, given
its full current content plus the plan — whole-file rewrite is far more
reliable than asking a small local model to produce correct unified-diff
hunks, and we diff it ourselves afterward."""

from __future__ import annotations

from dataclasses import dataclass

from backend.llm.client import LLMClient, Message
from backend.llm.prompt_builder import CODEGEN_SYSTEM_PROMPT, build_codegen_prompt
from backend.utils.helpers import strip_code_fences


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
    user_prompt = build_codegen_prompt(
        path, original_content, plan_summary, request, related_context
    )
    messages = [
        Message("system", CODEGEN_SYSTEM_PROMPT),
        Message("user", user_prompt),
    ]
    new_content = llm.chat(messages, temperature=0.1)
    new_content = strip_code_fences(new_content)
    return FileEdit(path=path, original=original_content, new=new_content)

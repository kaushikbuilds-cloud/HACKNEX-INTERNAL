"""Code Generation Agent: asks the LLM to rewrite one file at a time, given
its full current content plus the plan — whole-file rewrite is far more
reliable than asking a small local model to produce correct unified-diff
hunks, and we diff it ourselves afterward.

For files above LARGE_FILE_LINE_THRESHOLD, whole-file rewrite breaks down:
it won't fit a local model's context window, and accuracy on a full rewrite
of thousands of lines is poor even when it does. generate_chunk_edit
instead edits just the one function/class the plan targets and splices it
back into the file by line range."""

from __future__ import annotations

from dataclasses import dataclass

from backend.llm.client import LLMClient, Message
from backend.llm.prompt_builder import (
    CODEGEN_SYSTEM_PROMPT,
    CHUNK_CODEGEN_SYSTEM_PROMPT,
    build_chunk_codegen_prompt,
    build_codegen_prompt,
)
from backend.repository.parser import Chunk
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


def generate_chunk_edit(
    llm: LLMClient,
    path: str,
    original_content: str,
    chunk: Chunk,
    plan_summary: str,
    request: str,
    related_context: str = "",
) -> FileEdit:
    """Edit only `chunk` (a function/class the planner/retriever identified
    as the relevant one) and splice the result back into the full file."""
    user_prompt = build_chunk_codegen_prompt(
        path, chunk.name, chunk.kind, chunk.text, plan_summary, request, related_context
    )
    messages = [
        Message("system", CHUNK_CODEGEN_SYSTEM_PROMPT),
        Message("user", user_prompt),
    ]
    new_chunk_text = strip_code_fences(llm.chat(messages, temperature=0.1)).rstrip("\n")

    lines = original_content.splitlines()
    before = lines[: chunk.start_line - 1]
    after = lines[chunk.end_line :]
    new_lines = before + new_chunk_text.splitlines() + after
    new_content = "\n".join(new_lines)
    if original_content.endswith("\n"):
        new_content += "\n"

    return FileEdit(path=path, original=original_content, new=new_content)

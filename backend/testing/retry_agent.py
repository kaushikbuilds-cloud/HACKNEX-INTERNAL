"""Self-Healing Retry Loop: if tests fail, read the error, feed it back to
the code-generation agent along with the plan, and retry up to a fixed
number of attempts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from backend.core.config import settings
from backend.core.constants import LARGE_FILE_LINE_THRESHOLD
from backend.embeddings.chromadb_manager import ChromaDBManager
from backend.embeddings.vector_search import best_chunk_in_file
from backend.llm.client import LLMClient
from backend.llm.code_generator import FileEdit, generate_chunk_edit, generate_file_edit
from backend.patch.apply_patch import apply_edits
from backend.planner.change_planner import Plan
from backend.repository.repository_profile import RepositoryProfile
from backend.testing.validator import TestReport, failure_excerpt, run_validation


def _sibling_edits_context(edits_so_far: list[FileEdit], max_chars: int = 4000) -> str:
    """Format the files already edited in this attempt, so the next file's
    generation call can see their new content, not just their pre-edit
    state from the retrieval context."""
    if not edits_so_far:
        return ""
    blocks = []
    budget = max_chars
    for edit in edits_so_far:
        if not edit.changed:
            continue
        block = f"### {edit.path} (just changed in this same attempt)\n```\n{edit.new}\n```\n"
        if len(block) > budget:
            break
        blocks.append(block)
        budget -= len(block)
    if not blocks:
        return ""
    return "Files already edited in this attempt (for consistency with them):\n" + "\n".join(blocks)


@dataclass
class HealResult:
    report: TestReport
    edits: list[FileEdit]
    attempts: int
    healed: bool


def generate_and_validate(
    llm: LLMClient,
    root: Path,
    profile: RepositoryProfile,
    plan: Plan,
    request: str,
    related_context: str,
    branch: str,
    max_attempts: int | None = None,
    store: ChromaDBManager | None = None,
    python_executable: str | None = None,
) -> HealResult:
    max_attempts = max_attempts or settings.max_retry_attempts
    attempt = 0
    last_report: TestReport | None = None
    edits: list[FileEdit] = []
    extra_note = ""

    while attempt < max_attempts:
        attempt += 1
        edits = []
        for rel_path in plan.files_to_change:
            full_path = Path(root) / rel_path
            original = full_path.read_text() if full_path.exists() else ""
            plan_summary = "\n".join(plan.steps) + extra_note
            is_large = len(original.splitlines()) > LARGE_FILE_LINE_THRESHOLD

            # Files already edited earlier in THIS attempt are shown to the
            # next file's generation call, so a paired change (e.g. a
            # backend validator and its matching frontend regex) stays
            # consistent instead of each file being generated blind to
            # what the others just became.
            sibling_context = _sibling_edits_context(edits)
            combined_context = (
                f"{related_context}\n\n{sibling_context}" if sibling_context else related_context
            )

            chunk = best_chunk_in_file(store, rel_path, request) if (is_large and store) else None
            if chunk is not None:
                edit = generate_chunk_edit(
                    llm, rel_path, original, chunk, plan_summary, request, combined_context
                )
            else:
                edit = generate_file_edit(
                    llm, rel_path, original, plan_summary, request, combined_context
                )
            edits.append(edit)

        apply_edits(root, edits, branch)
        last_report = run_validation(
            root, profile, skip_install=attempt > 1, python_executable=python_executable
        )

        if last_report.passed:
            return HealResult(last_report, edits, attempt, healed=attempt > 1)

        excerpt = failure_excerpt(last_report)
        extra_note = f"\n\nThe previous attempt failed validation with this error — fix it:\n{excerpt}"

    return HealResult(last_report, edits, attempt, healed=False)

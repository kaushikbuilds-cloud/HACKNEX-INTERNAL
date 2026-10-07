"""Map each source file to its likely test file(s), so the planner and the
validator can reason about "which existing tests cover this change"."""

from __future__ import annotations

from pathlib import Path

from backend.repository.file_classifier import classify_repo


def analyze_tests(root: Path) -> dict:
    root = Path(root)
    buckets = classify_repo(root)
    source_files = buckets["source"]
    test_files = buckets["test"]

    coverage_map: dict[str, list[str]] = {}
    for src in source_files:
        stem = Path(src).stem
        matches = [
            t
            for t in test_files
            if stem in Path(t).stem.replace("test_", "").replace("_test", "")
        ]
        if matches:
            coverage_map[src] = matches

    untested = [s for s in source_files if s not in coverage_map]

    return {
        "test_files": test_files,
        "coverage_map": coverage_map,
        "source_files_without_an_obvious_test": untested,
    }

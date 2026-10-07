"""Repository Intelligence: detect language, framework, build tool, test
framework, and map project structure from file-extension counts and
well-known marker files (no LLM call needed)."""

from __future__ import annotations

import json
from pathlib import Path

from backend.core.constants import EXT_LANG
from backend.repository.repository_profile import RepositoryProfile
from backend.utils.file_utils import safe_read_text, walk_files


def scan_repo(root: Path) -> RepositoryProfile:
    root = Path(root)
    lang_counts: dict[str, int] = {}
    structure: dict[str, int] = {}
    file_count = 0

    for f in walk_files(root):
        file_count += 1
        lang = EXT_LANG.get(f.suffix)
        if lang:
            lang_counts[lang] = lang_counts.get(lang, 0) + 1
        top = f.relative_to(root).parts[0]
        structure[top] = structure.get(top, 0) + 1

    languages = sorted(lang_counts, key=lang_counts.get, reverse=True)

    profile = RepositoryProfile(
        root=str(root),
        languages=languages,
        file_count=file_count,
        structure=structure,
    )

    _detect_python(root, profile)
    _detect_node(root, profile)

    return profile


def _detect_python(root: Path, profile: RepositoryProfile) -> None:
    has_marker = (
        (root / "setup.py").exists()
        or (root / "pyproject.toml").exists()
        or (root / "requirements.txt").exists()
    )
    if not has_marker and "python" not in profile.languages:
        return

    # "{python}" is substituted by validator.run_command with the session's
    # sandbox venv interpreter when one exists, so install/test run isolated
    # from the host's own environment — falls back to the host interpreter
    # otherwise (see backend/sandbox/venv_manager.py).
    if (root / "pyproject.toml").exists():
        profile.build_tool = "pip"
        profile.install_command = "{python} -m pip install -e ."
    elif (root / "requirements.txt").exists():
        profile.build_tool = "pip"
        profile.install_command = "{python} -m pip install -r requirements.txt"
    elif (root / "setup.py").exists():
        profile.build_tool = "pip"
        profile.install_command = "{python} -m pip install -e ."

    has_pytest_ini = (root / "pytest.ini").exists() or (root / "conftest.py").exists()
    has_tests_dir = (root / "tests").is_dir() or (root / "test").is_dir()
    pyproject_text = safe_read_text(root / "pyproject.toml")
    if has_pytest_ini or has_tests_dir or "pytest" in pyproject_text:
        profile.test_framework = "pytest"
        profile.test_command = "{python} -m pytest -q"


def _detect_node(root: Path, profile: RepositoryProfile) -> None:
    pkg = root / "package.json"
    if not pkg.exists():
        return

    try:
        data = json.loads(safe_read_text(pkg) or "{}")
    except json.JSONDecodeError:
        return

    profile.build_tool = "npm"
    profile.install_command = "npm install"
    scripts = data.get("scripts", {})
    if "build" in scripts:
        profile.build_command = "npm run build"
    if "test" in scripts:
        profile.test_command = "npm test"
        dev_deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
        if "jest" in dev_deps:
            profile.test_framework = "jest"
        elif "vitest" in dev_deps:
            profile.test_framework = "vitest"
        elif "mocha" in dev_deps:
            profile.test_framework = "mocha"

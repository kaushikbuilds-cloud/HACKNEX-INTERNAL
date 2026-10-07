"""Workflow 1, step 3 (Repository Intelligence): detect language, framework,
build tool, test framework, and map project structure — without an LLM,
from file-extension counts and well-known marker files."""

from __future__ import annotations

from pathlib import Path

from .profile import RepoProfile

EXT_LANG = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".go": "go",
    ".java": "java",
    ".rb": "ruby",
    ".rs": "rust",
    ".c": "c",
    ".cpp": "cpp",
    ".cs": "csharp",
}

IGNORE_DIRS = {
    ".git",
    "node_modules",
    "venv",
    ".venv",
    "__pycache__",
    "dist",
    "build",
    ".tox",
    "target",
    "vendor",
}


def _walk_files(root: Path):
    for p in root.rglob("*"):
        if p.is_file() and not any(part in IGNORE_DIRS for part in p.parts):
            yield p


def scan_repo(root: Path) -> RepoProfile:
    root = Path(root)
    lang_counts: dict[str, int] = {}
    structure: dict[str, int] = {}
    file_count = 0

    for f in _walk_files(root):
        file_count += 1
        lang = EXT_LANG.get(f.suffix)
        if lang:
            lang_counts[lang] = lang_counts.get(lang, 0) + 1
        top = f.relative_to(root).parts[0]
        structure[top] = structure.get(top, 0) + 1

    languages = sorted(lang_counts, key=lang_counts.get, reverse=True)

    profile = RepoProfile(
        root=str(root),
        languages=languages,
        file_count=file_count,
        structure=structure,
    )

    _detect_python(root, profile)
    _detect_node(root, profile)

    return profile


def _detect_python(root: Path, profile: RepoProfile) -> None:
    if not (root / "setup.py").exists() and not (root / "pyproject.toml").exists() \
            and not (root / "requirements.txt").exists() and "python" not in profile.languages:
        return

    if (root / "pyproject.toml").exists():
        profile.build_tool = "pip"
        profile.install_command = "pip install -e ."
    elif (root / "requirements.txt").exists():
        profile.build_tool = "pip"
        profile.install_command = "pip install -r requirements.txt"
    elif (root / "setup.py").exists():
        profile.build_tool = "pip"
        profile.install_command = "pip install -e ."

    has_pytest_ini = (root / "pytest.ini").exists() or (root / "conftest.py").exists()
    has_tests_dir = (root / "tests").is_dir() or (root / "test").is_dir()
    if has_pytest_ini or has_tests_dir or "pytest" in _read(root / "pyproject.toml"):
        profile.test_framework = "pytest"
        profile.test_command = "pytest -q"


def _detect_node(root: Path, profile: RepoProfile) -> None:
    pkg = root / "package.json"
    if not pkg.exists():
        return
    import json

    try:
        data = json.loads(pkg.read_text())
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


def _read(path: Path) -> str:
    try:
        return path.read_text()
    except OSError:
        return ""

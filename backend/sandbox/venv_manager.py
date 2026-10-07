"""Per-session sandbox: an isolated Python venv for the *target* repo's own
dependencies, built right after clone and reused for every install/build/test
subprocess call in that session.

Why this exists: `run_command()` in testing/validator.py used to run a
target repo's install/build/test commands (e.g. "pip install -r
requirements.txt", "pytest -q") with whatever `pip`/`python` happened to be
first on PATH — the host's own interpreter. That means:
  - a target repo's dependencies get installed into (and can conflict with)
    the host's own environment, which this whole backend also runs in;
  - a target repo whose dependency isn't already present on the host
    (e.g. `python-jose`) fails with an opaque ModuleNotFoundError that has
    nothing to do with the actual code being reviewed;
  - two sessions loading two different repos with incompatible pinned
    versions would stomp on each other, since there's only one host env.

Each session instead gets its own venv under <workdir>/.sandboxes/<id>/,
with the target repo's own requirements installed into it. Static analysis
and security scanning are deliberately NOT routed through this sandbox —
they parse source text only (see static_analyzer.py / security_scanner.py
docstrings) and never import target code, so they have no dependency on the
target repo's packages and keep using the host interpreter, which already
has pyflakes/bandit installed once rather than per-session.

Best-effort throughout: if venv creation or the dependency install fails
(offline, no `venv` module, a pinned version that won't resolve, etc.) we
fall back to the host interpreter rather than blocking repo load. Static
analysis and security scanning are unaffected either way; only a target
repo's own install/build/test commands degrade back to today's behavior."""

from __future__ import annotations

import shutil
import subprocess
import sys
import venv
from dataclasses import dataclass, field
from pathlib import Path

INSTALL_TIMEOUT = 300


@dataclass
class Sandbox:
    python: str  # path to the venv's python, or sys.executable on fallback
    isolated: bool  # True if this is a real per-repo venv, not the host interpreter
    install_log: str = ""
    warnings: list[str] = field(default_factory=list)


def _venv_python(venv_dir: Path) -> Path:
    if sys.platform == "win32":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def _host_fallback(reason: str) -> Sandbox:
    return Sandbox(python=sys.executable, isolated=False, warnings=[reason])


def build_sandbox(root: Path, venv_dir: Path) -> Sandbox:
    """Create an isolated venv at venv_dir for the Python repo at root, and
    install its own requirements.txt / setup.py / pyproject.toml into it.
    No-ops (host fallback) for repos with no Python dependency file at all —
    there's nothing to isolate."""
    has_python_deps = any(
        (root / name).exists() for name in ("requirements.txt", "setup.py", "pyproject.toml")
    )
    if not has_python_deps:
        return _host_fallback("no requirements.txt/setup.py/pyproject.toml — nothing to sandbox")

    try:
        venv.EnvBuilder(with_pip=True, clear=True).create(venv_dir)
    except Exception as exc:  # noqa: BLE001 — any venv-creation failure degrades, never blocks
        return _host_fallback(f"venv creation failed ({exc}); using host interpreter")

    python = str(_venv_python(venv_dir))
    if not Path(python).exists():
        return _host_fallback("venv created but python executable missing; using host interpreter")

    req_file = root / "requirements.txt"
    if req_file.exists():
        install_cmd = [python, "-m", "pip", "install", "-r", str(req_file)]
    else:
        install_cmd = [python, "-m", "pip", "install", "-e", str(root)]

    warnings: list[str] = []
    log = ""
    try:
        proc = subprocess.run(
            install_cmd, cwd=root, capture_output=True, text=True, timeout=INSTALL_TIMEOUT,
        )
        log = (proc.stdout or "") + (proc.stderr or "")
        if proc.returncode != 0:
            warnings.append(
                "dependency install into the sandbox failed (see install_log) — "
                "install/build/test commands may still fail on missing packages"
            )
    except subprocess.TimeoutExpired:
        warnings.append("dependency install timed out — sandbox venv created but deps may be incomplete")
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"dependency install failed to run: {exc}")

    # Many repos run their tests with pytest in CI without ever listing it
    # as their own dependency (they assume it's "just available"). Isolating
    # into a clean venv would otherwise turn that assumption into a hard
    # ModuleNotFoundError that has nothing to do with the code under review,
    # so make sure the test *runner* itself is present regardless of what
    # the target repo declares — same idea as tox/nox installing their own
    # test tooling into each environment they manage.
    try:
        subprocess.run(
            [python, "-m", "pip", "install", "pytest"],
            cwd=root, capture_output=True, text=True, timeout=60,
        )
    except Exception:  # noqa: BLE001 — best-effort; a missing pytest surfaces as a test failure, not a crash
        pass

    return Sandbox(python=python, isolated=True, install_log=log, warnings=warnings)


def cleanup_sandbox(venv_dir: Path) -> None:
    shutil.rmtree(venv_dir, ignore_errors=True)

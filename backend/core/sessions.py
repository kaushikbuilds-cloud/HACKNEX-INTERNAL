"""In-memory session store: holds the loaded repo/profile/index/plan/result
for each session_id between API calls. Single-process only — fine for a
local dev/demo deployment; swap for Redis if this needs to scale out."""

from __future__ import annotations

import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Session:
    id: str
    root: Path | None = None
    profile: Any = None
    store: Any = None
    plan: Any = None
    heal: Any = None
    baseline: Any = None
    diff: str = ""
    base_ref: str | None = None  # branch the repo was on before the agent touched it
    sandbox: Any = None  # backend.sandbox.venv_manager.Sandbox, once the repo is loaded

    @property
    def python_executable(self) -> str:
        """The interpreter install/build/test commands should run with —
        the session's isolated sandbox venv if one was built, else the host
        interpreter (e.g. before load completes, or on sandbox fallback)."""
        if self.sandbox is not None:
            return self.sandbox.python
        return sys.executable


_sessions: dict[str, Session] = {}


def create_session() -> Session:
    sid = uuid.uuid4().hex[:12]
    session = Session(id=sid)
    _sessions[sid] = session
    return session


def get_session(session_id: str) -> Session | None:
    return _sessions.get(session_id)

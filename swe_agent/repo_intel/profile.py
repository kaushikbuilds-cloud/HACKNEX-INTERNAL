from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RepoProfile:
    root: str
    languages: list[str] = field(default_factory=list)
    build_tool: str | None = None  # pip, poetry, npm, maven, gradle, ...
    test_framework: str | None = None  # pytest, jest, junit, ...
    test_command: str | None = None
    install_command: str | None = None
    build_command: str | None = None
    file_count: int = 0
    structure: dict = field(default_factory=dict)  # top-level dir -> file count

    def to_dict(self) -> dict:
        return self.__dict__

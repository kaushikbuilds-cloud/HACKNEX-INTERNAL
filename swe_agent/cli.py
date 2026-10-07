from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

from .orchestrator import run_pipeline

app = typer.Typer(help="AI Software Engineering Agent")
console = Console()


@app.command()
def fix(
    repo: str = typer.Option(..., "--repo", help="Git URL or local path to the target repository"),
    issue: str = typer.Option(..., "--issue", help="Natural-language description of the bug/feature"),
    workdir: Path = typer.Option(Path("./workdir"), "--workdir", help="Where to clone/work"),
    branch: str = typer.Option("swe-agent/auto-fix", "--branch"),
    out: Path = typer.Option(Path("./out"), "--out", help="Where to write the patch/report"),
):
    """Read a codebase, understand it, fix the bug or add the feature, and verify nothing broke."""
    result = run_pipeline(repo, issue, workdir, branch=branch)

    out.mkdir(parents=True, exist_ok=True)
    (out / "patch.diff").write_text(result.diff)
    (out / "explanation.md").write_text(result.explanation())
    (out / "test_report.txt").write_text(
        f"BASELINE (before change)\n{result.baseline.summary()}\n\n"
        f"FINAL (after change, attempt {result.heal.attempts})\n{result.heal.report.summary()}\n"
    )

    status = "[bold green]PASSED[/]" if result.success else "[bold red]FAILED[/]"
    console.print(Panel(result.explanation(), title=f"Result: {status}"))
    console.print(f"Patch written to {out / 'patch.diff'}")

    if not result.success:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()

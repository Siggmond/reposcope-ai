from __future__ import annotations

import importlib.metadata
from pathlib import Path

import typer
from rich.console import Console

from reposcope import __version__
from reposcope.src.report.writer import write_reports
from reposcope.src.scanner.repo_loader import load_repo

app = typer.Typer(add_completion=False, invoke_without_command=True)
console = Console()


def _version() -> str:
    try:
        return importlib.metadata.version("reposcope-ai")
    except importlib.metadata.PackageNotFoundError:
        return __version__


@app.callback()
def _main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        help="Show version and exit",
        is_eager=True,
    ),
) -> None:
    if version:
        console.print(_version())
        raise typer.Exit(code=0)


@app.command()
def analyze(
    target: str = typer.Argument(..., help="Local path or GitHub URL"),
    output_dir: Path = typer.Option(
        Path(".reposcope"), "--output", "-o", help="Output folder"
    ),
    use_ai: bool = typer.Option(False, "--ai", help="Enable optional AI helpers"),
    aggressive: bool = typer.Option(
        False,
        "--aggressive",
        help="Enable optional heuristic analyzers (labeled [heuristic])",
    ),
    diff_base: str | None = typer.Option(
        None,
        "--diff",
        help="Compute deterministic PR impact against a git base ref (uses `git diff --name-only <base>`)",
    ),
) -> None:
    repo = load_repo(target)
    write_reports(
        repo=repo,
        output_dir=output_dir,
        use_ai=use_ai,
        aggressive=aggressive,
        diff_base=diff_base,
    )

    console.print(f"Wrote reports to: {output_dir.resolve()}")


if __name__ == "__main__":
    app()

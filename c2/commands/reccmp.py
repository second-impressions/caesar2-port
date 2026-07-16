"""Project-facing commands for the pinned Watcom-aware reccmp fork."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
from typing import Annotated, Optional

import typer

from c2.reccmp_project import BUILD_FILE, PROJECT_FILE, USER_FILE, write_user_config


app = typer.Typer(
    help="Run the Watcom-aware whole-binary reccmp workflow.",
    no_args_is_help=True,
)


def _require_configuration() -> None:
    missing = [
        path for path in (PROJECT_FILE, USER_FILE, BUILD_FILE) if not path.is_file()
    ]
    if missing:
        rendered = ", ".join(str(path) for path in missing)
        raise typer.BadParameter(
            f"missing reccmp configuration: {rendered}; run "
            "`c2 reccmp prepare` and `c2 rebuild` first"
        )


def _run_module(module: str, extra_args: list[str]) -> None:
    command = [sys.executable, "-m", module, "--target", "C2", *extra_args]
    completed = subprocess.run(command, check=False)
    if completed.returncode:
        raise typer.Exit(completed.returncode)


@app.command("prepare")
def prepare(
    original: Annotated[
        Path,
        typer.Option("--original", help="Original debug-build PS.EXE."),
    ] = Path("original/PS.EXE"),
    windows_original: Annotated[
        Optional[Path],
        typer.Option(
            "--windows-original",
            help="Original Windows build A CAESAR2.EXE for C2WIN annotations.",
        ),
    ] = None,
) -> None:
    """Validate original binaries and write the ignored reccmp-user.yml."""
    try:
        path = write_user_config(original, windows_original=windows_original)
    except (FileNotFoundError, ValueError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1) from exc
    targets = "C2 and C2WIN" if windows_original is not None else "C2"
    typer.echo(f"wrote {path} for {targets}")


_PASSTHROUGH = {"allow_extra_args": True, "ignore_unknown_options": True}


@app.command("code", context_settings=_PASSTHROUGH)
def code(ctx: typer.Context) -> None:
    """Run reccmp's function report; all additional options pass through."""
    _require_configuration()
    _run_module("reccmp.tools.asmcmp", list(ctx.args))


@app.command("data", context_settings=_PASSTHROUGH)
def data(ctx: typer.Context) -> None:
    """Run reccmp's initialized-data report; options pass through."""
    _require_configuration()
    _run_module("reccmp.tools.datacmp", list(ctx.args))

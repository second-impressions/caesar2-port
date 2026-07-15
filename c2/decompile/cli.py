"""``c2 decompile`` — the typer subcommand.

Wires the orchestrator behind a small typer command added to the
main ``c2`` app in ``c2/app.py``.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Optional

import typer

from c2.decompile.agent import DEFAULT_MODEL_ID
from c2.decompile.models import Target, Verdict
from c2.decompile.orchestrator import OrchestratorConfig, run_orchestrator
from c2.decompile.selectors import cli_describe, resolve
from c2.decompile.workspace import DEFAULT_RUNS_ROOT


def decompile_cmd(
    selectors: list[str] = typer.Argument(
        ...,
        help=(
            "One or more function names or source files.  "
            "Function name (e.g. mouse_follow_cohort) or file basename "
            "(e.g. map.c / decomp/src/map.c -- every diffing function "
            "in that file is queued).  Can be repeated."
        ),
        metavar="SELECTOR...",
    ),
    batch: int = typer.Option(
        4, "--batch", "-b",
        help="Max concurrent agents (default 4).",
    ),
    count: int = typer.Option(
        1, "--count", "-n",
        help=(
            "Replicas per function: race N independent agents on EACH "
            "selected function (default 1).  Each replica gets its own "
            "run dir + live reporter row (labelled ``<fn>#NN``).  "
            "Per-agent auto-apply is SUPPRESSED during a race (concurrent "
            "writers to one TU is the parallel-clobber hazard); instead "
            "the single best replica per function is applied ONCE after "
            "the race (unless --no-apply).  Use --batch to bound how many "
            "of the N run concurrently."
        ),
    ),
    target: Target = typer.Option(
        Target.WATCOM, "--target", "-t",
        help="Compile target + byte oracle (watcom = PS.EXE, msvc = CAESAR2.EXE).",
    ),
    model: str = typer.Option(
        DEFAULT_MODEL_ID, "--model",
        help=(
    "Pydantic-AI model id.  ``deepseek:<name>`` uses DeepSeek's "
            "OpenAI-compatible API (needs DEEPSEEK_API_KEY).  Custom "
            "prefixes recognised by this CLI: ``neuralwatt:`` / "
            "``requesty:`` (OpenAI-compatible), ``anthropic-proxy:`` / "
            "``anthropic-proxy2:`` (local pi-runtime Anthropic proxy at "
            "localhost:8000 / 8800; see ~/.pi/agent/models.json).  Any "
            "other ``provider:name`` pair is passed through to pydantic-ai "
            "(e.g. ``anthropic:claude-opus-4-7`` for the upstream API).  "
            "Short-context models with a long-context sibling on the same "
            "provider (currently neuralwatt:glm-5.2-short -> glm-5.2 and "
            "neuralwatt:glm-5.2-short-fast -> glm-5.2-fast) are wrapped in "
            "a pydantic-ai FallbackModel automatically: the SAME request "
            "rolls over to the long sibling on context-overflow (HTTP 400 "
            "with a 'maximum context length' body), transparent to the "
            "orchestrator and only paid for when actually needed."
        ),
    ),
    max_turns: int = typer.Option(
        200, "--max-turns",
        help=(
            "Per-agent model-request cap.  Default 200 — enough head-room "
            "for the agent to explore several hypotheses without artificial "
            "shutdown; the runaway-cost gate is ``--time-budget``, not turns."
        ),
    ),
    max_tokens: Optional[int] = typer.Option(
        None, "--max-tokens",
        help="Per-request output-token cap.  Provider default if unset.",
    ),
    thinking: Optional[str] = typer.Option(
        "high", "--thinking",
        help=(
            "Reasoning effort for thinking-capable models.  One of "
            "``minimal`` | ``low`` | ``medium`` | ``high`` | ``xhigh`` "
            "(default: high -- these functions need the model to REASON "
            "about the asm before editing; thinking-off runs flailed).  "
            "Pass ``--thinking none`` to disable.  Routes to the provider's "
            "native reasoning channel (Anthropic extended thinking, OpenAI "
            "o-series reasoning_effort, …).  Ignored for models without a "
            "thinking mode (DeepSeek V4 Pro's reasoning is always-on)."
        ),
    ),
    extra_prompt: Optional[str] = typer.Option(
        None, "--extra-prompt",
        help=(
            "Extra text appended to every subagent's system prompt "
            "(under an 'Additional instructions for this run' heading).  "
            "Use it to steer the whole batch toward a specific tactic "
            "for this run without editing the base prompt template."
        ),
    ),
    time_budget: Optional[float] = typer.Option(
        1800.0, "--time-budget",
        help=(
            "Per-agent wall-clock budget in seconds.  Default 1800 "
            "(30 min) — ample head-room for a single agent to drive a "
            "medium-complexity function to byte-exact or to a "
            "classified residue.  Pass ``--time-budget 0`` to disable "
            "the cap entirely (only useful for very large funcs)."
        ),
    ),
    runs_dir: Path = typer.Option(
        DEFAULT_RUNS_ROOT, "--runs-dir",
        help="Sandbox root.  One subdir is created per agent.",
    ),
    apply: bool = typer.Option(
        True, "--apply/--no-apply",
        help=(
            "After each agent finishes, land its best snapshot into\n"
            "decomp/src/ IFF it strictly improves HEAD's layered\n"
            "shape vector (lex on ir > width > spill > seat) or ties\n"
            "shape with strictly fewer bytes.  Per Hard Rule #3,\n"
            "shape > bytes -- an edit that drops shape_distance is\n"
            "PS-faithful even if bytes rose.  Default ON."
        ),
    ),
    jsonl: bool = typer.Option(
        False, "--jsonl",
        help="Emit JSONL events on stdout (machine-readable progress).",
    ),
    trace: bool = typer.Option(
        False, "--trace",
        help=(
            "Enable local OpenTelemetry tracing of agent runs + tool "
            "calls.  100% local: writes JSON-lines to --trace-file and "
            "NEVER sends data to logfire.pydantic.dev or any other "
            "non-explicit endpoint.  Pair with --otlp-endpoint to also "
            "forward to a local OTel collector / Jaeger / Tempo."
        ),
    ),
    trace_file: Optional[Path] = typer.Option(
        None, "--trace-file",
        help=(
            "Where to write the local trace JSONL.  Default: "
            "<runs-dir>/traces.jsonl."
        ),
    ),
    otlp_endpoint: Optional[str] = typer.Option(
        None, "--otlp-endpoint",
        help=(
            "Also ship traces to this OTLP-HTTP endpoint (e.g. "
            "http://localhost:4318 for a local Jaeger / Tempo / OTel "
            "Collector).  Should point at a host you control -- the "
            "orchestrator will not auto-discover any endpoint from "
            "environment variables."
        ),
    ),
    yes: bool = typer.Option(
        False, "--yes", "-y",
        help="Skip the interactive confirmation prompt.",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run",
        help="Resolve selectors + print the target list, then exit.",
    ),
) -> None:
    """Drive N pydantic-ai subagents at byte-exact decompilation in parallel.

    SELECTOR can be either:

    - a function name (e.g. ``mouse_follow_cohort``)
    - a file path/basename (e.g. ``screens.c`` — every diffing
      function in that file is queued)

    Each agent runs in its own sandboxed working directory under
    ``--runs-dir``.  Progress is streamed live to stdout (or JSONL with
    ``--jsonl``).
    """
    project_root = Path.cwd().resolve()

    # In --dry-run we don't want to spend 30s+ refreshing the verify
    # cache when stale -- the user is just inspecting the target list.
    # In the real run path we let the cache helper decide, but warn the
    # user upfront because the first refresh after a source change is
    # genuinely slow (full corpus build).
    if not dry_run:
        from c2.commands.verify_json import CACHE_PATH as _VJ_CACHE
        if not _VJ_CACHE.is_file():
            typer.echo(
                "note: .c2-cache/verify.json missing -- refreshing "
                "(this takes ~30s on first run, then cached)\u2026",
                err=True,
            )
    resolution = resolve(
        selectors, project_root=project_root, no_build=dry_run,
    )

    typer.echo(cli_describe(resolution))

    if not resolution.targets:
        typer.echo("Nothing to do.", err=True)
        raise typer.Exit(code=0 if not resolution.unknown else 1)

    if resolution.skipped_exact:
        typer.echo(
            f"Skipping (already byte-exact): "
            f"{', '.join(resolution.skipped_exact[:6])}"
            + (" ..." if len(resolution.skipped_exact) > 6 else "")
        )
    if resolution.skipped_blocked:
        # Group blocked fns by their blocking donor for a readable summary.
        by_donor: dict[str, list[str]] = {}
        for fn, donor in resolution.skipped_blocked:
            by_donor.setdefault(donor, []).append(fn)
        typer.echo(
            "Skipping (tail-merge-blocked — these resolve automatically "
            "once their donor goes byte-exact):"
        )
        for donor, fns in sorted(by_donor.items()):
            preview = ", ".join(fns[:4])
            if len(fns) > 4:
                preview += f", … ({len(fns)} total)"
            typer.echo(f"  · blocked on {donor}: {preview}")

    typer.echo("\nFunctions to drive:")
    for fn in resolution.targets:
        typer.echo(f"  · {fn}")

    if count > 1:
        typer.echo(
            f"\nRacing {count} replicas per function "
            f"({count * len(resolution.targets)} agents total, "
            f"batch {batch} concurrent)."
        )
        typer.echo(
            "  per-agent auto-apply suppressed; "
            + ("the single best replica per function is applied after the race."
               if apply else "nothing will be applied (--no-apply).")
        )

    if dry_run:
        raise typer.Exit(code=0)

    if not yes and sys.stdin.isatty():
        if not typer.confirm("\nProceed?", default=True):
            raise typer.Exit(code=1)

    cfg = OrchestratorConfig(
        runs_root=runs_dir,
        batch=batch,
        target=target,
        model_id=model,
        thinking=thinking,
        max_turns=max_turns,
        max_tokens=max_tokens,
        # ``--time-budget 0`` from the CLI → None → unlimited.
        time_budget_s=(time_budget if time_budget and time_budget > 0 else None),
        apply_byte_exact=apply,
        count=count,
        jsonl_output=jsonl,
        project_root=project_root,
        trace=trace,
        trace_file=trace_file,
        otlp_endpoint=otlp_endpoint,
        extra_prompt=extra_prompt,
    )

    if trace:
        resolved_trace_file = trace_file or (runs_dir / "traces.jsonl")
        typer.echo(
            f"tracing: ON — local-only → {resolved_trace_file}"
            + (f" + OTLP → {otlp_endpoint}" if otlp_endpoint else "")
        )

    reports = asyncio.run(run_orchestrator(resolution, cfg))

    # Final rich-rendered summary table (the LiveReporter created in
    # the orchestrator owns the console, but its lifetime ended with
    # run_orchestrator -- spin up a fresh ad-hoc one for the table
    # using the same NO_COLOR-honouring style).
    from rich.console import Console as _Console
    from rich.table import Table as _Table
    import os as _os
    console = _Console(no_color=bool(_os.environ.get("NO_COLOR")), markup=True, highlight=False)
    tbl = _Table(title="decompile summary", show_lines=False, expand=False)
    tbl.add_column("function", style="cyan", no_wrap=True)
    tbl.add_column("verdict")
    tbl.add_column("bytes", justify="right")
    tbl.add_column("shape", justify="right")
    tbl.add_column("target")
    _VERDICT_STYLE = {
        Verdict.BYTE_EXACT: "bold green", Verdict.SHAPE_MATCHES: "green",
        Verdict.IMPROVED_PARTIAL: "yellow", Verdict.NO_CHANGE: "dim",
        Verdict.REGRESSED: "red", Verdict.BUILD_BROKEN: "bold red",
    }
    for r in reports:
        vstyle = _VERDICT_STYLE.get(r.verdict, "white")
        bd = r.final_verify.byte_diff
        bd_text = "[bold green]0[/]" if bd == 0 else str(bd)
        shape_text = "—"
        if r.final_verify.shape is not None:
            s = r.final_verify.shape
            ssum = sum(d for d, _ in (s.ir, s.width, s.spill, s.seat))
            shape_text = f"Σ{ssum} → {s.fix_next.value}"
        tbl.add_row(
            r.function, f"[{vstyle}]{r.verdict.value}[/]",
            bd_text, shape_text, r.final_target.value,
        )
    console.print()
    console.print(tbl)
    n_exact = sum(1 for r in reports if r.verdict == Verdict.BYTE_EXACT)
    console.print(f"\n[bold]→[/] {n_exact}/{len(reports)} byte-exact   [dim]run dirs at {runs_dir}[/]")

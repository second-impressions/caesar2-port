"""Per-function byte-diff baseline snapshots.

The `c2 baseline` family lets us freeze the current state of every
decomp function (byte-exact set + per-function diff_byte_count for
the non-exact ones) and later compare against the live state to
detect *any* regression — including:

  1. A previously byte-exact function that now diffs at all.
  2. A previously diffing function whose `diff_byte_count` got
     worse (i.e. the function is "better off before").
  3. A diffing function that vanished entirely (renamed / lost).

Workflow:

    # before starting a risky refactor (Phase 1, etc.)
    uv run c2 baseline save --out baselines/pre-phase1.json

    # after the refactor (or mid-way)
    uv run c2 baseline check baselines/pre-phase1.json

`save` is idempotent and cheap (one `decomp-verify --json` call).
`check` prints a concise table of changes and exits non-zero when
*any* regression is detected, so it can wedge into CI / pre-commit
hooks.

The baseline file format is intentionally small and stable:

```json
{
  "schema": 1,
  "generated_at": "2026-05-08T16:42:31Z",
  "commit": "a8af5d7",
  "cflags": "-bt=dos -mf -4r -s -d1",
  "summary": {"exact": 965, "diff": 556, "compared": 1521, ...},
  "exact": ["fnA", "fnB", ...],         # sorted; covers every byte-exact fn
  "diffs": {                             # only functions with diff_byte_count > 0
    "fnX": {"file": "...", "size": 1234, "byte_diff": 17, "row_diff": 9}
  }
}
```

We store the EXACT set explicitly (not implicitly) so that
post-restructure name changes are easy to spot.
"""

from __future__ import annotations

import contextlib
import datetime as _dt
import io
import json
import re
import subprocess
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from c2.commands.c_source import classify_source
from c2.commands.decomp_verify import decomp_verify, PS_CFLAGS


_ASM_LABEL_RE = re.compile(r"^([a-z_][a-z_0-9]+)_:", re.M)


SCHEMA_VERSION = 1


def _git_head_short() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
        )
        return out.decode().strip()
    except Exception:
        return ""


def _run_verify_json() -> dict:
    """Call ``decomp_verify`` in-process with ``--json --no-strict`` and parse
    the captured stdout.  No subprocess.

    The verifier already routes all human-facing chatter to stderr when
    ``json_out=True``, so stdout is a single JSON document.
    """
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        try:
            decomp_verify(
                c_files=None,
                symbols_json=Path("data/out/symbols.json"),
                exe_path=Path("data/PS.EXE"),
                decomp_dir=Path("decomp"),
                json_out=True,
                strict=False,
                strict_warnings=False,
            )
        except typer.Exit as exc:
            if exc.exit_code not in (0, None):
                raise
    return json.loads(buf.getvalue())


def _shape_baseline(verify: dict) -> dict:
    """Turn a raw decomp-verify --json blob into a compact baseline dict."""
    diffs: dict[str, dict] = {}
    diff_names: set[str] = set()
    for fn in verify.get("functions", []):
        name = fn["name"]
        diff_names.add(name)
        diffs[name] = {
            "file": fn.get("file", ""),
            "size": fn.get("size", 0),
            "byte_diff": fn.get("diff_byte_count", 0),
            "row_diff": fn.get("diff_row_count", 0),
        }

    # Also enumerate asm-defined publics (one per `name_:` label in
    # the hand-written .asm modules).  These are compared by the
    # verifier too but never live in classify_source, so we'd
    # otherwise mis-flag them as "vanished" on every check.
    asm_names: set[str] = set()
    for asm in sorted(Path("decomp/src").glob("*.asm")):
        try:
            asm_names.update(_ASM_LABEL_RE.findall(asm.read_text()))
        except Exception:
            continue

    # Exact functions are implied by (compared - diff): the verifier
    # only emits diffing functions in `functions[]`.  Enumerate every
    # FUNCTION-annotated body by re-parsing the .c files via
    # classify_source, then subtract the diffing set.
    exact: list[str] = []
    for src_path in sorted(Path("decomp/src").glob("*.c")):
        try:
            cs = classify_source(src_path.read_text(), str(src_path))
        except Exception:
            continue
        # An annotated FuncDef whose annotation line maps to kind=FUNCTION
        # is a decompiled body (regardless of byte-exact status).
        # Stubs (kind=STUB) are skipped — they don't compare.
        ann_by_line = cs.annotations
        for fd in cs.func_defs:
            decl_line = getattr(fd.decl, "coord", None)
            line_no = decl_line.line if decl_line else None
            ann = ann_by_line.get(line_no) if line_no else None
            if ann is None or ann.kind != "FUNCTION":
                continue
            name = fd.decl.name
            if name not in diff_names:
                exact.append(name)

    for name in asm_names:
        if name not in diff_names:
            exact.append(name)

    return {
        "schema": SCHEMA_VERSION,
        "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "commit": _git_head_short(),
        "cflags": PS_CFLAGS,
        "summary": verify.get("summary", {}),
        "exact": sorted(set(exact)),
        "diffs": diffs,
    }


# ---------------------------------------------------------------------------
# CLI: save
# ---------------------------------------------------------------------------


def save(
    out: Path = typer.Option(
        Path("baselines/latest.json"),
        "--out",
        "-o",
        help="Where to write the baseline JSON.",
    ),
    label: Optional[str] = typer.Option(
        None,
        "--label",
        "-l",
        help="Free-text label stored in the baseline (e.g. 'pre-phase1').",
    ),
) -> None:
    """Snapshot the current per-function diff state to a JSON file.

    Re-uses `decomp-verify --json --no-strict`, so the snapshot is
    consistent with whatever the verifier currently reports.
    """
    verify = _run_verify_json()
    snapshot = _shape_baseline(verify)
    if label:
        snapshot["label"] = label

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(snapshot, indent=2, sort_keys=False) + "\n")

    s = snapshot["summary"]
    Console(color_system=None).print(
        f"[green]Wrote[/] {out}  "
        f"({s.get('exact', '?')} exact, {s.get('diff', '?')} diff, "
        f"{len(snapshot['exact'])} exact-fn names recorded)"
    )


# ---------------------------------------------------------------------------
# CLI: check
# ---------------------------------------------------------------------------


def check(
    baseline_path: Path = typer.Argument(
        Path("baselines/latest.json"),
        help="Baseline JSON to compare against.",
    ),
    show_improvements: bool = typer.Option(
        True, "--improvements/--no-improvements",
        help="Include improvement rows in the report.",
    ),
    json_out: bool = typer.Option(
        False, "--json",
        help="Emit machine-readable JSON instead of a Rich table.",
    ),
    fail_on_regression: bool = typer.Option(
        True, "--fail-on-regression/--no-fail",
        help="Exit non-zero if any regression is detected.",
    ),
) -> None:
    """Compare the current state to a saved baseline.

    Categorises every function into one of five buckets:

    - **was_exact_now_diff**  (regression: drift from byte-exact)
    - **diff_worse**          (regression: byte_diff grew)
    - **diff_better**         (improvement)
    - **was_diff_now_exact**  (improvement)
    - **vanished**             (function no longer present — likely
                                renamed; treated as warning, not a hard
                                fail by default)

    Exit code is **1** iff `--fail-on-regression` is set and either
    of the first two buckets is non-empty.
    """
    if not baseline_path.exists():
        Console(color_system=None).print(f"[red]Baseline not found:[/] {baseline_path}")
        raise typer.Exit(2)

    base = json.loads(baseline_path.read_text())
    verify = _run_verify_json()
    current = _shape_baseline(verify)

    base_exact = set(base.get("exact", []))
    cur_exact = set(current["exact"])
    base_diffs = base.get("diffs", {})
    cur_diffs = current["diffs"]

    base_known = base_exact | set(base_diffs)
    cur_known = cur_exact | set(cur_diffs)

    was_exact_now_diff: list[dict] = []
    diff_worse: list[dict] = []
    diff_better: list[dict] = []
    was_diff_now_exact: list[str] = []
    vanished: list[str] = []

    for name, cur in cur_diffs.items():
        if name in base_exact:
            was_exact_now_diff.append({
                "name": name,
                "file": cur["file"],
                "size": cur["size"],
                "byte_diff": cur["byte_diff"],
            })
        elif name in base_diffs:
            b = base_diffs[name]["byte_diff"]
            c = cur["byte_diff"]
            if c > b:
                diff_worse.append({
                    "name": name,
                    "file": cur["file"],
                    "size": cur["size"],
                    "before": b,
                    "after": c,
                    "delta": c - b,
                })
            elif c < b:
                diff_better.append({
                    "name": name,
                    "file": cur["file"],
                    "size": cur["size"],
                    "before": b,
                    "after": c,
                    "delta": c - b,
                })
        # if name in neither: new function (post-baseline addition) —
        # not a regression, silent.

    for name in base_diffs:
        if name in cur_exact:
            was_diff_now_exact.append(name)
        elif name not in cur_known:
            vanished.append(name)
    for name in base_exact:
        if name not in cur_known:
            vanished.append(name)

    was_exact_now_diff.sort(key=lambda r: (-r["byte_diff"], r["name"]))
    diff_worse.sort(key=lambda r: (-r["delta"], r["name"]))
    diff_better.sort(key=lambda r: (r["delta"], r["name"]))
    was_diff_now_exact.sort()
    vanished.sort()

    regressions = len(was_exact_now_diff) + len(diff_worse)
    improvements = len(diff_better) + len(was_diff_now_exact)

    if json_out:
        print(json.dumps({
            "baseline": str(baseline_path),
            "baseline_commit": base.get("commit"),
            "baseline_generated_at": base.get("generated_at"),
            "current_commit": current["commit"],
            "summary": {
                "regressions": regressions,
                "improvements": improvements,
                "vanished": len(vanished),
                "was_exact_now_diff": len(was_exact_now_diff),
                "diff_worse": len(diff_worse),
                "diff_better": len(diff_better),
                "was_diff_now_exact": len(was_diff_now_exact),
            },
            "was_exact_now_diff": was_exact_now_diff,
            "diff_worse": diff_worse,
            "diff_better": diff_better if show_improvements else [],
            "was_diff_now_exact": was_diff_now_exact if show_improvements else [],
            "vanished": vanished,
        }, indent=2))
    else:
        c = Console(color_system=None)
        c.print(
            f"\n[bold]Baseline:[/] {baseline_path}  "
            f"(commit {base.get('commit', '?')}, "
            f"{base.get('generated_at', '?')})"
        )
        c.print(
            f"[bold]Current :[/] commit {current['commit'] or '?'}, "
            f"{current['generated_at']}\n"
        )

        if was_exact_now_diff:
            t = Table(
                title=f"REGRESSIONS — were exact, now diff "
                f"({len(was_exact_now_diff)})",
                title_style="red bold",
                show_lines=False,
            )
            t.add_column("name", style="bold")
            t.add_column("file", style="dim")
            t.add_column("size", justify="right")
            t.add_column("byte_diff", justify="right", style="red")
            for r in was_exact_now_diff:
                t.add_row(r["name"], r["file"], str(r["size"]),
                          str(r["byte_diff"]))
            c.print(t)

        if diff_worse:
            t = Table(
                title=f"REGRESSIONS — diff grew "
                f"({len(diff_worse)})",
                title_style="red bold",
                show_lines=False,
            )
            t.add_column("name", style="bold")
            t.add_column("file", style="dim")
            t.add_column("before", justify="right")
            t.add_column("after", justify="right", style="red")
            t.add_column("delta", justify="right", style="red")
            for r in diff_worse:
                t.add_row(r["name"], r["file"], str(r["before"]),
                          str(r["after"]), f"+{r['delta']}")
            c.print(t)

        if show_improvements and diff_better:
            t = Table(
                title=f"improvements — diff shrunk "
                f"({len(diff_better)})",
                title_style="green",
                show_lines=False,
            )
            t.add_column("name", style="bold")
            t.add_column("file", style="dim")
            t.add_column("before", justify="right")
            t.add_column("after", justify="right", style="green")
            t.add_column("delta", justify="right", style="green")
            for r in diff_better:
                t.add_row(r["name"], r["file"], str(r["before"]),
                          str(r["after"]), str(r["delta"]))
            c.print(t)

        if show_improvements and was_diff_now_exact:
            c.print(
                f"\n[green]improvements — now byte-exact "
                f"({len(was_diff_now_exact)}):[/] "
                + ", ".join(was_diff_now_exact)
            )

        if vanished:
            c.print(
                f"\n[yellow]vanished — function no longer compared "
                f"({len(vanished)}):[/] "
                + ", ".join(vanished[:15])
                + (" …" if len(vanished) > 15 else "")
            )

        bs = base.get("summary", {})
        cs = current["summary"]
        c.print(
            f"\nsummary: "
            f"exact {bs.get('exact', '?')} → {cs.get('exact', '?')}  "
            f"diff {bs.get('diff', '?')} → {cs.get('diff', '?')}  "
            f"compared {bs.get('compared', '?')} → {cs.get('compared', '?')}"
        )
        if regressions:
            c.print(
                f"[red bold]{regressions} regression(s)[/]  "
                f"[green]{improvements} improvement(s)[/]"
            )
        else:
            c.print(
                f"[green bold]no regressions[/]  "
                f"[green]{improvements} improvement(s)[/]"
            )

    if fail_on_regression and regressions > 0:
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# Typer sub-app glue
# ---------------------------------------------------------------------------


app = typer.Typer(
    help="Per-function byte-diff baselines (snapshot + regression check).",
    no_args_is_help=True,
)
app.command("save")(save)
app.command("check")(check)

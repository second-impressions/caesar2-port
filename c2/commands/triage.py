"""`c2 triage` -- corpus-wide allocator-residue triage report.

Reads ``.c2-cache/triage.json`` (built from a one-shot
``decomp-verify -v`` capture) and produces an actionable table grouping
the remaining diff functions by their cascade verdict class:

  - **tie-reorder REACHABLE**: pure decl/use-order swap fix.  The
    cascade verdict NAMES the two vars + lines + savings.  ACTION:
    swap the births (Rule 115 decl order / Rule 28a use order).
  - **savings**: the verdict says PS's allocation requires a SAVINGS
    delta on a specific var.  ACTION: change that var's weighted use
    count via the named source-shape lever (chain/split, inline a
    single-use temp, add/remove a re-read).
  - **unreachable**: search exhausted; NO single allocation-order
    move/swap reproduces PS.  ACTION: STOP grinding decl/use-order
    levers -- the difference is in masks/ranges (live-range shape,
    candidate narrowing) or a non-allocator mechanism (rover,
    treegen).  Document with a PROBE comment.
  - **inconclusive**: search budget hit before space exhausted (big
    routines).  ACTION: re-run with --budget or focus the search.
  - **no-cascade**: no register-swap diff -- the function is in a
    different class entirely (frame-shift, tail-merge, semantic
    divergence, etc.).  Use the dossier.

This complements the dossier's per-function view by giving the
corpus-wide picture in one read.

Build the cache with::

    c2 triage --rebuild     # ~3 min full verify-v capture

Refresh after meaningful source changes.  The triage cache is
gitignored (corpus-snapshot data).
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Annotated

import typer

_CACHE = Path(".c2-cache/triage.json")


def _classify(t: dict) -> str:
    cas = t.get("cascade", [])
    if not cas:
        return "no-cascade"
    if any("REACHABLE by TIE-REORDER" in l for l in cas):
        return "tie-reorder REACHABLE"
    if any("needs a SAVINGS" in l for l in cas):
        return "savings"
    if any("UNRELIABLE for H2" in l for l in cas):
        return "h2-unreliable"
    if any("UNREACHABLE" in l for l in cas):
        return "unreachable"
    if any("INCONCLUSIVE" in l for l in cas):
        return "inconclusive"
    return "other"


def _rebuild_cache(out: Path) -> dict:
    """Run ``decomp-verify -v`` once, parse every Cascade / PS-alloc /
    Prologue / Regalloc / Rule-hint line per function, and persist."""
    typer.secho("Running decomp-verify -v --no-mac-decompile "
                "(may take 1-3 min) ...", fg="cyan")
    r = subprocess.run(
        ["uv", "run", "c2", "decomp-verify", "-v", "--no-mac-decompile"],
        capture_output=True, text=True,
    )
    text = r.stdout + "\n" + r.stderr
    triage: dict[str, dict] = {}
    cur = None
    for line in text.splitlines():
        m = re.search(r"^\s*\u2717\s+(\S+)", line)
        if m:
            cur = m.group(1)
            triage[cur] = {
                "byte_diff": 0,
                "cascade": [],
                "ps_alloc": [],
                "prologue": [],
                "regalloc": [],
                "rule_hints": [],
                "neg_corpus": [],
                "mac": None,
            }
            continue
        if cur is None:
            continue
        s = line.strip()
        if "Cascade:" in s:
            triage[cur]["cascade"].append(s)
        elif "PS-alloc:" in s:
            triage[cur]["ps_alloc"].append(s)
        elif s.startswith("Prologue hint:"):
            triage[cur]["prologue"].append(s)
        elif s.startswith("Regalloc:"):
            triage[cur]["regalloc"].append(s)
        elif s.startswith("Rule hints:"):
            triage[cur]["rule_hints"].append(s)
        elif s.startswith("Neg-corpus:"):
            triage[cur]["neg_corpus"].append(s)
        elif s.startswith("mac:"):
            triage[cur]["mac"] = s
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(triage, indent=1))
    typer.secho(f"Wrote triage for {len(triage)} functions to {out}",
                fg="green")
    return triage


def triage(
    klass: Annotated[
        str,
        typer.Argument(
            help="Show functions of this class: tie-reorder | savings | "
                 "unreachable | inconclusive | no-cascade | all"),
    ] = "all",
    rebuild: Annotated[
        bool,
        typer.Option("--rebuild",
                     help="Re-run decomp-verify -v to refresh the cache"),
    ] = False,
    summary: Annotated[
        bool,
        typer.Option("--summary", "-s",
                     help="Just print the per-class counts and exit"),
    ] = False,
    name: Annotated[
        str | None,
        typer.Option("--fn", help="Show only this function"),
    ] = None,
    limit: Annotated[
        int,
        typer.Option("--limit", "-n",
                     help="Limit number of functions shown per class"),
    ] = 50,
) -> None:
    """Corpus-wide allocator-residue triage report."""
    if rebuild or not _CACHE.exists():
        data = _rebuild_cache(_CACHE)
    else:
        data = json.loads(_CACHE.read_text())

    # group by class
    by_cls: dict[str, list[tuple[str, dict]]] = {}
    for fn, t in data.items():
        if name and fn != name:
            continue
        c = _classify(t)
        by_cls.setdefault(c, []).append((fn, t))

    # keep insertion (file) order within each class -- not byte-ranked.
    # (byte diff is a corpus-progress figure, surfaced only in
    # ``decomp-verify`` / ``progress`` project views, never per function.)

    # summary
    typer.secho("=== triage summary ===", bold=True)
    order = ["tie-reorder REACHABLE", "savings", "inconclusive",
             "no-cascade", "unreachable", "other"]
    for c in order:
        if c not in by_cls:
            continue
        rows = by_cls[c]
        color = {"tie-reorder REACHABLE": "green",
                 "savings": "yellow",
                 "inconclusive": "yellow",
                 "no-cascade": "white",
                 "unreachable": "red",
                 "other": "white"}.get(c, "white")
        typer.secho(
            f"  {len(rows):>4} fns   {c}",
            fg=color, bold=True)

    if summary:
        return

    # detail -- accept short forms (tie-reorder, savings, ...)
    klass_aliases = {
        "tie": "tie-reorder REACHABLE",
        "tie-reorder": "tie-reorder REACHABLE",
        "reachable": "tie-reorder REACHABLE",
        "savings": "savings",
        "unreachable": "unreachable",
        "inconclusive": "inconclusive",
        "no-cascade": "no-cascade",
        "none": "no-cascade",
        "other": "other",
    }
    if klass != "all":
        resolved = klass_aliases.get(klass, klass)
        if resolved not in by_cls:
            typer.secho(
                f"[!] no functions in class {klass!r} (try one of: "
                + ", ".join(sorted(by_cls)) + ")", fg="red")
            return
        classes_to_show = [resolved]
    else:
        classes_to_show = order

    for c in classes_to_show:
        rows = by_cls.get(c, [])
        if not rows:
            continue
        typer.echo()
        color = {"tie-reorder REACHABLE": "green",
                 "savings": "yellow",
                 "inconclusive": "yellow",
                 "unreachable": "red"}.get(c, "white")
        typer.secho(f"=== {c}  ({len(rows)} fn, "
                    f"showing top {min(limit, len(rows))}) ===",
                    bold=True, fg=color)
        for fn, t in rows[:limit]:
            typer.echo(f"  {fn}")
            for line in t["cascade"][:2]:
                # collapse SIDE EFFECTS sub-clause
                short = re.sub(r"\s+SIDE EFFECTS[^.]*\.", "", line)
                short = re.sub(r"\s+CAVEAT:.*$", "", short)
                short = re.sub(r"\s+No downstream re-seats \(strict\)\.",
                               "", short)
                typer.echo(f"       \u2192 {short[:200]}")
        if len(rows) > limit:
            typer.echo(f"  ... and {len(rows) - limit} more")

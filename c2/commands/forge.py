"""``c2 forge`` -- the automatic per-function source-shape solver.

Five commands, converged on the 90% path:

  c2 forge solve [FN|FILE.c ...]   THE default: beam-search each target
                                   with the full lever battery, keep
                                   improvements, record the tree
  c2 forge report [RUN]            list stored runs / inspect one
  c2 forge diff RUN ITEM           reconstruct any tried permutation's
                                   unified diff (offline, no recompile)
  c2 forge exp [SLUG]              authored experiment files (the 10%
                                   investigative path)
  c2 forge levers                  the lever catalogue (docstring-derived)

Authoritative docs / cheatsheet: ``.pi/skills/forge/SKILL.md``
"""

from __future__ import annotations

import importlib.util
import json
import os
import time
from pathlib import Path
from typing import Annotated, List, Optional

import typer


app = typer.Typer(
    help="Automatic source-shape solver (beam search over the lever "
         "battery).  `c2 forge solve <fn>` is the 90% path; read "
         ".pi/skills/forge/SKILL.md for the guide.",
    no_args_is_help=True,
)

_EXPS_DIR = Path("docs/codegen-experiments")


def _worklist_rows() -> list[dict]:
    import subprocess
    out = subprocess.run(
        ["uv", "run", "c2", "worklist", "--json"],
        capture_output=True, text=True, check=True,
    ).stdout
    return json.loads(out)["rows"]


def _verify_records() -> dict[str, dict]:
    """``{fn: record}`` from the verify cache (fix_next + seat_recon).
    Empty on any failure -- the seat oracle then no-ops (full battery)."""
    try:
        d = json.loads(Path(".c2-cache/verify.json").read_text())
        return {r["name"]: r for r in d.get("functions", [])}
    except Exception:                              # noqa: BLE001
        return {}


def _route_profile(fn: str, file: str, vrec: dict | None, *,
                   enabled: bool) -> tuple[tuple[str, ...], dict, bool]:
    """Autonomously pick the lever profile for one target.

    Returns ``(presets, preset_opts, skip)``.  fix_next=seat consults the
    offline seat oracle:

      reorder  -> FOCUSED birth-reorder profile on the named movers.
      bridge   -> FOCUSED register-class flip on the named competing
                  values (reorder pruned).
      skip     -> the seat tie is between anonymous temps (no source
                  handle) -> CERTIFIED residue; don't climb at all.
      fallback -> untrusted / no trace / non-seat -> full battery.

    Every focused profile is restricted to a handful of vars, so the
    singles pool is tens (not hundreds) and the pairs escalation stays
    far under the cap.  Monotone-safe: survivors are byte-verified.
    """
    default = (("all",), {}, False)
    if not enabled or not vrec:
        return default
    if (vrec.get("shape_distance") or {}).get("fix_next") != "seat":
        return default

    # The seat oracle reasons about the CURRENT local set (decl/use-order
    # + width).  The win-census (MSVC /Od) is only an informational HINT
    # here, NOT a router: a survey of known seat closers showed its
    # `de_invent` verdict was empirically UNRELIABLE (2/2 high-Q
    # de_invent verdicts were actually closed by decl-order, not
    # de-invent -- port drift + /Od-frame artifact; see
    # /tmp/survey_out.jsonl).  PS.EXE is the ground truth; win/mac are a
    # different, later source cut.
    try:
        from c2.forge.seat_oracle import census_verdict
        cv = census_verdict(fn)
        if cv.status in ("de_invent", "add_local"):
            typer.echo(f"[solve] {fn}: win-census hint {cv.status} "
                       f"({cv.detail}) -- informational only, not routing",
                       err=True)
    except Exception:                               # noqa: BLE001
        pass

    try:
        from c2.forge.seat_oracle import probe
        v = probe(fn, file, vrec.get("seat_recon"))
    except Exception as exc:                        # noqa: BLE001
        typer.echo(f"[solve] {fn}: seat oracle error ({exc!r}) -- "
                   "full battery", err=True)
        return default
    if v.status == "reorder":
        typer.echo(f"[solve] {fn}: seat oracle REORDER -- focus "
                   f"{v.restrict_vars} ({v.detail})", err=True)
        return (("seat",), {"restrict": v.restrict_vars}, False)
    if v.status == "skip":
        typer.echo(f"[solve] {fn}: seat oracle SKIP -- {v.detail}", err=True)
        return default[:2] + (True,)
    typer.echo(f"[solve] {fn}: seat oracle FALLBACK -- full battery "
               f"({v.detail})", err=True)
    return default


def _resolve_file(function: str) -> str | None:
    """Find the TU defining ``function`` (tree-sitter confirmed)."""
    from c2.forge import cspan
    for p in sorted(Path("decomp/src").glob("*.c")):
        text = p.read_text()
        if function not in text:
            continue
        if cspan.fnspan(text, function) is not None:
            return p.name
    return None


def _resolve_targets(selectors: list[str],
                     status_ok=("workable", "hard", "diagnose", "park"),
                     ) -> list[tuple[str, str]]:
    """Selectors -> [(function, file), ...].

    A selector is a function name or a TU basename (``map.c`` = every
    still-diffing function in that file).  No selectors = the whole
    non-blocked diffing worklist, shape-distance order.
    """
    rows = [r for r in _worklist_rows() if r.get("status") != "blocked"]
    by_fn = {r["name"]: Path(r["file"]).name for r in rows}
    if not selectors:
        rows = [r for r in rows if r.get("status") in status_ok]
        rows.sort(key=lambda r: r.get("shape_total") or 0)
        return [(r["name"], Path(r["file"]).name) for r in rows]
    out: list[tuple[str, str]] = []
    for sel in selectors:
        if sel.endswith(".c"):
            base = Path(sel).name
            hits = [(r["name"], base) for r in rows
                    if Path(r["file"]).name == base]
            if not hits:
                typer.echo(f"[solve] {sel}: no diffing functions", err=True)
            out.extend(hits)
            continue
        file = by_fn.get(sel) or _resolve_file(sel)
        if file is None:
            raise typer.BadParameter(
                f"cannot resolve {sel!r} to a function in decomp/src")
        out.append((sel, file))
    return out


@app.command("solve")
def solve(
    selectors: Annotated[Optional[List[str]], typer.Argument(
        help="Function name(s) and/or TU basename(s) (file.c = every "
             "diffing fn in it).  Omit to run the whole non-blocked "
             "diffing worklist.")] = None,
    jobs: Annotated[int, typer.Option("--jobs", "-j",
        help="Warm-container workers")] = max(4, (os.cpu_count() or 8) - 2),
    rounds: Annotated[int, typer.Option("--rounds",
        help="Max beam rounds per function (a brake; the search "
             "normally ends on stall or byte-exact first.  One lex "
             "edit = one round, so long descents on big functions "
             "need many rounds -- prefer --budget as the real "
             "limit)")] = 48,
    budget: Annotated[float, typer.Option("--budget",
        help="Wall-clock seconds per function (0 = unlimited); the "
             "honest cost knob now that variant caps rarely "
             "bind")] = 0,
    beam: Annotated[int, typer.Option("--beam", "-b",
        help="Beam width: DISTINCT improving states kept per round "
             "(family-diverse branching; 1 = plain greedy)")] = 2,
    policy: Annotated[str, typer.Option("--policy",
        help="'lex' (strict fix-order) or 'lex+weighted' (default: "
             "composite plateau steps; ir/islands may NEVER "
             "regress)")] = "lex+weighted",
    pairs_cap: Annotated[int, typer.Option("--pairs-cap",
        help="Variant cap for the stuck-escalation pairs pass "
             "(~100+/s on a warm pool since the persistent-shell "
             "builder; the cap is a runaway brake, not a budget)")]
        = 25_000,
    max_variants: Annotated[int, typer.Option("--max-variants",
        help="Per-round singles cap")] = 25_000,
    keep: Annotated[bool, typer.Option("--keep/--restore",
        help="Keep lex-improving final states applied to decomp/src "
             "(default) or restore (read-only exploration)")] = True,
    bridge: Annotated[bool, typer.Option("--bridge/--no-bridge",
        help="When the lex ladder wall-locks, let the beam take a "
             "BOUNDED ir/islands/bytes regression that buys a deeper "
             "(seat/spill/width) gain -- hopping into a seat=0 basin. "
             "Never changes the keep bar (net-lex/byte-exact only)")]
        = True,
    max_bridges: Annotated[int, typer.Option("--max-bridges",
        help="Cap on total basin-hop bridge steps per function "
             "(each admission is a DISTINCT (plan,outcome) signature "
             "-- duplicates from neutral-variant states are not "
             "charged)")] = 8,
    bridge_ir: Annotated[Optional[int], typer.Option("--bridge-ir",
        help="Max ir-layer regression a single bridge may pay "
             "(default: adaptive, max(12, ir_total//6) -- scales "
             "with function size)")] = None,
    bridge_isl: Annotated[Optional[int], typer.Option("--bridge-isl",
        help="Max islands-layer regression a single bridge may pay "
             "(default: adaptive, max(16, ir_total//4))")] = None,
    fix_filter: Annotated[Optional[str], typer.Option("--fix-next",
        help="Corpus mode: only functions whose fix_next matches "
             "(ir/width/spill/seat)")] = None,
    seat_oracle: Annotated[bool, typer.Option("--seat-oracle/--no-seat-oracle",
        help="Auto-route fix_next=seat functions to the offline seat "
             "oracle: it predicts (no compile) whether a birth-reorder "
             "flips the diverging register seat, then focuses the decl/"
             "stmt levers on the named vars, or -- when it certifies no "
             "reorder can -- prunes them and goes straight to the bridge "
             "levers. Untrusted/inconclusive falls back to the full "
             "battery. Monotone-safe (every edit is still byte-verified)")]
        = True,
    out: Annotated[Path, typer.Option("--out",
        help="JSON sidecar for corpus runs")] =
        Path(".c2-cache/forge-solve.json"),
) -> None:
    """Beam-search each target with the full lever battery (the 90%
    path -- run it, re-verify the wins, commit).

    Per function: rounds of full-battery singles expand up to --beam
    DISTINCT improving states (branches from different lever families
    are explored in parallel, not just the single best); capped pairs
    + weighted plateau steps break stalls; stop at byte-exact.  Judged
    by the fix-order layer vector decomp-verify prints; only a LEX
    improvement (or byte-exact) is kept.  Every run's search tree +
    all diffs land under .c2-cache/forge-runs/ (`c2 forge report`,
    `c2 forge diff`).  Wins are applied to decomp/src -- re-run
    `c2 decomp-verify -f <fn>` and commit per Hard Rule #2.
    """
    from c2.forge.experiment import climb

    targets = _resolve_targets(selectors or [])
    if fix_filter:
        rows = {r["name"]: r for r in _worklist_rows()}
        targets = [(fn, f) for fn, f in targets
                   if rows.get(fn, {}).get("fix_next") == fix_filter]
    if not targets:
        typer.echo("no targets.")
        raise typer.Exit(0)
    vrecs = _verify_records() if seat_oracle else {}
    single = len(targets) == 1
    typer.echo(f"[solve] {len(targets)} target(s), jobs={jobs}, "
               f"beam={beam}, policy={policy}, "
               f"bridge={'on' if bridge else 'off'}"
               f"{f' (<={max_bridges})' if bridge else ''}", err=True)

    results: list[dict] = []
    t0 = time.perf_counter()
    for i, (fn, file) in enumerate(targets, 1):
        t_fn = time.perf_counter()
        rec: dict = {"fn": fn, "file": file}
        try:
            presets, preset_opts, skip = _route_profile(
                fn, file, vrecs.get(fn), enabled=seat_oracle)
            if skip:
                rec.update({"status": "skipped",
                            "reason": "seat oracle: certified sub-source "
                                      "residue (no source handle)",
                            "elapsed_s": round(time.perf_counter() - t_fn, 1)})
                results.append(rec)
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(json.dumps(results, indent=2))
                typer.echo(f"[{i:>3d}/{len(targets)}] {fn:<34s} "
                           f"\u25cb skipped (certified residue)  "
                           f"({rec['elapsed_s']:.0f}s)", err=True)
                continue
            # focused seat profiles need only a small pairs budget (the
            # oracle already told us WHERE to look); a big cap just wastes
            # compiles on the tiny focused pool.
            eff_pairs_cap = (4000 if presets in (("seat",), ("localset",))
                             else pairs_cap)
            rep = climb(fn, file=file, jobs=jobs, max_rounds=rounds,
                        beam=beam, policy=policy, pairs_cap=eff_pairs_cap,
                        max_variants=max_variants, keep=keep,
                        budget=budget or None, quiet=not single,
                        presets=presets, preset_opts=preset_opts,
                        bridge=bridge, max_bridges=max_bridges,
                        bridge_ir_budget=bridge_ir,
                        bridge_isl_budget=bridge_isl)
            rec.update({
                "status": ("byte-exact" if rep["byte_exact"]
                           else "improved" if rep["improved"]
                           else "neutral"),
                "start": rep["start"], "final": rep["final"],
                "rounds": rep["rounds"], "steps": rep["steps"],
                "evaluated": rep.get("evaluated"),
                "rate": rep.get("rate"),
                "run_dir": rep["run_dir"],
                "applied": not rep["restored"],
                "elapsed_s": round(time.perf_counter() - t_fn, 1),
            })
        except Exception as exc:                  # noqa: BLE001
            rec.update({"status": "error", "error": str(exc)[:300],
                        "elapsed_s": round(time.perf_counter() - t_fn, 1)})
        results.append(rec)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(results, indent=2))
        tag = {"byte-exact": "✓ BYTE-EXACT", "improved": "▲ improved",
               "neutral": "· neutral", "error": "! error"}[rec["status"]]
        detail = ""
        if rec.get("final") and rec.get("start"):
            s, f = rec["start"], rec["final"]
            detail = (f"  ir{s['layers'][0]}→{f['layers'][0]} "
                      f"b{s['bytes']}→{f['bytes']}")
        typer.echo(f"[{i:>3d}/{len(targets)}] {fn:<34s} {tag}{detail}  "
                   f"({rec['elapsed_s']:.0f}s)", err=True)

    n_exact = sum(1 for r in results if r["status"] == "byte-exact")
    n_imp = sum(1 for r in results if r["status"] == "improved")
    typer.echo(
        f"\n[solve] done in {time.perf_counter() - t0:.0f}s: "
        f"{n_exact} byte-exact, {n_imp} improved, "
        f"{len(results) - n_exact - n_imp} neutral/error "
        f"-> {out}", err=True)
    if (n_exact or n_imp) and keep:
        typer.echo(
            "[solve] wins are applied in decomp/src -- re-verify with "
            "`c2 decomp-verify -f <fn>` and commit (Hard Rule #2).",
            err=True)
    elif (n_exact or n_imp) and not keep:
        typer.echo(
            "[solve] --restore: improvements NOT applied -- diffs via "
            "`c2 forge report <fn>` / `c2 forge diff <fn> <node>`.",
            err=True)
    raise typer.Exit(0 if (n_exact or n_imp or not results) else 1)


@app.command("report")
def report_cmd(
    run: Annotated[Optional[str], typer.Argument(
        help="Run selector: function name (latest run), fn/ts-kind id, "
             "or run dir.  Omit to list all stored runs.")] = None,
    top: Annotated[int, typer.Option("--top", "-n",
        help="Winners/branches to show")] = 12,
) -> None:
    """List stored runs, or summarise one: winners, pareto front, and
    the full search tree (every branch taken or logged)."""
    from c2.forge import runstore as rs
    if run is None:
        runs = rs.list_runs()
        if not runs:
            typer.echo("(no stored runs)")
            return
        typer.echo(f"{'run':<46s} {'kind':<6s} {'status':<11s} "
                   f"{'baseline':<18s} final")
        typer.echo("-" * 100)
        for m in runs[:40]:
            d = Path(m["dir"])
            rid = f"{d.parent.name}/{d.name}"
            summ = m.get("summary") or {}
            base = m.get("baseline") or {}
            base_s = (f"ir{base['layers'][0]} i{base['layers'][1]} "
                      f"b{base['bytes']}" if base.get("layers") else "?")
            fin = summ.get("final") or {}
            fin_s = (f"ir{fin['layers'][0]} i{fin['layers'][1]} "
                     f"b{fin['bytes']}" if fin.get("layers") else "-")
            typer.echo(f"{rid:<46s} {m.get('kind', '?'):<6s} "
                       f"{summ.get('status', '(open)'):<11s} "
                       f"{base_s:<18s} {fin_s}")
        return

    from c2.forge.matrix import pareto_front
    d = rs.resolve(run)
    meta = rs.load_meta(d)
    base = meta.get("baseline") or {}
    summ = meta.get("summary") or {}
    typer.echo(f"run:      {d}")
    typer.echo(f"function: {meta.get('function')}  ({meta.get('file')})  "
               f"kind={meta.get('kind')}  git={meta.get('git_head')}")
    typer.echo(f"config:   {json.dumps(meta.get('config', {}))}")
    typer.echo(f"baseline: layers={base.get('layers')}  "
               f"bytes={base.get('bytes')}")
    _skip = {"status", "bridge_overbudget"}
    typer.echo(f"status:   {summ.get('status', '(open)')}  "
               + " ".join(f"{k}={v}" for k, v in summ.items()
                          if k not in _skip))

    ob = summ.get("bridge_overbudget") or []
    if ob:
        typer.echo(f"\ndeep-gain paths OVER the bridge budget "
                   f"({len(ob)} shown; rerun `c2 forge solve` with a wider "
                   f"--bridge-ir/--bridge-isl to explore):")
        for r in ob:
            pl = r["layers"]
            typer.echo(f"  {r['plan']:<40s} ir{pl[0]} i{pl[1]} w{pl[2]} "
                       f"sp{pl[3]} st{pl[4]} b{r['bytes']}  "
                       f"needs --bridge-ir>={r['need_ir']} "
                       f"--bridge-isl>={r['need_isl']}")

    tree = rs.load_tree(d)
    if tree:
        typer.echo("\nsearch tree (accepted states ★, logged children ·):")
        by_parent: dict = {}
        for rec in tree:
            by_parent.setdefault(rec.get("parent"), []).append(rec)

        def _walk(pid, depth):
            for rec in by_parent.get(pid, []):
                mark = "★" if rec.get("accepted") else "·"
                lay = rec.get("layers")
                lay_s = (f"ir{lay[0]} i{lay[1]} w{lay[2]} sp{lay[3]} "
                         f"st{lay[4]}" if lay else "?")
                plan = rec.get("plan", "(baseline)")
                if len(plan) > 46:
                    plan = plan[:43] + "..."
                typer.echo(f"  {'  ' * depth}{mark} {rec['id']:<6s} "
                           f"r{rec.get('round', 0)} "
                           f"[{lay_s} b{rec.get('bytes', '?')}] "
                           f"{rec.get('reason', ''):<10s} {plan}")
                if rec.get("accepted"):
                    _walk(rec["id"], depth + 1)
        _walk(None, 0)
        typer.echo(f"\n  diff any node:  c2 forge diff "
                   f"{meta.get('function')} <id>   (--step = vs parent)")

    results = list(rs.iter_results(d))
    if results:
        ok = [r for r in results if r.get("ok")]

        class _R:                            # shim for pareto_front
            def __init__(self, rec):
                self.rec = rec

        front = pareto_front(
            [_R(r) for r in ok],
            vector=lambda it: tuple(it.rec["layers"]) + (it.rec["bytes"],))
        improving = sorted(
            (r for r in ok
             if (tuple(r["layers"]), r["bytes"])
             < (tuple(base.get("layers", [9e9] * 5)),
                base.get("bytes", 0))),
            key=lambda r: (tuple(r["layers"]), r["bytes"]))
        typer.echo(f"\n{len(results)} plan(s) scored, "
                   f"{len(improving)} improving, "
                   f"pareto front {len(front)}:")
        for r in improving[:top]:
            lay = r["layers"]
            typer.echo(f"  {r['id']}  ir{lay[0]} i{lay[1]} w{lay[2]} "
                       f"sp{lay[3]} st{lay[4]} b{r['bytes']}  {r['plan']}")
        if improving:
            typer.echo(f"\n  reconstruct any: c2 forge diff "
                       f"{meta.get('function')} <plan-id>")


@app.command("diff")
def diff_cmd(
    run: Annotated[str, typer.Argument(
        help="Run selector (function name = latest run, or run id)")],
    item: Annotated[str, typer.Argument(
        help="Plan id (results) or node id (climb tree); prefixes ok")],
    step: Annotated[bool, typer.Option("--step",
        help="Diff vs the item's parent state instead of the run "
             "baseline")] = False,
    context: Annotated[int, typer.Option("--context", "-c")] = 3,
) -> None:
    """Reconstruct + print the unified diff of ANY tried permutation or
    tree node -- offline, from the stored edits; nothing recompiles."""
    from c2.forge import runstore as rs
    d = rs.resolve(run)
    typer.echo(rs.diff_for(d, item, context=context,
                           against_baseline=not step))


@app.command("exp")
def exp_cmd(
    slug: Annotated[Optional[str], typer.Argument(
        help="Experiment slug under docs/codegen-experiments/. "
             "Omit to list.")] = None,
    depth: Annotated[int, typer.Option("--depth", "-d",
        help="Cartesian depth (1=singles, 2=pairs, ...)")] = 1,
    jobs: Annotated[int, typer.Option("--jobs", "-j")] = 8,
    max_variants: Annotated[int, typer.Option("--max-variants")] = 5000,
    top: Annotated[int, typer.Option("--top", "-n")] = 10,
    dry_run: Annotated[bool, typer.Option("--dry-run",
        help="Enumerate plans without compiling (search-space size "
             "check)")] = False,
    apply: Annotated[bool, typer.Option("--apply",
        help="Apply the best winning plan to decomp/src")] = False,
    new: Annotated[bool, typer.Option("--new",
        help="Scaffold a new experiment file (needs --fn and --file)")]
        = False,
    fn: Annotated[Optional[str], typer.Option("--fn",
        help="Target function (with --new)")] = None,
    file: Annotated[Optional[str], typer.Option("--file",
        help="Source TU basename (with --new)")] = None,
    store: Annotated[bool, typer.Option("--store/--no-store")] = True,
) -> None:
    """Run an authored experiment file (targeted hypotheses / probes --
    the investigative 10%; `c2 forge solve` is the default path).

    Every scored plan's edits + judges are stored so any permutation's
    diff is reconstructable later via `c2 forge diff`.
    """
    from c2.forge import Forge

    if new:
        if not slug or not fn or not file:
            raise typer.BadParameter("--new needs SLUG, --fn and --file")
        path = _EXPS_DIR / f"{slug}.py"
        if path.exists():
            raise typer.BadParameter(f"{path} already exists")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            f'"""{slug}: forge experiment on {fn} ({file}).\n\n'
            f'See .pi/skills/forge/SKILL.md for the DSL surface.\n"""\n\n'
            f'from c2.forge import Forge\n\n'
            f'forge = Forge("{fn}", file="{file}")\n\n'
            f'forge.preset("all")\n'
            f'# forge.swap_decls("a", "b")\n'
            f'# forge.commute_at(line=42)\n'
            f'# forge.try_type("count", ["short", "unsigned short"])\n'
            f"\n# run: c2 forge exp {slug} --depth 2 --jobs $(nproc)\n")
        typer.echo(f"created {path}")
        return

    if slug is None:
        found = sorted(p.stem for p in _EXPS_DIR.glob("*.py")
                       if not p.stem.startswith("_")) \
            if _EXPS_DIR.exists() else []
        typer.echo("\n".join(f"  {s}" for s in found) or "(no experiments)")
        return

    mod_path = _EXPS_DIR / f"{slug}.py"
    if not mod_path.exists():
        raise typer.BadParameter(f"no experiment at {mod_path}")
    spec = importlib.util.spec_from_file_location(f"forge_{slug}", mod_path)
    if spec is None or spec.loader is None:
        raise typer.BadParameter(f"cannot import {mod_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    forge = getattr(mod, "forge", None)
    if not isinstance(forge, Forge):
        raise typer.BadParameter(
            f"{mod_path} must define a module-level `forge = Forge(...)`")

    if dry_run:
        typer.echo(json.dumps(
            forge.dry_run(mode=depth, max_variants=max_variants), indent=2))
        return

    run_store = None
    if store:
        from c2.forge import runstore as rs
        run_store = rs.RunStore.create(
            forge.function, forge.file, "exp", forge.text,
            config={"slug": slug, "depth": depth,
                    "max_variants": max_variants})
    summary = forge.run(mode=depth, jobs=jobs, max_variants=max_variants,
                        store=run_store)
    summary.show(top=top)
    best = summary.best()
    if run_store is not None:
        winners = summary.winners()
        winners.sort(key=lambda p: (p.score.layers, p.score.bytes))
        for i, pr in enumerate(winners[:5], 1):
            run_store.write_winner(i, pr.plan, pr.score,
                                   forge.text, forge.file)
        run_store.finalize(
            status=("byte-exact" if best and best.score.bytes == 0
                    else "winner" if best else "neutral"),
            plans=len(summary.plans), winners=len(winners),
            pareto=len(summary.pareto()))
        typer.echo(f"\nartifacts: {run_store.dir}\n"
                   f"  any permutation's diff: c2 forge diff "
                   f"{forge.function} <plan-id>")
    if apply and best is not None:
        forge.apply(best.plan)
        typer.echo(f"\napplied: {best.plan.name}\n  -> {forge._file_path}")


@app.command("levers")
def levers_cmd() -> None:
    """The lever catalogue (descriptions straight from the preset
    docstrings -- cannot drift from the implementation)."""
    from c2.forge import PRESETS
    typer.echo(f"{'preset':<26s}  description")
    typer.echo("-" * 96)
    seen: set[int] = set()
    for name, fn in PRESETS.items():
        doc = " ".join((fn.__doc__ or "").strip()
                       .split("\n\n")[0].split())
        alias = "(alias) " if id(fn) in seen else ""
        seen.add(id(fn))
        if len(doc) > 64:
            doc = doc[:61] + "..."
        typer.echo(f"  {name:<24s}  {alias}{doc}")


# Convenience CLI entry the parent app wires up under name="forge".
forge_app = app

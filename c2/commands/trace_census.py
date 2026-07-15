"""Corpus-wide grounding census over the persisted build trace.

Every new trace observable MUST be grounded against the WHOLE corpus before
its hint is trusted -- the two 2026-06-11 misfires (PS-alloc tie
misattribution on font_format_split, given_regs drift false positives on
sa12_army_sail_home/build_region_item) were both sample-validated tools that
broke on the first untested member.

This command is OFFLINE AND FAST: it reads the persisted per-function build
trace (`.c2-cache/build/regtrace.json`, captured as a side effect of the
normal decomp-verify build -- no extra compiles) and computes:

  * cache freshness  -- schema version + function count; a stale/partial
    cache is the FIRST thing to fix (run a full rebuild: `touch decomp/src/
    *.c` then any `c2 decomp-verify <file>` repopulates every TU's entry).
  * given_regs drift census (stream-level) -- every function where the bt
    ground truth disagrees with union-of-earlier-picks = order-reasoning-
    unreliable; expected RARE.  A high count means the CHECK is wrong, not
    the corpus.
  * comtail/retlists field grounding -- distribution of cm.save and the
    cm.raw20 field values across all routines.  This census is what proved
    the field initially labelled `ins_line` is actually a repeated-constant
    oc_entry header word (0x100/0x201/0x600/...), NOT a source line.
  * alloc/given_regs coverage -- how many functions carry each observable,
    so a consumer knows when absence-of-signal means absence-of-data.

Cross-references `.c2-cache/verify.json` (when present) to split stats by
exact-vs-diff functions.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import typer

_TRACE_CACHE = Path(".c2-cache/build/regtrace.json")
_VERIFY_CACHE = Path(".c2-cache/verify.json")


def _load(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def trace_census(
    json_out: bool = typer.Option(False, "--json", help="machine-readable output"),
) -> None:
    """Ground the trace observables corpus-wide from the CACHED build trace
    (offline; no compiles).  Run after any trace-schema change."""
    from c2.regalloc import _CACHE_VERSION
    from c2.commands.regtrace import given_regs_drift

    data = _load(_TRACE_CACHE)
    if not data:
        typer.secho(f"[!] no persisted build trace at {_TRACE_CACHE} -- run any "
                    "`c2 decomp-verify <file>` (trace image) first.", fg="red")
        raise typer.Exit(1)
    by_func = data.get("by_func", {})
    stale = data.get("v") != _CACHE_VERSION

    res: dict = {
        "cache_version": data.get("v"),
        "expected_version": _CACHE_VERSION,
        "stale": stale,
        "functions": len(by_func),
        "with_alloc": 0,
        "with_given_regs": 0,
        "with_comtail": 0,
        "with_retlists": 0,
        "drift": {},            # fn -> drift lines
        "comtail_save_hist": Counter(),
        "comtail_raw20_hist": Counter(),
        "retlist_len_hist": Counter(),
        # oc_events corpus view (>= v20 caches; per-TU summaries)
        "oc_files": 0,
        "oc_tags": Counter(),
        "oc_op_cls": Counter(),
        "oc_em_cls": Counter(),
        "oc_fw_save": Counter(),
        "oc_ct_save": Counter(),
        "oc_em_bytes": 0,
        "oc_nj_ct_mismatch": [],     # files violating nj == ct
        "oc_drain_violations": [],   # files where first fq <= last op
    }

    for fname, s in (data.get("oc_census") or {}).items():
        res["oc_files"] += 1
        res["oc_tags"].update(s.get("tags", {}))
        res["oc_op_cls"].update(s.get("op_cls", {}))
        res["oc_em_cls"].update(s.get("em_cls", {}))
        res["oc_fw_save"].update(s.get("fw_save", {}))
        res["oc_ct_save"].update(s.get("ct_save", {}))
        res["oc_em_bytes"] += s.get("em_bytes", 0)
        t = s.get("tags", {})
        if t.get("nj", 0) != t.get("ct", 0):
            res["oc_nj_ct_mismatch"].append(fname)
        if s.get("drain_after_push") is False:
            res["oc_drain_violations"].append(fname)

    for fn, r in by_func.items():
        alloc = r.get("alloc") or []
        if alloc:
            res["with_alloc"] += 1
        if any(a.get("given_regs") for a in alloc):
            res["with_given_regs"] += 1
            stream = [{"order": i, "var": a.get("var"),
                       "chosen": a.get("reg_name"),
                       "given_regs": a.get("given_regs", 0)}
                      for i, a in enumerate(alloc)]
            d = given_regs_drift(stream)
            if d:
                res["drift"][fn] = d
        ct = r.get("comtail") or []
        if ct:
            res["with_comtail"] += 1
            for e in ct:
                res["comtail_save_hist"][e["save"]] += 1
                res["comtail_raw20_hist"][e["raw20"]] += 1
        rl = r.get("retlists") or []
        if rl:
            res["with_retlists"] += 1
            for n in rl:
                res["retlist_len_hist"][n] += 1

    if json_out:
        out = dict(res)
        for k in ("comtail_save_hist", "comtail_raw20_hist",
                  "retlist_len_hist", "oc_tags", "oc_op_cls", "oc_em_cls",
                  "oc_fw_save", "oc_ct_save"):
            out[k] = dict(res[k])
        typer.echo(json.dumps(out, indent=2))
        return

    typer.secho("=== trace census (offline, cached build trace) ===",
                fg="green", bold=True)
    ver = res["cache_version"]
    if stale:
        typer.secho(f"  [!] cache schema v{ver} != expected v{res['expected_version']}"
                    " -- STALE: refresh with `touch decomp/src/*.c` + any "
                    "`c2 decomp-verify <file>` (one full build), then re-run.",
                    fg="red", bold=True)
    typer.echo(f"  functions: {res['functions']}   with_alloc: {res['with_alloc']}"
               f"   given_regs: {res['with_given_regs']}"
               f"   comtail: {res['with_comtail']}   retlists: {res['with_retlists']}")

    typer.secho(f"\n  given_regs drift (stream-level): {len(res['drift'])} "
                "function(s)", bold=True)
    for fn, lines in sorted(res["drift"].items())[:20]:
        typer.secho(f"    {fn}:", fg="yellow")
        for ln in lines[:-1]:
            typer.echo("    " + ln)
    if len(res["drift"]) > 20:
        typer.echo(f"    ... {len(res['drift']) - 20} more")
    if res["with_given_regs"] and not res["drift"]:
        typer.echo("    (clean corpus-wide -- union-of-earlier-picks model "
                   "EXACT on every function with bt data)")

    if res["with_comtail"]:
        typer.secho("\n  comtail (cm) save distribution:", bold=True)
        for save, n in sorted(res["comtail_save_hist"].items())[:15]:
            typer.echo(f"    save={save:<5} x{n}")
        typer.secho("  comtail (cm) raw20-field top values (GROUNDED: an "
                    "oc_entry header word, NOT a source line -- see "
                    "trace.py cm comment):", bold=True)
        for w, n in res["comtail_raw20_hist"].most_common(10):
            typer.echo(f"    raw20={w:#06x} x{n}")
        typer.secho("  retlist length distribution:", bold=True)
        for ln_, n in sorted(res["retlist_len_hist"].items())[:12]:
            typer.echo(f"    len={ln_:<4} x{n}")
    else:
        typer.echo("\n  (no rl/cm comtail data in cache -- retired records; "
                   "the fw stream in oc_census supersedes them)")

    if res["oc_files"]:
        typer.secho(f"\n  OC-queue merge stream ({res['oc_files']} TU "
                    "summaries):", bold=True)
        typer.echo("    tag totals: " + "  ".join(
            f"{t}:{n}" for t, n in res["oc_tags"].most_common()))
        typer.echo("    op class hist: " + "  ".join(
            f"{c}:{n}" for c, n in sorted(res["oc_op_cls"].items(),
                                          key=lambda kv: int(kv[0]))))
        typer.echo("    em class hist: " + "  ".join(
            f"{c}:{n}" for c, n in sorted(res["oc_em_cls"].items(),
                                          key=lambda kv: int(kv[0]))))
        typer.echo("    fw save hist (capped 64): " + "  ".join(
            f"{s}:{n}" for s, n in sorted(res["oc_fw_save"].items(),
                                          key=lambda kv: int(kv[0]))[:16]))
        typer.echo("    ct save hist: " + "  ".join(
            f"{s}:{n}" for s, n in sorted(res["oc_ct_save"].items(),
                                          key=lambda kv: int(kv[0]))[:16]))
        typer.echo(f"    em bytes total: {res['oc_em_bytes']}")
        ok1 = not res["oc_nj_ct_mismatch"]
        ok2 = not res["oc_drain_violations"]
        typer.secho(f"    invariant nj==ct: "
                    f"{'OK' if ok1 else 'VIOLATED: ' + ', '.join(res['oc_nj_ct_mismatch'][:5])}",
                    fg="green" if ok1 else "red")
        typer.secho(f"    invariant first-fq>last-op (drain-after-push): "
                    f"{'OK' if ok2 else 'VIOLATED: ' + ', '.join(res['oc_drain_violations'][:5])}",
                    fg="green" if ok2 else "red")
    else:
        typer.echo("\n  (no oc_census in cache -- refresh with a v20+ full "
                   "build: `touch decomp/src/*.c` + `c2 decomp-verify <file>`)")

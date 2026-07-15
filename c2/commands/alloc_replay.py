"""`c2 alloc-replay` -- offline allocator replay & lever what-ifs.

Validates the corpus-certified replay (SortConflicts ShellSort per retry
round + the GiveBestReg selection rule) against a routine's trace ground
truth, and answers birth-order what-ifs without compiling.

Usage:
    c2 alloc-replay --census                 # corpus validation numbers
    c2 alloc-replay flag_range               # one routine, both halves
    c2 alloc-replay get_ptr_to_corner --swap 5,7
                                             # what-if: swap two presort
                                             # slots, show queue delta
"""
from __future__ import annotations

import json
from pathlib import Path

import typer

_TRACE_CACHE = Path(".c2-cache/build/regtrace.json")


def _load() -> dict:
    if not _TRACE_CACHE.exists():
        typer.secho(f"[!] no build trace at {_TRACE_CACHE} -- run a "
                    "decomp-verify with the trace image first", fg="red")
        raise typer.Exit(1)
    return json.loads(_TRACE_CACHE.read_text())


def alloc_replay(
    name: str = typer.Argument(None, help="function name"),
    census: bool = typer.Option(False, "--census",
                                help="validate corpus-wide and exit"),
    swap: str = typer.Option(None, "--swap",
                             help="what-if: swap presort slots I,J and "
                                  "show the queue delta"),
    move: str = typer.Option(None, "--move",
                             help="CASCADE what-if: move alloc row I to "
                                  "position J and replay every pick "
                                  "(masks/given evolve; trusted only if "
                                  "the identity gate is exact)"),
    want: str = typer.Option(None, "--want",
                             help="INVERSE search: 'var=REG,var2=REG2' "
                                  "(PS's seats); enumerate all single "
                                  "moves + pair swaps of the allocation "
                                  "order and report which reproduce the "
                                  "target, annotated by lever class "
                                  "(tie-break vs savings change)"),
) -> None:
    """Replay the allocator offline; validate or run a what-if."""
    from c2.regalloc import replay

    data = _load()
    by_func = data.get("by_func", {})

    if census:
        s_tot = s_ok = p_tot = p_ok = 0
        bad_sort, bad_pick = [], []
        for fn, r in by_func.items():
            v = replay.validate_routine(r)
            if v["sort_ok"] is not None:
                s_tot += 1
                if v["sort_ok"]:
                    s_ok += 1
                else:
                    bad_sort.append(fn)
            p_tot += v["picks_total"]
            p_ok += v["picks_ok"]
            if v["pick_misses"]:
                bad_pick.append((fn, len(v["pick_misses"])))
        typer.secho(f"sort:  {s_ok}/{s_tot} routines exact", fg="green"
                    if s_ok == s_tot else "yellow")
        typer.secho(f"picks: {p_ok}/{p_tot} allocations exact", fg="green"
                    if p_ok == p_tot else "yellow")
        for fn in bad_sort[:10]:
            typer.echo(f"  sort mismatch: {fn}")
        for fn, n in bad_pick[:10]:
            typer.echo(f"  pick mismatch: {fn} ({n})")
        return

    if not name:
        typer.secho("name or --census required", fg="red")
        raise typer.Exit(1)
    r = by_func.get(name) or by_func.get(name.rstrip("_"))
    if not r:
        typer.secho(f"[!] {name!r} not in build trace", fg="red")
        raise typer.Exit(1)

    v = replay.validate_routine(r)
    rows = replay.replay_rows(r.get("alloc") or [])
    ident = replay.replay_order(rows, list(range(len(rows))))
    gate = all(x["pick"] == x["identity"] for x in ident)
    typer.secho(f"# {name}: sort_ok={v['sort_ok']} "
                f"(rounds={v['sort_rounds']})  "
                f"picks {v['picks_ok']}/{v['picks_total']}  "
                f"cascade-gate={'EXACT' if gate else 'LEAKY (do not trust what-ifs)'}",
                fg="cyan", bold=True)
    for m in v["pick_misses"]:
        typer.echo(f"  pick miss: {m}")

    if want:
        import itertools
        targets = dict(kv.split("=") for kv in want.split(","))
        graph = replay.build_graph(rows)
        n = len(rows)
        ident_map = {x["idx"]: x["identity"] for x in ident}
        wanted = dict(ident_map)
        named = {("%s" % (a.get("var"),)): i for i, a in enumerate(rows)}
        for v, reg in targets.items():
            if v not in named:
                typer.secho(f"[!] no alloc row named {v!r} "
                            f"(have: {sorted(k for k in named if k != 'None')})",
                            fg="red")
                raise typer.Exit(1)
            wanted[named[v]] = reg.upper()
        cands = []
        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                order = list(range(n))
                order.insert(j, order.pop(i))
                cands.append(("move", i, j, order))
        for i, j in itertools.combinations(range(n), 2):
            order = list(range(n))
            order[i], order[j] = order[j], order[i]
            cands.append(("swap", i, j, order))
        hits = []
        for kind, i, j, order in cands:
            res = {x["idx"]: x["pick"]
                   for x in replay.replay_order(rows, order, graph)}
            if res == wanted:
                si, sj = rows[i].get("savings"), rows[j].get("savings")
                lever = ("tie-break (same savings -- Rule 28a/115 birth "
                         "reorder)" if si == sj else
                         f"SAVINGS change needed ({si} vs {sj} -- source "
                         "shape, not decl order)")
                hits.append((kind, i, j, lever))
        typer.secho(f"-- inverse search: {len(cands)} what-ifs, "
                    f"{len(hits)} reproduce the target --", bold=True)
        for kind, i, j, lever in hits[:12]:
            a, b = rows[i], rows[j]
            typer.echo(f"  {kind} [{i}]{a.get('var') or a['name']} -> "
                       f"[{j}]{b.get('var') or b['name']}: {lever}")
        if not hits:
            typer.echo("  (no single-move/pair-swap order reproduces the "
                       "target -- the lever is outside pure allocation "
                       "order: savings, candidate masks, or ranges)")
        if not gate:
            typer.secho("  [UNTRUSTED: identity gate leaky for this "
                        "routine]", fg="yellow")
        return

    if move:
        i, j = (int(x) for x in move.split(","))
        order = list(range(len(rows)))
        order.insert(j, order.pop(i))
        what = replay.replay_order(rows, order)
        typer.secho(f"-- cascade what-if: alloc row {i} -> position {j} --",
                    bold=True)
        by_idx = {x["idx"]: x for x in what}
        changed = 0
        for k in range(len(rows)):
            x = by_idx[k]
            d = "" if x["pick"] == x["identity"] else \
                f"   {x['identity']} -> {x['pick']}" + \
                ("" if x["confident"] else "  (LOW CONFIDENCE)")
            if d:
                changed += 1
                typer.echo(f"  [{k:>2}] {x['var']:>14}{d}")
        typer.echo(f"  {changed} pick(s) change" +
                   ("" if gate else "  [UNTRUSTED: identity gate leaky]"))
        return

    pres = r.get("presort") or []
    rounds = replay.split_rounds(pres)
    if swap:
        i, j = (int(x) for x in swap.split(","))
        base = replay.replay_sort(rounds[0])
        what = replay.whatif_swap(rounds[0], i, j)
        typer.secho(f"-- what-if: swap presort[{i}] <-> presort[{j}] "
                    f"(round 1) --", bold=True)
        moved = 0
        for k, (a, b) in enumerate(zip(base, what)):
            mark = "" if a["node"] == b["node"] else "   <- MOVED"
            if mark:
                moved += 1
            typer.echo(f"  q[{k:>2}] {a['node']}/{a['savings']:<6} -> "
                       f"{b['node']}/{b['savings']:<6}{mark}")
        typer.echo(f"  {moved} queue slot(s) move; allocations re-seat "
                   "downstream of the first moved slot (re-verify those "
                   "picks' withregs/scores still apply before trusting)")
    else:
        typer.secho(f"-- presort round 1 ({len(rounds[0])} entries; index "
                    "for --swap) --", bold=True)
        queue = replay.replay_sort(rounds[0])
        pos = {x["node"]: k for k, x in enumerate(queue)}
        for k, p in enumerate(rounds[0]):
            typer.echo(f"  sl[{k:>2}] {p['node']}/{p['savings']:<6} "
                       f"-> q[{pos.get(p['node'], '?')}]")

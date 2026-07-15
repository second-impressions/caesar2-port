"""``c2 tempbirths`` -- the attributed Names[N_TEMP] table for one function.

THE drill-in for the Rule 107 slot-swap class now that the whole slot chain
is modeled and corpus-validated (see ``c2/regalloc/shellsort_sim_slots.py``
``validate_routine_chain`` and ``docs/slot-swap-survey-2026-06-25.md``,
2026-07-10 addendum):

    source -> AllocName births -> Names[N_TEMP] (= reversed births)
           -> BuildNameConflicts sort -> AssignTemps sort -> [esp+N] slots

Every nt_pre entry is printed with its var (if named), size, usage bits,
FE line, and the CREATING PASS (``nbc``/``nbo`` probe attribution:
BGNewTemp / FlowOut / CondConstStores2Bool / BurnCopyToTemp / ...), plus
the simulator's single-perturbation flip search against PS's slot order
when it is derivable from the current diff.

Requires the >= 2026-07-10 trace image (auto-used; stale caches
re-trace on demand).
"""

from __future__ import annotations

from pathlib import Path

import typer


def tempbirths(
    function: str = typer.Argument(..., help="function name"),
    file: str = typer.Option(None, "--file", help="TU basename (default: located via the AST index)"),
    json_out: bool = typer.Option(False, "--json", help="machine-readable output"),
):
    """Attributed Names[N_TEMP] creation table (Rule 107 drill-in)."""
    import json as _json

    import c2.regalloc as regalloc
    from c2.regalloc.tempbirth import attribute_births, birth_label, creator_note
    from c2.commands.regtrace import _find_function

    cfile, _, _, _ = _find_function(function, file)
    td = regalloc.file_trace(Path(cfile), Path("decomp/include"))
    rt = (td.get("by_func") or {}).get(function)
    if rt is None:
        typer.echo(f"{function} not in {cfile}'s trace")
        raise typer.Exit(1)

    nt = rt.get("nt_pre") or []
    alloc = {a["name"]: a for a in rt.get("alloc") or []}
    attrib = attribute_births(rt)
    if not attrib:
        typer.echo("no birth attribution in this trace -- image predates the "
                   "nb/nbc/nbo probes (2026-07-10); re-trace with the current "
                   "image (c2 cache clear trace or wait for auto-invalidation)")
    rows = []
    for i, e in enumerate(nt):
        a = alloc.get(e["name"], {})
        rows.append({
            "nt": i, "size": e["size"], "usage": e["usage"],
            "var": a.get("var"), "defline": a.get("defline"),
            "birth": birth_label(e["name"], attrib),
        })
    if json_out:
        typer.echo(_json.dumps({"fn": function, "file": str(cfile),
                                "rows": rows}, indent=1))
        return
    typer.echo(f"{function} ({cfile}) -- Names[N_TEMP] at AssignTemps entry, "
               f"{len(nt)} temps (nt order = REVERSED creation; slots come "
               f"from the two downstream ShellSorts)")
    seen_passes = {}
    for r in rows:
        v = r["var"] or "-"
        dl = f"L{r['defline']}" if r.get("defline") else ""
        typer.echo(f"  nt[{r['nt']:3d}] sz{r['size']} u{r['usage']:<3d} "
                   f"{v:14s}{dl:7s} \u2190 {r['birth']}")
        p = r["birth"].split()[0]
        if not p.startswith(("burn", "?", "pass@")):
            seen_passes[p] = creator_note(p)
    if seen_passes:
        typer.echo("\n  creator passes seen:")
        for p, note in sorted(seen_passes.items()):
            if note:
                typer.echo(f"    {p}: {note}")
    typer.echo(
        "\n  levers: an INSERT in a window = ADD a construct that births a "
        "temp there (bool-valued expr -> FlowOut; if/else const stores "
        "differing by 1 -> CondConstStores2Bool); a REMOVAL = fold/inline "
        "the attributed construct.  The `Slot-swap:` hint in decomp-verify "
        "-v runs the flip search against PS's order automatically."
    )

    # ---- name DEATHS (nf records, image >= 2026-07-10j) ---------------
    # The chronological nb/nf join: names born class-2 that die BEFORE
    # AssignTemps were CULLED (the reason byte-neutral insert candidates
    # -- coalesced copies, dead stores -- keep vanishing).  The caller RA
    # names the killing pass.
    nf = rt.get("nf") or []
    if nf:
        from c2.regalloc.tempbirth import resolve_wcc_base, _symbolize
        nb = rt.get("nb") or []
        base = resolve_wcc_base(nb)
        ev = sorted([(r["seq"], "nb", r) for r in nb if "seq" in r] +
                    [(r["seq"], "nf", r) for r in nf if "seq" in r])
        open_b: dict = {}
        culled = []
        teardown = 0
        for _s, kind, r in ev:
            if kind == "nb":
                open_b[r["name"]] = r
            else:
                b = open_b.pop(r["name"], None)
                if b is None or b.get("class") != 2:
                    continue
                kva = (int(r["caller"], 16) - base) if (base and r.get("caller")) else None
                if kva == 0x3a241:      # FreeNames all-class teardown (routine end)
                    teardown += 1
                    continue
                culled.append((b, kva))
        if culled:
            typer.echo(f"\n  culled before AssignTemps ({len(culled)}; +{teardown} routine-end teardown):")
            for b, kva in culled:
                killer = _symbolize(kva) if kva is not None else "?"
                if killer.startswith("pass@") and kva is not None:
                    killer = {0x5862f: "pre-RegAlloc useless-name sweep"}.get(kva, killer)
                ln = f"L{b.get('line')}" if b.get("line") else ""
                # NOTE: attribute_births keys by ptr LAST birth (recycling), so
                # label the culled name from ITS OWN nb record, not attrib.
                pc = b.get("pass_caller") or b.get("caller")
                lbl = _symbolize(int(pc, 16) - base) if (base and pc) else "?"
                typer.echo(f"    {b['name']} {ln:7s} born←{lbl}  killed←{killer}")
            typer.echo("    (a byte-neutral INSERT candidate must SURVIVE this cull: "
                       "it needs a reference some useful instruction still holds at "
                       "the sweep -- coalesced `t = x;` copies and dead stores do not.)")

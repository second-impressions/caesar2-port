"""``c2 savings`` -- the CalcSavings forward-model dossier (P1 surface).

Per conflict: the RECORDED savings next to the FORWARD-COMPUTED value
(c2.regalloc.savings, certified 20,432/20,432 exact / zero misses on
the 2026-07-10g substrate) -- and with ``--var``, the per-REF ledger:
every unit of the conflict's savings named to (block, depth, ins, ref
kind, weighted units).

Why this matters for the byte-equal grind: savings drive the ConfBefore
sort order, TooGreedy and WorthProlog.  A Cascade verdict like
place_sprite's "ECX<->ESI needs sav(side) <= 6 or sav(t.25c0) >= 8" was
previously actionable only by blind probing; the ledger names WHICH
refs carry each unit, so "remove ~2 straight-line uses" becomes "these
are the 8 refs of `side`; the deletable ones are ...".  Pair with
c2.regalloc.edit_sim.diagnose_savings_edit for the sort/pick replay of
a hypothetical delta.
"""
from __future__ import annotations

import json as _json
from pathlib import Path

import typer


def savings_view(
    function: str = typer.Argument(..., help="function name"),
    file: str = typer.Option(None, "--file", help="TU basename"),
    var: str = typer.Option(None, "--var",
                            help="drill into one conflict: named local, "
                                 "anon id (6c168804) or t.XXXX suffix"),
    flip: str = typer.Option(None, "--flip",
                             help="'VAR=REG': search grounded savings "
                                  "edits that re-seat VAR in REG through "
                                  "the full sort+pick replay"),
    depth: int = typer.Option(1, "--depth",
                              help="1 = single edits; 2 = composed pairs "
                                   "(movers-first, capped)"),
    json_out: bool = typer.Option(False, "--json"),
):
    """CalcSavings forward-model dossier (recorded vs recomputed +
    per-ref ledger)."""
    import c2.regalloc as regalloc
    from c2.regalloc import savings as sv
    from c2.commands.regtrace import _find_function

    def rows_sav(rt, conf):
        for a in rt.get("alloc") or []:
            if a["conf"] == conf and a.get("round", 0) == 0:
                return a["savings"]
        return "?"

    cfile, _, _, _ = _find_function(function, file)
    td = regalloc.file_trace(Path(cfile), Path("decomp/include"))
    rt = (td.get("by_func") or {}).get(function)
    if rt is None:
        typer.echo(f"{function} not in {cfile}'s trace")
        raise typer.Exit(1)

    snap = sv.snap_index(rt)
    if snap is None:
        typer.echo("no il_walks substrate (pre-v46 trace?)")
        raise typer.Exit(1)
    amap = sv.alias_map(rt)
    dmap = sv._depth_map(rt)

    if flip and "=" in flip:
        from c2.regalloc.savings_flip import flip_search
        tgt, reg = (s.strip() for s in flip.split("=", 1))
        r = flip_search(rt, tgt, reg, depth=depth)
        if json_out:
            typer.echo(_json.dumps(r, indent=1, default=str))
            return
        if "error" in r:
            typer.echo(f"  flip: {r['error']}")
            raise typer.Exit(1)
        typer.echo(f"{function}: flip {tgt} -> {r['want']}  "
                   f"(identity replay {'OK' if r['identity_ok'] else 'MISMATCH -- report'};"
                   f" {r['replayed']} replays over {r['candidates']} "
                   f"single edits, {r.get('movers', 0)} movers, depth {depth})")
        if not r["hits"]:
            typer.echo(f"  NO grounded savings edit (depth {depth}) flips "
                       "this seat through the full replay -- the lever is "
                       "outside the savings-order class (check c2 seats' "
                       "verdict: masked/outscored/rover)"
                       + (", or try --depth 2." if depth < 2 else "."))
            return
        for h in r["hits"][:12]:
            alt = f" (+{h['alt']} equivalent edits)" if h.get("alt") else ""
            conf = "" if h["confident"] else "  [LOW-CONF: rescored rows]"
            if h.get("edits", 1) > 1:
                typer.echo(f"  FLIP via COMPOSED {h['kind']}: "
                           f"{h['detail']}{alt}{conf}")
            elif "sav" in h:
                typer.echo(f"  FLIP via {h['kind']} of {h['label']} "
                           f"{h['detail']}  sav {rows_sav(rt, h['conf'])}->"
                           f"{h['sav']}{alt}{conf}")
            else:
                typer.echo(f"  FLIP via {h['kind']} on {h['label']}: "
                           f"{h['detail']}{alt}{conf}")
            for s in h["side_effects"]:
                typer.echo(f"       side: {s['label']} "
                           f"{s['from']}->{s['to']}  (must MATCH a PS "
                           f"seat_recon swap or the edit is wrong)")
            if not h["side_effects"]:
                typer.echo("       no side effects -- clean single flip")
        return

    def _match(a) -> bool:
        if var is None:
            return False
        suffix = var[2:] if var.startswith("t.") else var
        nm = str(a.get("name") or "")
        return (a.get("var") == var or nm == var
                or (len(suffix) >= 3 and nm.endswith(suffix.lower())))

    rows_out = []
    for a in rt.get("alloc") or []:
        if a.get("round", 0) != 0:
            continue
        fin = sv.savings_for_row(rt, a, snap, dmap, amap)
        rows_out.append((a, fin))

    if json_out:
        out = [{"var": a.get("var"), "name": a["name"],
                "recorded": a["savings"], "computed": fin,
                "reg": a.get("reg_name"),
                "ledger": (sv.ref_ledger(rt, a, snap, amap)
                           if _match(a) else None)}
               for a, fin in rows_out]
        typer.echo(_json.dumps(out, indent=1, default=str))
        return

    n_ok = sum(1 for a, fin in rows_out if fin == a["savings"])
    n_gap = sum(1 for _, fin in rows_out if fin is None)
    typer.echo(f"{function}: {len(rows_out)} conflicts -- "
               f"{n_ok} recomputed exact, {n_gap} substrate-gapped"
               + ("" if n_ok + n_gap == len(rows_out) else
                  f", {len(rows_out) - n_ok - n_gap} MISMATCH (model bug "
                  f"or new mechanism -- report)"))
    for a, fin in rows_out:
        label = a.get("var") or a["name"]
        mark = ("=" if fin == a["savings"]
                else "GAP" if fin is None else "!!")
        typer.echo(f"  {label:>14} sav={a['savings']:<5} "
                   f"fwd={'-' if fin is None else fin:<5} {mark}  "
                   f"-> {a.get('reg_name') or 'mem'}")
        if _match(a):
            led = sv.ref_ledger(rt, a, snap, amap)
            if led is None:
                typer.echo("       (ledger unavailable: substrate gap)")
                continue
            for e in led:
                typer.echo(
                    f"       {e['side']:>4} {e['units']}u x W(d{e['depth']})"
                    f" = {e['weighted']:<5} {e['kind']:<16} "
                    f"ins {e['ins']} op {e['opcode']:#x} blk {e['blk']}")
            tot = (sum(e["weighted"] for e in led if e["side"] == "save")
                   - sum(e["weighted"] for e in led if e["side"] == "cost"))
            typer.echo(f"       total {max(tot, 0)} (recorded "
                       f"{a['savings']})")

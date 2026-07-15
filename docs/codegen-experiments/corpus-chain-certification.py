"""corpus-chain-certification -- the [P0] full-corpus certification run
for the allocator prediction stack (TODO.md 2026-07-11 item 1).

Every chain certification to date (liveness 16,572/16,572 ·
with.regs 6,243/6,243 · CountRegMoves 32,192/32,192 · GiveBestReg
19,116/19,116 · full-chain seat identity 6,243/6,243 · sorts/slots
100%) ran on the pcsound+map+battle sample.  This experiment runs the
SAME certifiers over every TU in decomp/src, so the claims the tools
now surface corpus-wide (`c2 seats`, the `Seat-chain:` hint, regtrace
chain verdicts) are hardened corpus-wide.  Any miss is a NEW MECHANISM
to reverse-engineer, not noise.

Method
------
Per TU (regalloc.file_trace, content-hash cached; only uncached TUs
cost trace time), per routine:

  1. liveness.certify_routine   -- within-block FlowConflicts port
  2. neighbours.certify         -- with.regs mask port
  3. seatchain.certify_chain    -- full-chain seat identity
                                   (mask -> crm10a_v2 scores -> pick)
  4. replay.validate_routine    -- ConfBefore ShellSort + GiveBestReg
                                   picks from recorded scores
  5. slots.validate_routine_chain -- Names[N_TEMP] births -> nb1 ->
                                   nb2 -> nt sort -> [esp+N] slots
  6. savings.certify_routine      -- P1 CalcSavings forward model
                                   (iv IL walk -> per-block units ->
                                   loop-weighted final savings)
  7. toogreedy.certify_routine    -- P2 TooGreedy port (RegList/RegSets
                                   need chains, StealsIdx/StealsSeg,
                                   allocation-vintage gi tg_ctx)
  8. fixins.certify_routine       -- P5 FixInstructions rewrite kernel
                                   (vs the v50 per-round rr walks)
  9. rover.certify_picks/_except  -- P6 FindRegister forward model:
                                   cursor replay == frx ground truth,
                                   and except == zap|live|resreg (the
                                   >= 2026-07-13 component fields; the
                                   counterfactual-walk substrate)
  9b. rover.certify_attribution   -- P6c seat-flip substrate: every fr
                                   except bit attributable to BASE /
                                   static(gi) / live / resreg / a
                                   spanning committed seat (the bits a
                                   seat_flip_walk may legally move)
  9c. rover.certify_chain_model   -- the offline MakeFlowGraph chain
                                   model: RPO over the bre edge order +
                                   ReturnsToBottom == the recorded br
                                   chain (ReorderBlocks/intervals not
                                   modeled; misses route there)

Results stream into .c2-cache/corpus-chain-cert.json after every TU,
so an interrupted run resumes for free (the trace cache) and partial
results are readable while it runs.

Run:  uv run python docs/codegen-experiments/corpus-chain-certification.py
"""
from __future__ import annotations

import json
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import c2.regalloc as regalloc
from c2.regalloc import (fixins, liveness, neighbours, replay, rover,
                         savings, toogreedy)
from c2.regalloc import shellsort_sim_slots as slots
from c2.regalloc.seatchain import certify_chain

SRC = Path("decomp/src")
INC = Path("decomp/include")
OUT = Path(".c2-cache/corpus-chain-cert.json")


def certify_tu(cfile: Path) -> dict:
    td = regalloc.file_trace(cfile, INC)
    tu = {"functions": 0, "errors": [],
          "liveness": {"rows": 0, "exact": 0, "misses": []},
          "withregs": {"total": 0, "either": 0, "misses": []},
          "chain": {"rows": 0, "agree": 0, "recomputed_full": 0,
                    "misses": []},
          "sort": {"routines": 0, "sort_ok": 0, "picks_total": 0,
                   "picks_ok": 0, "misses": []},
          "slots": {"stages": 0, "ok": 0, "misses": []},
          "savings": {"rows": 0, "exact": 0, "gapped": 0, "misses": []},
          "fixins": {"slots": 0, "exact": 0, "routines": 0, "misses": []},
          "toogreedy": {"rows": 0, "checked": 0, "agree": 0,
                        "no_sub": 0, "misses": []},
          "rover": {"picks": 0, "picks_ok": 0, "except": 0,
                    "except_ok": 0, "attrib": 0, "attrib_ok": 0, "attrib_pinned": 0,
                    "chains": 0, "chains_ok": 0, "misses": []}}
    for fn, rt in (td.get("by_func") or {}).items():
        tu["functions"] += 1
        try:
            r = liveness.certify_routine(rt)
            tu["liveness"]["rows"] += r["rows"]
            tu["liveness"]["exact"] += r["exact"]
            for m in r["misses"][:2]:
                tu["liveness"]["misses"].append({"fn": fn, "m": m})

            r = neighbours.certify(rt.get("alloc") or [])
            tu["withregs"]["total"] += r["total"]
            tu["withregs"]["either"] += r["either"]
            for m in r["misses"][:2]:
                tu["withregs"]["misses"].append({"fn": fn, **m})

            r = certify_chain(rt)
            tu["chain"]["rows"] += r["rows"]
            tu["chain"]["agree"] += r["agree"]
            tu["chain"]["recomputed_full"] += r["recomputed_full"]
            for m in r["misses"][:2]:
                tu["chain"]["misses"].append({"fn": fn, **m})

            r = replay.validate_routine(rt)
            if r["sort_ok"] is not None:
                tu["sort"]["routines"] += 1
                tu["sort"]["sort_ok"] += 1 if r["sort_ok"] else 0
                if not r["sort_ok"]:
                    tu["sort"]["misses"].append({"fn": fn,
                                                 "kind": "sort"})
            tu["sort"]["picks_total"] += r["picks_total"]
            tu["sort"]["picks_ok"] += r["picks_ok"]
            for m in r["pick_misses"][:2]:
                tu["sort"]["misses"].append({"fn": fn, "kind": "pick",
                                             **m})

            r = slots.validate_routine_chain(rt)
            for stage, ok in r.items():
                if ok is None:
                    continue
                tu["slots"]["stages"] += 1
                tu["slots"]["ok"] += 1 if ok else 0
                if not ok:
                    tu["slots"]["misses"].append({"fn": fn,
                                                  "stage": stage})

            r = savings.certify_routine(rt)
            tu["savings"]["rows"] += r["rows"]
            tu["savings"]["exact"] += r["exact"]
            tu["savings"]["gapped"] += r["gapped"]
            fx = fixins.certify_routine(rt)
            if not fx["no_sub"]:
                tu["fixins"]["routines"] += 1
                tu["fixins"]["slots"] += fx["slots"]
                tu["fixins"]["exact"] += fx["exact"]
                for m in fx["misses"][:2]:
                    tu["fixins"]["misses"].append({"fn": fn, **m})
            for m in r["misses"][:2]:
                tu["savings"]["misses"].append({"fn": fn, **m})

            r = toogreedy.certify_routine(rt)
            for k in ("rows", "checked", "agree", "no_sub"):
                tu["toogreedy"][k] += r[k]
            for m in r["misses"][:2]:
                tu["toogreedy"]["misses"].append({"fn": fn, **m})

            r = rover.certify_picks(rt)
            tu["rover"]["picks"] += r["total"]
            tu["rover"]["picks_ok"] += r["ok"]
            for m in r["mismatches"][:2]:
                tu["rover"]["misses"].append({"fn": fn, "kind": "pick",
                                              "m": m})
            r = rover.certify_except(rt)
            tu["rover"]["except"] += r["total"]
            tu["rover"]["except_ok"] += r["ok"]
            for m in r["mismatches"][:2]:
                tu["rover"]["misses"].append({"fn": fn, "kind": "except",
                                              "m": m})
            r = rover.certify_attribution(rt)
            tu["rover"]["attrib"] += r["total"]
            tu["rover"]["attrib_ok"] += r["ok"]
            tu["rover"]["attrib_pinned"] += r["pinned"]
            for m in r["misses"][:2]:
                tu["rover"]["misses"].append({"fn": fn, "kind": "attrib",
                                              "m": (m[0], hex(m[1]))})
            r = rover.certify_chain_model(rt)
            if r is not None:
                tu["rover"]["chains"] += 1
                tu["rover"]["chains_ok"] += 1 if r["ok"] else 0
                if not r["ok"]:
                    tu["rover"]["misses"].append(
                        {"fn": fn, "kind": "chain",
                         "m": (r["first_diff"], r["n"])})
        except Exception:
            tu["errors"].append({"fn": fn,
                                 "err": traceback.format_exc(limit=3)})
    return tu


def main() -> None:
    results: dict = {}
    if OUT.exists():
        results = json.loads(OUT.read_text()).get("tus", {})
    files = sorted(SRC.glob("*.c"))
    t0 = time.time()
    for i, cfile in enumerate(files, 1):
        if cfile.name in results:
            print(f"[{i}/{len(files)}] {cfile.name}: cached result, skip")
            continue
        print(f"[{i}/{len(files)}] {cfile.name}: tracing+certifying ...",
              flush=True)
        t1 = time.time()
        try:
            tu = certify_tu(cfile)
        except Exception:
            tu = {"tu_error": traceback.format_exc(limit=5)}
        results[cfile.name] = tu
        OUT.write_text(json.dumps({"tus": results}, indent=1))
        if "tu_error" in tu:
            print(f"    TU ERROR:\n{tu['tu_error']}")
            continue
        print(f"    fns={tu['functions']} "
              f"liveness {tu['liveness']['exact']}/{tu['liveness']['rows']} "
              f"withregs {tu['withregs']['either']}/{tu['withregs']['total']} "
              f"chain {tu['chain']['agree']}/{tu['chain']['rows']} "
              f"picks {tu['sort']['picks_ok']}/{tu['sort']['picks_total']} "
              f"slots {tu['slots']['ok']}/{tu['slots']['stages']} "
            f"savings {tu['savings']['exact']}/{tu['savings']['rows']} "
            f"(+{tu['savings']['gapped']} gapped) "
            f"tg {tu['toogreedy']['agree']}/{tu['toogreedy']['checked']} "
            f"fixins {tu['fixins']['exact']}/{tu['fixins']['slots']} "
            f"rover {tu['rover']['picks_ok']}/{tu['rover']['picks']} "
            f"exc {tu['rover']['except_ok']}/{tu['rover']['except']} "
              f"({time.time() - t1:.0f}s)")

    # -- corpus roll-up ------------------------------------------------
    tot: dict = {}
    misses: list = []
    for name, tu in results.items():
        if "tu_error" in tu:
            continue
        for cert in ("liveness", "withregs", "chain", "sort", "slots",
                     "savings", "toogreedy", "fixins", "rover"):
            if cert not in tu:      # cached result from an older gate set
                continue
            d = tot.setdefault(cert, {})
            for k, v in tu[cert].items():
                if k == "misses":
                    for m in v:
                        misses.append({"tu": name, "cert": cert, **m})
                elif isinstance(v, (int, float)):
                    d[k] = d.get(k, 0) + v
        for e in tu.get("errors") or []:
            misses.append({"tu": name, "cert": "ERROR", **e})
    print("\n== CORPUS ROLL-UP ==")
    for cert, d in tot.items():
        print(f"  {cert}: " + "  ".join(f"{k}={v}" for k, v in d.items()))
    print(f"  misses: {len(misses)}")
    for m in misses[:40]:
        print(f"    {m}")
    print(f"\ntotal {time.time() - t0:.0f}s; results in {OUT}")


if __name__ == "__main__":
    main()

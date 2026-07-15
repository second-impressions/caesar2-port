#!/usr/bin/env python3
"""Analyze the exhaustive flag-survey results (streamed, memory-light).

Input: data/flag-survey/funcdiffs.jsonl.gz  (line 1 = baseline full diffs;
       lines 2.. = per-config DELTAS vs baseline, masked diff-vs-PS).

Produces:
  * per-function reduction table  -> data/flag-survey/by_function.json
      for every residue fn: baseline diff, min diff across all configs,
      the flag(s) achieving it, and the reduction.
  * per-TU movement table         -> data/flag-survey/by_tu.json
      for every TU: baseline total masked-diff, min total under any
      config (whole-TU-closer), and the achieving flag.
  * prints the top movers of each kind.

Usage: python3 tools/flag_survey_analyze.py
"""
import gzip, json, os
from collections import defaultdict

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = "data/flag-survey/funcdiffs.jsonl.gz"
if not os.path.exists(SRC):
    SRC = "/tmp/flag_full_funcdiffs.jsonl"
opener = gzip.open if SRC.endswith(".gz") else open


def main():
    base = {}             # tu -> {fn: diff}
    base_tot = {}         # tu -> sum(diffs)
    # per-function: min diff + configs achieving it (only for residue fns)
    fn_min = {}           # (tu,fn) -> [min_diff, set(configs)]
    fn_base = {}          # (tu,fn) -> baseline diff (residue only)
    # per-TU: min total + config
    tu_min = {}           # tu -> [min_total, config]

    with opener(SRC, "rt") as f:
        first = json.loads(f.readline())
        assert first.get("baseline")
        for tu, dd in first["diffs"].items():
            base[tu] = dd
            base_tot[tu] = sum(dd.values())
            tu_min[tu] = [base_tot[tu], "BASE"]
            for fn, d in dd.items():
                if d > 0:
                    fn_base[(tu, fn)] = d
                    fn_min[(tu, fn)] = [d, set()]   # set of configs that match this min
        n = 0
        for line in f:
            r = json.loads(line)
            cfg = r["cfg"]
            deltas = r.get("deltas", {})
            # per-TU total under this config = base_tot + delta sum (sparse)
            for tu, fnd in deltas.items():
                tot = base_tot[tu] + sum(fnd[fn] - base[tu].get(fn, 0) for fn in fnd)
                if tot < tu_min[tu][0]:
                    tu_min[tu] = [tot, cfg]
                for fn, d in fnd.items():
                    key = (tu, fn)
                    if key in fn_base:           # a residue fn
                        cur = fn_min[key]
                        if d < cur[0]:
                            fn_min[key] = [d, {cfg}]
                        elif d == cur[0]:
                            cur[1].add(cfg)
            n += 1
    print(f"analyzed baseline + {n} configs", flush=True)

    # baseline tokens to strip so the hint shows only the deviation
    BASETOK = {"BASE", "-bt=dos", "-mf", "-4r", "-s", "-d1"}

    def clean_flags(cfgs):
        toks = sorted({t for c in cfgs for t in c.split() if t not in BASETOK})
        return toks[:10]

    # --- per-function reductions ---
    func_rows = []
    for (tu, fn), (mind, cfgs) in fn_min.items():
        bd = fn_base[(tu, fn)]
        if mind < bd:
            func_rows.append({
                "tu": tu, "fn": fn.rstrip("_"), "baseline": bd, "min": mind,
                "reduction": bd - mind, "flipped": mind == 0,
                "n_configs": len(cfgs),
                "flags": clean_flags(list(cfgs)[:80]),
            })
    func_rows.sort(key=lambda r: -r["reduction"])
    json.dump(func_rows, open("data/flag-survey/by_function.json", "w"), indent=1)

    # --- per-TU movement ---
    tu_rows = []
    for tu, (mint, cfg) in tu_min.items():
        bt = base_tot[tu]
        tu_rows.append({"tu": tu, "baseline_total_diff": bt, "min_total_diff": mint,
                        "reduction": bt - mint, "best_flag": cfg})
    tu_rows.sort(key=lambda r: -r["reduction"])
    json.dump(tu_rows, open("data/flag-survey/by_tu.json", "w"), indent=1)

    nres = len(fn_base)
    nred = sum(1 for r in func_rows)
    nflip = sum(1 for r in func_rows if r["flipped"])
    print(f"\nresidue fns (baseline masked-diff>0): {nres}", flush=True)
    print(f"  reduced by >=1 flag: {nred}   flipped to exact: {nflip}", flush=True)
    print(f"\n=== TOP 25 FUNCTION reductions (toward PS) ===", flush=True)
    for r in func_rows[:25]:
        flip = " [FLIP->0]" if r["flipped"] else ""
        print(f"  {r['tu']:9s} {r['fn']:34s} {r['baseline']:5d} -> {r['min']:5d}"
              f"  (-{r['reduction']}){flip}  {r['flags'][:5]}", flush=True)
    print(f"\n=== PER-TU whole-TU movement (total masked-diff) ===", flush=True)
    for r in sorted(tu_rows, key=lambda x: -x["reduction"]):
        pct = 100 * r["reduction"] // max(1, r["baseline_total_diff"])
        print(f"  {r['tu']:10s} {r['baseline_total_diff']:6d} -> {r['min_total_diff']:6d}"
              f"  (-{r['reduction']}, {pct}%)  best={r['best_flag']}", flush=True)
    print("\nwrote data/flag-survey/by_function.json + by_tu.json", flush=True)


if __name__ == "__main__":
    main()

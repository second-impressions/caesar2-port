"""spell-verdict-audit -- score `c2 spell`'s screening verdicts against
byte compiles, using the BYTE-EXACT corpus as labeled ground truth.

Motivation (2026-07-09): the trace-level screener (`c2 spell`) makes
falsifiable claims -- "INERT@TREE = provably unreachable, stop" and
"only LIVE candidates are worth a byte compile" -- that had never been
batch-validated.  On a byte-exact function the source is KNOWN correct,
so every generated fold/unfold candidate gives a perfectly labeled
(source-delta -> screener-verdict -> byte-delta) triple: any INERT
verdict on a candidate that CHANGES bytes is a measured false negative.

Method
------
1. Take all byte-exact functions >= 48 b (verify.json), generate the
   same fold (de_invent) / unfold (cache_field) candidates that
   `c2 spell --suggest` emits (forge span presets through _ShimForge).
   248 fns qualified; 60 selected round-robin across 26 TUs, cap 6
   candidates/fn -> 119 candidates.
2. Screen each candidate with the trace ladder
   (regalloc.trace_compile + lwalk.spelling_compare / birth_compare /
   il_birth_compare).
3. Byte-compile each candidate with ForgeBuilder (LE mode, verifier
   byte parity) + judge.score vs the PS reference; the base TU must
   score byte_diff 0 (sanity gate, 58/60 passed -- 2 skips were
   .map-carve misses on static-linkage fns).
   changed := byte_diff != 0 OR the linked slab prefix
   (len(PS)+64 b) differs from the base compile's.

Results (109 scored candidate rows, 58 fns)
-------------------------------------------
  verdict       n    changed  unchanged   precision
  LIVE         86       80        6        0.93  (predicts byte change)
  INERT@BURN   23        4       19        0.83  (predicts neutrality)
  INERT@TREE    0        -        -        (see bug below)
  ERROR         4  (candidate does not compile; both channels agree)

BUG FOUND AND FIXED: `_trace_routine` (c2/commands/spell.py) selected
the traced routine by fr-hits seeded at -1 -- a function with NO fr
record in its span silently matched the FIRST fr-carrying routine in
the TU.  Base and candidate then compared the same WRONG routine and
emitted a confident false "INERT@TREE -- provably unreachable, stop".
In the first (pre-fix) run ALL 13 INERT@TREE verdicts were this bug;
10 of the 13 candidates actually moved bytes (7..193 b).  Worked
example: colour_cycle_delay1 (lib32.c L3346-3381) matched a routine
whose fr lines were 128-140.  Fixed by scoring lw+fr line hits inside
the span (slack -2/+8 for candidate line drift) and REQUIRING a
nonzero hit.

Residual false negatives (post-fix): 4 rows / 2 fns
(get_pm_over_diamond x3, control_buttons x1), signature "IL births
DIVERGED + walk IDENTICAL".  Mechanism: the lw walk is a LdStAlloc-
stage lens; a fold that changes the CONFLICT GRAPH / savings upstream
(e.g. de-inventing rel_x duplicates `mouse_x + x_adj - ...` into two
reads) can leave the walk signature intact while regalloc moves 193 b.
Consequence: INERT@BURN means DEPRIORITIZE, not proven dead; only
INERT@TREE (post-fix: genuinely identical trees of the RIGHT routine)
is a stop verdict.

LIVE-but-unchanged (6 rows) are the benign direction and consistent
with the rover model: a fold can land the rover on the same register
(byte-neutral +1 advance), and zero-delta walk reorders can re-seat
identically.

Reproduce:  uv run python docs/codegen-experiments/spell-verdict-audit.py
(~2 min warm; writes .c2-cache/spell-audit.json)
"""
from __future__ import annotations

import json
import os
import random
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def apply_edits(text: str, edits) -> str:
    buf = text
    for e in sorted(edits, key=lambda e: (-e.start, -e.end)):
        buf = buf[: e.start] + e.replacement + buf[e.end :]
    return buf


def main() -> None:
    os.chdir(ROOT)
    from c2 import regalloc
    from c2.commands.regtrace import INCLUDE_DIR, _find_function
    from c2.commands.spell import _ShimForge
    from c2.forge import judge, ps_ref
    from c2.forge.build import ForgeBuilder
    from c2.forge.presets import de_invent_candidates, preset_cache_field
    from c2.regalloc import lwalk

    vj = json.load(open(".c2-cache/verify.json"))
    exact = [f for f in vj["functions"]
             if f.get("exact") and f.get("size", 0) >= 48
             and f["file"].endswith(".c")]

    tu_text: dict[str, str] = {}
    pool: dict[str, tuple[dict, list]] = {}
    for f in exact:
        text = tu_text.setdefault(f["file"],
                                  Path(f["file"]).read_text(errors="replace"))
        shim = _ShimForge(text, f["name"])
        try:
            de_invent_candidates(shim)
            preset_cache_field(shim)
        except Exception:
            continue
        if shim.collected:
            pool[f["name"]] = (f, shim.collected)
    print(f"{len(pool)} exact fns with candidates")

    # round-robin selection across TUs
    random.seed(7)
    by_tu: dict[str, list[str]] = {}
    for name, (f, _) in pool.items():
        by_tu.setdefault(f["file"], []).append(name)
    tus = sorted(by_tu)
    random.shuffle(tus)
    sel: list[str] = []
    idx = {t: 0 for t in tus}
    while len(sel) < 60:
        progressed = False
        for t in tus:
            lst = sorted(by_tu[t])
            if idx[t] < len(lst):
                sel.append(lst[idx[t]])
                idx[t] += 1
                progressed = True
                if len(sel) >= 60:
                    break
        if not progressed:
            break

    def trace_routine(func: str, src_text: str, start: int, end: int) -> dict:
        files = {"TARGET.C": src_text}
        for h in INCLUDE_DIR.glob("*.h"):
            files[h.name.upper()] = h.read_text(errors="replace")
        td = regalloc.trace_compile(files, main="TARGET.C")
        lo, hi = start - 2, end + 8
        best, bh = None, 0
        for r in td["routines"]:
            hits = sum(1 for x in r.get("lw", [])
                       if x.get("line") and lo <= x["line"] <= hi)
            hits += sum(1 for x in r.get("fr", [])
                        if x.get("line") and lo <= x["line"] <= hi)
            if hits > bh:
                bh, best = hits, r
        if best is None:
            raise RuntimeError(f"{func}: no traced routine in {lo}-{hi}")
        return best

    builder = ForgeBuilder(source_root=ROOT / "decomp")
    builder.warm()
    results: list[dict] = []
    status: dict[str, str] = {}
    t0 = time.time()
    for fn in sel:
        f, cands = pool[fn]
        base_text = tu_text[f["file"]]
        file = os.path.basename(f["file"])
        try:
            br_base = builder.compile_one(file=file, function=fn,
                                          source_text=base_text)
        except Exception as exc:            # noqa: BLE001
            status[fn] = f"base build fail: {exc}"
            continue
        ps = ps_ref.load(fn)
        ps_len = len(ps.bytes_)
        sc_base = judge.score(ps, br_base.code, br_base.fixups,
                              br_base.line_marks)
        if not sc_base.ok or sc_base.bytes != 0:
            status[fn] = f"base not exact ({sc_base.bytes})"
            continue
        _, start, end, _ = _find_function(fn, None)
        try:
            base_r = trace_routine(fn, base_text, start, end)
        except Exception as exc:            # noqa: BLE001
            status[fn] = f"base trace fail: {exc}"
            continue
        win = ps_len + 64
        for tag, edits in cands[:6]:
            cand_text = apply_edits(base_text, edits)
            row: dict = dict(fn=fn, file=file, tag=tag, ps_len=ps_len)
            try:
                cand_r = trace_routine(fn, cand_text, start, end)
                v = lwalk.spelling_compare(base_r, cand_r)
                row.update(
                    head=v.headline(), tree_same=v.tree_same,
                    walk_same=v.walk_same, delta=v.delta,
                    births=lwalk.birth_compare(base_r, cand_r)["verdict"],
                    il_births=lwalk.il_birth_compare(base_r, cand_r)["verdict"],
                )
            except Exception as exc:        # noqa: BLE001
                row["head"] = f"ERROR {exc}"
            try:
                br = builder.compile_one(file=file, function=fn,
                                         source_text=cand_text)
                sc = judge.score(ps, br.code, br.fixups, br.line_marks)
                row["bytes"] = sc.bytes
                row["changed"] = (sc.bytes != 0
                                  or br.code[:win] != br_base.code[:win])
            except Exception as exc:        # noqa: BLE001
                row["bytes"] = None
                row["changed"] = None
                row["build_err"] = str(exc)[:100]
            results.append(row)
        status[fn] = "ok"
    builder.shutdown()

    out = ROOT / ".c2-cache" / "spell-audit.json"
    json.dump(dict(results=results, fn_status=status), open(out, "w"),
              indent=1)
    tab: dict[str, Counter] = {}
    for r in results:
        c = r["head"].split(" ")[0].split("(")[0]
        k = ("build_err" if r.get("changed") is None
             else "changed" if r["changed"] else "unchanged")
        tab.setdefault(c, Counter())[k] += 1
    print(f"\n{len(results)} rows in {time.time() - t0:.0f}s -> {out}")
    for c in sorted(tab):
        print(f"  {c:14s} {dict(tab[c])}")


if __name__ == "__main__":
    main()

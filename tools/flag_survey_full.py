#!/usr/bin/env python3
"""Exhaustive compiler-flag search: which flag config maximizes total
byte-exact functions vs PS across ALL C TUs?

Metric: sum over all 34 C TUs of byte-exact-vs-PS function count, with
decomp-verify-grade masking (fixups + rel32 branch displacements).

Covers (deduped):
  * every single-flag deviation from baseline (incl. the "fixed" flags),
  * all -o subsets size 1..4 + permutations of the order-sensitive
    letters {d,s,t,x} within each subset,
  * pairwise combinations across dimensions,
  * the structural cross-product callconv x char x debug x packing.

Archives every .obj (hash-named) + manifest, monitors disk/inodes.
Streams any config that ties or beats baseline.
"""
import sys, os, time, threading, tempfile, shutil, hashlib, json, itertools
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from itertools import combinations, permutations

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ".")
from c2.commands.compiler_id import (
    _strip_stub_bodies, _run_in_container, _load_exe_functions, _exe_func_bytes)
from c2.commands.decomp_verify import _parse_annotations, _rel_call_jmp_disp_mask
from c2.parsers.omf import parse_obj_functions
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
_CS_SURVEY = Cs(CS_ARCH_X86, CS_MODE_32)

IMAGE = "localhost/watcom-10.0a-wibo"
INC = Path("decomp/include")
BASE = "-bt=dos -mf -4r -s -d1"
WORKERS = int(os.environ.get("SURVEY_WORKERS", "6"))
INC_HEADERS = [(h.name, h.read_text()) for h in INC.glob("*.h")]
import glob
C_TUS = sorted(Path(p).stem for p in glob.glob("decomp/src/*.c"))

print("loading PS.EXE ...", flush=True)
CODE, FIXUPS, CODE_SYMS, _ = _load_exe_functions(
    Path("data/PS.EXE"), Path("data/out/symbols.json"))
PS_FN = {}
for tu in C_TUS:
    addrs, _ = _parse_annotations(Path(f"decomp/src/{tu}.c"))
    d = {}
    for s in CODE_SYMS:
        if s["address"] in addrs:
            pb, pf = _exe_func_bytes(s["address"], CODE, FIXUPS, CODE_SYMS)
            if pb is not None:
                d[s["raw_name"]] = (pb, pf)
    if d:
        PS_FN[tu] = d
TUS = sorted(PS_FN)            # TUs with annotated funcs
print(f"{len(TUS)} C TUs with annotated funcs; "
      f"{sum(len(v) for v in PS_FN.values())} annotated funcs total", flush=True)


def _dm(a, af, b, bf):
    """Tail-merge-aware masked diff-vs-PS.

    Compares only min(len(a),len(b)) bytes (so a tail-merged PS stub is
    compared against the RC prefix only) and adds NO length-mismatch term
    -- this is what makes it tail-merge-aware: evolve_a_building -> 1 not
    127, matching `c2 decomp-verify`.

    Masks by UNION (skip any offset that is a fixup on EITHER side, or a
    rel call/jmp disp on either side). We must mask-union rather than
    zero-fill (decomp-verify's _compare_bytes) because PS fixups are LE
    loader relocations (link-resolved, sparse) while the RC fixups come
    from the raw .obj (OMF, includes link-resolved self-relative refs);
    the two fixup representations don't align, so zero-fill would inject
    spurious diffs at .obj-only fixup offsets.

    Also masks residue cluster #32 (jump-table alignment filler): when
    every remaining diff sits in a trailing fixup-dense JUMP TABLE region
    (one loader fixup per 4-byte entry) plus its <=7-byte alignment NOP
    pad, the CODE is byte-exact and only the dead inter-table filler
    differs -- decomp-verify counts these as exact (~pad). Matching that
    here stops copy_ferret_run_to_citizen / fight_barbarian /
    try_this_battlemap_square from showing as spurious flips."""
    n = min(len(a), len(b))
    mask = set(af) | set(bf) | _rel_call_jmp_disp_mask(a[:n]) | _rel_call_jmp_disp_mask(b[:n])
    diffs = [i for i in range(n) if i not in mask and a[i] != b[i]]
    if not diffs:
        return 0
    # Cheap pre-check: is the tail (from the first diff to n) a dense PS
    # jump table (>=8 fixup bytes, <=7 non-fixup pad)?  Only then pay for
    # the trailing-pad classification.
    fd = diffs[0]
    tail = n - fd
    if tail >= 8:
        fx = sum(1 for i in range(fd, n) if i in af)
        if fx >= 8 and (tail - fx) <= 7 and _all_after_last_ret(a, fd):
            # every diff is dead jump-table filler/pad -> code exact
            return 0
    return len(diffs)


def _all_after_last_ret(code, first_diff):
    """True if a ret/jmp ends at or before first_diff (so everything from
    first_diff on is dead trailing data, not executed code)."""
    last_end = None
    for insn in _CS_SURVEY.disasm(code[:first_diff + 1], 0):
        if insn.mnemonic.startswith(("ret", "jmp")) and insn.address + insn.size <= first_diff:
            last_end = insn.address + insn.size
    return last_end is not None


def _compile(tu, cflags):
    """Compile in an isolated tempdir, parse, discard the .obj (data already
    extracted as per-function bytes)."""
    cf_ = Path(f"decomp/src/{tu}.c"); work = Path(tempfile.mkdtemp(prefix="ff_"))
    try:
        (work / cf_.name).write_text(_strip_stub_bodies(cf_.read_text()))
        for n, t in INC_HEADERS:
            (work / n).write_text(t)
        ok, _ = _run_in_container(work, IMAGE, f"wcc386 {cflags} -fo={cf_.stem}.obj {cf_.name}")
        obj = work / f"{cf_.stem}.obj"
        if not obj.exists():
            obj = work / f"{cf_.stem.upper()}.OBJ"
        if not ok or not obj.exists():
            return None
        try:
            return {n: (c, f) for n, c, f in parse_obj_functions(obj)}
        except Exception:
            return None
    finally:
        shutil.rmtree(work, ignore_errors=True)


def func_diffs(tu, cflags):
    """Per-function masked diff-vs-PS dict {fn: ndiff} for TU+flags, or None
    if the compile never succeeded. (Full granular data — replaces the .obj.)"""
    want = set(PS_FN[tu]); need = max(1, int(0.8 * len(want)))
    by = None
    for _ in range(4):
        by = _compile(tu, cflags)
        if by is not None and len(want & set(by)) >= need:
            break
        by = None; time.sleep(0.2)
    if by is None:
        return None
    return {fn: _dm(pb, pf, *by[fn]) for fn, (pb, pf) in PS_FN[tu].items()
            if fn in by}


def gen_configs():
    """Return list[(label, cflags)] deduped by the exact wcc386 arg string."""
    cfgs = {}
    def add(cf):
        cf = cf.strip()
        cfgs.setdefault(cf, cf)
    add(BASE)
    # NOTE: flags PROVEN inert (byte-identical _TEXT to baseline on all 33
    # TUs, even in -o combos -- measured 2026-06-15) are DROPPED: -ei, all
    # -fp*, -om/-on/-op/-oz, -r, -zp1 (== baseline default pack), -zdp/-zff/
    # -zfp/-zg/-zgf/-zgp/-zl/-zld.  Debug dimension is SETTLED -d1 (PS used
    # only -d1), so -d2/-d3/-d1+/-ez are dropped too.  This shrinks the -o
    # letter pool from 17 -> 13 (drop m,n,p,z) and removes ~25 inert configs.
    # --- single-dimension deviations (only flags that change bytes) ---
    for cc in ["-3r", "-3s", "-4s", "-5r", "-5s"]:
        add(BASE.replace("-4r", cc))
    for f in ["-j", "-ri", "-sg", "-st",
              "-zp2", "-zp4", "-zp8", "-zc", "-zm", "-zu", "-zdf",
              "-en", "-ee"]:
        add(BASE + " " + f)
    add(BASE.replace(" -d1", ""))          # no debug (confirms -d1 neutrality)
    add(BASE.replace(" -s", ""))           # no stack-check
    # --- -o subsets size 1..4 (canonical order); pool = changing letters ---
    OLET = "acdefilorstux"                  # dropped inert m,n,p,z
    for k in (1, 2, 3, 4):
        for c in combinations(OLET, k):
            add(BASE + " -o" + "".join(c))
    # --- order-sensitivity: ALL permutations of {d,s,t,x} subsets (proven
    #     non-idempotent: -od clears, -os/-ot/-ox set OptSize/enable), each
    #     also crossed with one idempotent letter at start/end ---
    ORD = "dstx"
    IDEM = "iu"                             # m,n,p,z inert -> dropped
    for k in (2, 3, 4):
        for c in combinations(ORD, k):
            for perm in set(permutations(c)):
                p = "".join(perm)
                add(BASE + " -o" + p)
                for x in IDEM:
                    add(BASE + " -o" + x + p)   # idem before
                    add(BASE + " -o" + p + x)   # idem after
    # --- pairwise across dims (curated breaking + neutral singletons) ---
    singles = ["-j", "-ri", "-zp2", "-sg", "-st",
               "-3s", "-4s", "-oa", "-oc", "-oe", "-of", "-ol", "-or",
               "-os", "-ot", "-ox", "-oi", "-zc", "-zu"]
    for a, b in combinations(singles, 2):
        add(BASE + " " + a + " " + b)
    # --- structural cross-product: callconv x char x packing (debug=-d1) ---
    for cc in ["-4r", "-3r", "-4s", "-5r"]:
        for ch in ["", "-j", "-ri"]:
            for dbg in ["-d1", ""]:
                for zp in ["", "-zp2"]:
                    parts = ["-bt=dos -mf", cc, "-s"]
                    if dbg:
                        parts.append(dbg)
                    if ch:
                        parts.append(ch)
                    if zp:
                        parts.append(zp)
                    add(" ".join(parts))
    out = [(cf.replace("-bt=dos -mf -4r -s -d1", "BASE").strip() or "BASE", cf)
           for cf in cfgs]
    return out


def _exact(diffs):
    """#byte-exact funcs from a {fn:ndiff} dict."""
    return sum(1 for d in diffs.values() if d == 0)


def main():
    configs = gen_configs()
    print(f"{len(configs)} unique flag configs x {len(TUS)} TUs "
          f"= {len(configs)*len(TUS)} compiles, {WORKERS}w", flush=True)
    # full per-function diff data, streamed to JSONL (granular replacement
    # for the .obj: baseline diffs + per-config DELTAS vs baseline)
    fd = open("/tmp/flag_full_funcdiffs.jsonl", "w")
    fdlock = threading.Lock()

    # baseline per-function diffs
    base = {}
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        fs = {ex.submit(func_diffs, tu, BASE): tu for tu in TUS}
        for f in as_completed(fs):
            base[fs[f]] = f.result() or {}
    base_exact = {t: _exact(base[t]) for t in TUS}
    base_total = sum(base_exact.values())
    fd.write(json.dumps({"cfg": "BASE", "baseline": True,
                         "diffs": {t: base[t] for t in TUS}}) + "\n")
    print(f"BASELINE total byte-exact = {base_total}", flush=True)

    results = {}
    from collections import defaultdict
    flip_log = defaultdict(list)   # 'tu:fn' -> [configs that flip it to byte-exact]
    lock = threading.Lock(); t0 = time.time(); n = 0; best = base_total; best_cfg = "BASE"
    per_tu_best = {t: (base_exact[t], "BASE") for t in TUS}
    CH = 80
    for ci in range(0, len(configs), CH):
        chunk = configs[ci:ci + CH]
        cur = {l: {} for l, _ in chunk}; pend = {l: len(TUS) for l, _ in chunk}
        with ThreadPoolExecutor(max_workers=WORKERS) as ex:
            futs = [ex.submit(lambda l, cf, tu: (l, tu, func_diffs(tu, cf)), l, cf, tu)
                    for l, cf in chunk for tu in TUS]
            for fut in as_completed(futs):
                l, tu, diffs = fut.result()
                with lock:
                    cur[l][tu] = diffs; pend[l] -= 1; n += 1
                    if pend[l] == 0:
                        cf = dict(chunk)[l]
                        failed = [t for t in TUS if cur[l][t] is None]
                        per_tu_ex = {}; deltas = {}; gained = []; lost = []
                        tot = 0
                        for t in TUS:
                            dd = cur[l][t]
                            if dd is None:
                                per_tu_ex[t] = base_exact[t]
                                tot += base_exact[t]
                                continue
                            per_tu_ex[t] = _exact(dd)
                            tot += per_tu_ex[t]
                            d = {fn: dd[fn] for fn in dd if base[t].get(fn) != dd[fn]}
                            if d:
                                deltas[t] = d
                            for fn in dd:
                                bd = base[t].get(fn)
                                if bd is not None and bd > 0 and dd[fn] == 0:
                                    gained.append(f"{t}:{fn.rstrip('_')}")
                                elif bd == 0 and dd[fn] > 0:
                                    lost.append(f"{t}:{fn.rstrip('_')}")
                            if per_tu_ex[t] > per_tu_best[t][0]:
                                per_tu_best[t] = (per_tu_ex[t], l)
                        results[l] = {"cf": cf, "total": tot, "failed": failed,
                                      "per_tu": per_tu_ex, "gained": gained, "lost": lost}
                        with fdlock:
                            fd.write(json.dumps({"cfg": l, "cf": cf, "total": tot,
                                                 "gained": gained, "lost": lost,
                                                 "deltas": deltas}) + "\n")
                            fd.flush()
                        # SURFACE every flip-to-exact (the lever signal)
                        if gained:
                            for g in gained:
                                flip_log[g].append(l)
                            print(f"  FLIP {l:20s} +{len(gained)}/-{len(lost)} "
                                  f"(tot {tot}/{base_total})  GAINED: {gained}", flush=True)
                        if tot > best:
                            best = tot; best_cfg = l
        print(f"  [{ci//CH+1}/{(len(configs)+CH-1)//CH}] {n} compiles "
              f"{time.time()-t0:.0f}s  best={best} ({best_cfg})", flush=True)
    fd.close()
    json.dump({"base_total": base_total, "base_exact": base_exact,
               "per_tu_best": per_tu_best, "results": results},
              open("/tmp/flag_full_results.json", "w"))
    ranked = sorted(results.items(), key=lambda kv: -kv[1]["total"])
    print(f"\n=== TOP 15 configs by GLOBAL total byte-exact (baseline={base_total}) ===", flush=True)
    for l, r in ranked[:15]:
        print(f"  {r['total']:4d}  {l:28s} {r['cf']}", flush=True)
    print(f"\n=== PER-TU BEST config (>baseline only) ===", flush=True)
    for t in TUS:
        bn, bl = per_tu_best[t]
        if bl != "BASE":
            print(f"  {t:10s} baseline {base_exact[t]} -> {bn} ({bl}: {results[bl]['cf']})", flush=True)
    if all(bl == "BASE" for bn, bl in per_tu_best.values()):
        print("  (every TU's best is BASELINE)", flush=True)
    # THE LEVER SIGNAL: every residue function that flips to byte-exact under
    # some flag, with the configs that do it (fewer configs = more specific).
    print(f"\n=== FLIP-TO-EXACT LEVERS ({len(flip_log)} residue fns flip under >=1 flag) ===", flush=True)
    flips = sorted(flip_log.items(), key=lambda kv: len(kv[1]))
    for g, cfgs in flips:
        # collapse configs to their distinguishing flag tokens
        toks = sorted({t for c in cfgs for t in c.split()})
        print(f"  {g:42s} by {len(cfgs):4d} cfg(s); flags: {toks[:8]}", flush=True)
    json.dump({"flip_log": {g: cfgs for g, cfgs in flip_log.items()}},
              open("/tmp/flag_full_flips.json", "w"))
    print(f"\nDONE {n} compiles {time.time()-t0:.0f}s; best={best} ({best_cfg})", flush=True)


if __name__ == "__main__":
    main()

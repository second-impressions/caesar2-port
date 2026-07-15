#!/usr/bin/env python3
"""Flag survey, vs-PS metric.

For each flag config, compile the DIFFING TUs and count how many
functions become byte-exact vs PS.EXE (after fixup masking).  Reports
configs that flip residue functions to exact (the real signal), even if
they perturb a few currently-exact TUs.

Usage: python3 tools/flag_survey_vsps.py <mode>
  o13 / o14  : -o subsets size 1..3 / 1..4
  single     : curated single-flag list (incl. the 'fixed' ones)
"""
import sys, os, time, threading, tempfile, shutil, json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from itertools import combinations

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ".")
from c2.commands.compiler_id import (
    _strip_stub_bodies, _run_in_container, _load_exe_functions,
    _exe_func_bytes,
)
from c2.commands.decomp_verify import _parse_annotations, _rel_call_jmp_disp_mask
from c2.parsers.omf import parse_obj_functions


def _diff_masked(a, af, b, bf):
    """Fixup- AND rel32-branch-displacement-masked diff (matches
    decomp-verify; compiler-id's _diff_bytes alone leaves layout-dependent
    call/jmp displacements unmasked -> phantom diffs)."""
    n = min(len(a), len(b)); extra = abs(len(a) - len(b))
    mask = set(af) | set(bf) | _rel_call_jmp_disp_mask(a[:n]) | _rel_call_jmp_disp_mask(b[:n])
    return sum(1 for i in range(n) if i not in mask and a[i] != b[i]) + extra

IMAGE = "localhost/watcom-10.0a-wibo"
INC = Path("decomp/include")
BASE = "-bt=dos -mf -4r -s -d1"
WORKERS = int(os.environ.get("SURVEY_WORKERS", "6"))
INC_HEADERS = [(h.name, h.read_text()) for h in INC.glob("*.h")]

# the diffing TUs (lowest reproduction rate) — where flipping fns to exact matters
DIFF_TUS = ["evolver", "map", "battle", "int_c2", "landfill",
            "pm_map1", "pm_map2", "pm_map3", "controls"]
# a few fully-exact TUs as a guardrail (how badly does the flag break them)
GUARD_TUS = ["common", "c2", "loadsave", "web"]
ALL_TUS = DIFF_TUS + GUARD_TUS

print("loading PS.EXE ...", flush=True)
CODE, FIXUPS, CODE_SYMS, NAME2ADDR = _load_exe_functions(
    Path("data/PS.EXE"), Path("data/out/symbols.json"))

# per-TU: {func_name: (ps_bytes, ps_fix)} for FUNCTION-annotated fns
PS_FN = {}
for tu in ALL_TUS:
    addrs, _ = _parse_annotations(Path(f"decomp/src/{tu}.c"))
    d = {}
    for s in CODE_SYMS:
        if s["address"] in addrs:
            pb, pf = _exe_func_bytes(s["address"], CODE, FIXUPS, CODE_SYMS)
            if pb is not None:
                d[s["raw_name"]] = (pb, pf)
    PS_FN[tu] = d
print("PS funcs per TU:", {t: len(d) for t, d in PS_FN.items()}, flush=True)


def _compile_once(tu, cflags):
    cf_ = Path(f"decomp/src/{tu}.c")
    work = Path(tempfile.mkdtemp(prefix="vp_"))
    try:
        (work / cf_.name).write_text(_strip_stub_bodies(cf_.read_text()))
        for n, t in INC_HEADERS:
            (work / n).write_text(t)
        ok, _ = _run_in_container(work, IMAGE,
                                  f"wcc386 {cflags} -fo={cf_.stem}.obj {cf_.name}")
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


def exact_set(tu, cflags):
    """Set of fn names byte-exact vs PS, or None if the compile never succeeded.
    Retries + validates the parse covers most expected fns (guards against
    flaky/partial parallel compiles)."""
    want = set(PS_FN[tu])
    need = max(1, int(0.8 * len(want)))  # expect >=80% of annotated fns present
    by = None
    for _ in range(4):
        by = _compile_once(tu, cflags)
        if by is not None and len(want & set(by)) >= need:
            break
        by = None
        time.sleep(0.2)
    if by is None:
        return None
    return {fn for fn, (pb, pf) in PS_FN[tu].items()
            if fn in by and _diff_masked(pb, pf, *by[fn]) == 0}


def build(configs, outpath):
    # baseline exact sets
    base = {}
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        fs = {ex.submit(exact_set, tu, BASE): tu for tu in ALL_TUS}
        for f in as_completed(fs):
            base[fs[f]] = f.result() or set()
    base_diff = sum(len(base[t]) for t in DIFF_TUS)
    base_guard = sum(len(base[t]) for t in GUARD_TUS)
    print(f"BASELINE exact funcs: diff-TUs={base_diff} guard-TUs={base_guard}", flush=True)
    for t in DIFF_TUS:
        print(f"    {t}: {len(base[t])}/{len(PS_FN[t])} exact", flush=True)

    results = {}
    lock = threading.Lock(); t0 = time.time(); n = 0; hits = []
    CH = 100

    def work(lbl, cf, tu):
        return lbl, tu, exact_set(tu, cf)

    for ci in range(0, len(configs), CH):
        chunk = configs[ci:ci + CH]
        cur = {l: {} for l, _ in chunk}
        pend = {l: len(ALL_TUS) for l, _ in chunk}
        with ThreadPoolExecutor(max_workers=WORKERS) as exr:
            futs = [exr.submit(work, l, cf, tu) for l, cf in chunk for tu in ALL_TUS]
            for fut in as_completed(futs):
                lbl, tu, es = fut.result()
                with lock:
                    cur[lbl][tu] = es  # None = compile failed (excluded)
                    pend[lbl] -= 1; n += 1
                    if pend[lbl] == 0:
                        c = cur[lbl]
                        failed = [t for t in ALL_TUS if c[t] is None]
                        # gained/lost over ALL TUs that compiled (diff + guard)
                        gained, lost, guard_lost = [], [], 0
                        for t in ALL_TUS:
                            if c[t] is None:
                                continue
                            for fn in (c[t] - base[t]):
                                gained.append(f"{t}:{fn.rstrip('_')}")
                            for fn in (base[t] - c[t]):
                                lost.append(f"{t}:{fn.rstrip('_')}")
                                if t in GUARD_TUS:
                                    guard_lost += 1
                        cf = dict(chunk)[lbl]
                        net = len(gained) - len(lost)
                        per_tu = {t: (len(c[t]) if c[t] is not None else None)
                                  for t in ALL_TUS}
                        results[lbl] = {"cf": cf, "gained": gained, "lost": lost,
                                        "failed_tus": failed, "net": net,
                                        "guard_lost": guard_lost,
                                        "per_tu_exact": per_tu}
                        # only worth printing if it's a NET improvement overall
                        if net > 0 or (gained and guard_lost == 0):
                            hits.append(lbl)
                            print(f"  >>> {lbl:14s} {cf}  NET{net:+d} "
                                  f"(+{len(gained)} -{len(lost)}, guardLost={guard_lost})"
                                  + (f" [fail:{failed}]" if failed else "")
                                  + f"  GAINED: {gained}", flush=True)
        print(f"  [{ci//CH+1}/{(len(configs)+CH-1)//CH}] {n} compiles "
              f"{time.time()-t0:.0f}s  {len(hits)} configs gained fns", flush=True)
    json.dump({"baseline": {"diff_ex": base_diff, "guard_ex": base_guard,
                            "per_tu": {t: sorted(base[t]) for t in ALL_TUS},
                            "per_tu_n": {t: len(base[t]) for t in ALL_TUS}},
               "results": results}, open(outpath, "w"))
    print(f"DONE {n} compiles {time.time()-t0:.0f}s; "
          f"{len(hits)} configs flipped >=1 residue fn to exact", flush=True)
    # PER-TU best config (max byte-exact funcs), vs baseline
    print("\n=== PER-TU BEST FLAG CONFIG (max byte-exact funcs vs PS) ===", flush=True)
    for t in ALL_TUS:
        bestlbl, bestn = "BASELINE", len(base[t])
        for lbl, r in results.items():
            c = r["per_tu_exact"].get(t)
            if c is not None and c > bestn:
                bestn, bestlbl = c, lbl
        tot = len(PS_FN[t])
        mark = "" if bestlbl == "BASELINE" else f"  <== {results[bestlbl]['cf']}"
        print(f"  {t:10s} baseline {len(base[t])}/{tot}  ->  best {bestn}/{tot} "
              f"({bestlbl}){mark}", flush=True)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "o13"
    OLET = "acdefilmnoprstuxz"
    if mode in ("o13", "o14"):
        ks = (1, 2, 3) if mode == "o13" else (1, 2, 3, 4)
        subs = [''.join(c) for k in ks for c in combinations(OLET, k)]
        configs = [("o=" + s, BASE + " -o" + s) for s in subs]
        out = f"/tmp/vsps_{mode}.json"
    elif mode == "single":
        flags = ["-j", "-ri", "-ei", "-3s", "-4s", "-5s", "-fpi", "-oc", "-oi",
                 "-or", "-os", "-ot", "-oz", "-sg", "-st", "-r", "-zp1", "-zp2",
                 "-zc", "-zu", "-d2", "-en", "-ee", "-oa", "-oe", "-of"]
        configs = [(f, BASE + " " + f) for f in flags]
        out = "/tmp/vsps_single.json"
    else:
        print("unknown mode"); return
    print(f"mode={mode}: {len(configs)} configs x {len(ALL_TUS)} TUs "
          f"= {len(configs)*len(ALL_TUS)} compiles, {WORKERS}w", flush=True)
    build(configs, out)


if __name__ == "__main__":
    main()

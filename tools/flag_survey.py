#!/usr/bin/env python3
"""Compiler-flag survey: find flag configs neutral on byte-exact TUs but
active on the residue (candidate "missing levers").

Compiles each probe TU with baseline vs a flag config (isolated podman
runs), diffs per-function (fixup-masked), archives every .obj.

Usage: python3 tools/flag_survey.py <mode> [args]
  mode=o13     : all -o subsets size 1..3
  mode=o14     : all -o subsets size 1..4
  mode=single  : single-flag sweep (a curated list)
  mode=neutral : subsets of the neutral -o letters only (imnopuz) 1..4
"""
import sys, os, time, threading, tempfile, shutil, hashlib, json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from itertools import combinations

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ".")
from c2.commands.compiler_id import _strip_stub_bodies, _run_in_container
from c2.parsers.omf import parse_obj_functions

IMAGE = "localhost/watcom-10.0a-wibo"
INC = Path("decomp/include")
BASE = "-bt=dos -mf -4r -s -d1"
WORKERS = int(os.environ.get("SURVEY_WORKERS", "6"))
INC_HEADERS = [(h.name, h.read_text()) for h in INC.glob("*.h")]

EXACT_TUS = ["c2", "common", "loadsave", "message", "pump", "refresh", "smacker", "web"]
RESIDUE_TUS = ["evolver", "map", "battle", "int_c2"]
ALL_PROBE = EXACT_TUS + RESIDUE_TUS

ARCHIVE = Path("/tmp/flag_survey_objs"); OH = ARCHIVE / "ohunt"
OH.mkdir(parents=True, exist_ok=True)
_man = []; _ml = threading.Lock()


def _diff(a, af, b, bf):
    n = min(len(a), len(b)); d = abs(len(a) - len(b))
    for i in range(n):
        if i in af or i in bf:
            continue
        if a[i] != b[i]:
            d += 1
    return d


def compare(base, var):
    if not isinstance(var, dict):
        return -1
    return sum(1 for nm, (b, fx) in base.items()
               if nm in var and _diff(b, fx, *var[nm]) > 0)


def compile_arch(tu, cflags):
    cf_ = Path(f"decomp/src/{tu}.c")
    work = Path(tempfile.mkdtemp(prefix="oh_"))
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
        dest = OH / f"{tu}__{hashlib.md5((tu+chr(124)+cflags).encode()).hexdigest()[:12]}.obj"
        shutil.copy2(obj, dest)
        with _ml:
            _man.append((dest.name, tu, cflags))
        try:
            return {nm: (b, fx) for nm, b, fx in parse_obj_functions(dest)}
        except Exception:
            return "ERR"
    finally:
        shutil.rmtree(work, ignore_errors=True)


def build_baselines():
    bl = {}
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        fs = {ex.submit(compile_arch, tu, BASE): tu for tu in ALL_PROBE}
        for f in as_completed(fs):
            bl[fs[f]] = f.result()
    return bl


def survey(configs, baselines, outpath):
    agg = {l: {"cf": cf, "ebrk": 0, "etus": set(), "rchg": 0, "rtus": set(), "fail": 0}
           for l, cf in configs}
    lock = threading.Lock(); t0 = time.time(); n = 0; cand = []
    total = len(configs) * len(ALL_PROBE)

    def work(lbl, cf, tu):
        return lbl, tu, compare(baselines[tu], compile_arch(tu, cf))

    CH = 120
    for ci in range(0, len(configs), CH):
        chunk = configs[ci:ci + CH]
        pend = {l: len(ALL_PROBE) for l, _ in chunk}
        with ThreadPoolExecutor(max_workers=WORKERS) as ex:
            futs = [ex.submit(work, l, cf, tu) for l, cf in chunk for tu in ALL_PROBE]
            for fut in as_completed(futs):
                lbl, tu, nch = fut.result()
                with lock:
                    a = agg[lbl]; pend[lbl] -= 1; n += 1
                    if nch < 0:
                        a["fail"] += 1
                    elif nch > 0:
                        if tu in EXACT_TUS:
                            a["ebrk"] += nch; a["etus"].add(tu)
                        else:
                            a["rchg"] += nch; a["rtus"].add(tu)
                    if pend[lbl] == 0 and a["ebrk"] == 0 and a["rchg"] > 0:
                        cand.append(lbl)
                        print(f"  *** CANDIDATE {lbl}  {a['cf']}  "
                              f"res:{a['rchg']}fn {sorted(a['rtus'])}", flush=True)
        print(f"  [{ci//CH+1}/{(len(configs)+CH-1)//CH}] {n}/{total} "
              f"{time.time()-t0:.0f}s  {len(cand)} cand", flush=True)
    json.dump({l: {"cf": a["cf"], "ebrk": a["ebrk"], "etus": sorted(a["etus"]),
                   "rchg": a["rchg"], "rtus": sorted(a["rtus"]), "fail": a["fail"]}
               for l, a in agg.items()}, open(outpath, "w"))
    print(f"DONE {n} compiles {time.time()-t0:.0f}s; candidates: {cand}", flush=True)
    return agg, cand


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "o13"
    OLET = "acdefilmnoprstuxz"
    if mode == "o13":
        subs = [''.join(c) for k in (1, 2, 3) for c in combinations(OLET, k)]
        configs = [("o=" + s, BASE + " -o" + s) for s in subs]
        out = "/tmp/ohunt_1_3.json"
    elif mode == "o14":
        subs = [''.join(c) for k in (1, 2, 3, 4) for c in combinations(OLET, k)]
        configs = [("o=" + s, BASE + " -o" + s) for s in subs]
        out = "/tmp/ohunt_1_4.json"
    elif mode == "neutral":
        NL = "imnopuz"
        subs = [''.join(c) for k in range(1, len(NL) + 1) for c in combinations(NL, k)]
        configs = [("o=" + s, BASE + " -o" + s) for s in subs]
        out = "/tmp/ohunt_neutral.json"
    else:
        print("unknown mode"); return
    print(f"mode={mode}: {len(configs)} configs x {len(ALL_PROBE)} TUs "
          f"= {len(configs)*len(ALL_PROBE)} compiles, {WORKERS} workers", flush=True)
    print("building baselines...", flush=True)
    bl = build_baselines()
    print("baselines:", {t: (len(v) if isinstance(v, dict) else v)
                         for t, v in bl.items()}, flush=True)
    survey(configs, bl, out)
    with open("/tmp/flag_survey_manifest.jsonl", "w") as f:
        for name, tu, cf in _man:
            f.write(json.dumps({"obj": name, "tu": tu, "cflags": cf}) + "\n")
    print(f"archived {len(_man)} objs -> {OH}", flush=True)


if __name__ == "__main__":
    main()

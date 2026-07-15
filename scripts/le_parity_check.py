"""Corpus-wide: compare the sandbox LE-linked compile_scratch byte_diff
against the real c2 decomp-verify (cached verify.json) for EVERY function.

For each function:
  - real byte_diff  <- cached .c2-cache/verify.json (the ground truth)
  - sandbox byte_diff <- compose a sandbox, run engine verify (LE carve)
  - record match / mismatch

Outputs .c2-runs/le-parity/records.jsonl + report.txt
"""
import json, sys, time, traceback
from pathlib import Path
REPO = Path("/home/simon/git/caesar2")
sys.path.insert(0, str(REPO))

from c2.decompile._engine.project import ProjectConfig
from c2.decompile._engine.runs import compose as engine_compose
from c2.decompile._engine.verify import verify as engine_verify

project = ProjectConfig.load(REPO, target="watcom")
tc = project.toolchain()

# Real ground truth: cached verify.json
real = {f["name"]: f for f in json.load(open(REPO/".c2-cache/verify.json"))["functions"]}

# Only check functions present in verify.json (the real oracle set;
# excludes AIL/CRT 3rd-party which we never decompile).
names = sorted(real.keys())

OUT = REPO / ".c2-runs" / "le-parity"
OUT.mkdir(parents=True, exist_ok=True)
RECORDS = OUT / "records.jsonl"
REPORT = OUT / "report.txt"

# resume
done = set()
if RECORDS.exists():
    for ln in RECORDS.read_text().splitlines():
        ln = ln.strip()
        if ln:
            try: done.add(json.loads(ln)["name"])
            except: pass

PER_FN_TIMEOUT = 90
todo = [n for n in names if n not in done]
print(f"functions: {len(names)} total, {len(done)} done, {len(todo)} to run", flush=True)

t0 = time.time()
for i, name in enumerate(todo, 1):
    rec = {"name": name}
    try:
        rf = real.get(name)
        rec["real_byte_diff"] = rf["diff_byte_count"] if rf else None
        rec["real_exact"] = (rf and rf["diff_byte_count"] == 0)
        _rd = Path(REPO / ".c2-runs" / "le-test" / name)
        _rd.parent.mkdir(parents=True, exist_ok=True)
        run_dir = engine_compose(project, name, blank=False, out_dir=_rd)
        comp = tc.compile_scratch(run_dir, name)
        rec["sandbox_build_ok"] = comp.ok
        if not comp.ok:
            rec["sandbox_byte_diff"] = None
            rec["error"] = (comp.stderr or "")[:200]
        else:
            vr = engine_verify(project, run_dir, diff=False, target="watcom")
            rec["sandbox_byte_diff"] = vr.byte_diff
            rec["sandbox_exact"] = vr.exact
            rec["your_size"] = len(comp.function_bytes) if comp.function_bytes else 0
            rec["target_size"] = rf["size"] if rf else None
    except Exception as e:
        rec["error"] = f"{type(e).__name__}: {e}"[:300]
    finally:
        try: tc.stop_warm_container(run_dir)
        except: pass
        try:
            import shutil
            shutil.rmtree(_rd, ignore_errors=True)
        except: pass

    # classify
    rb = rec.get("real_byte_diff"); sb = rec.get("sandbox_byte_diff")
    if rb is not None and sb is not None:
        rec["match"] = (rb == sb)
        rec["delta"] = sb - rb
    else:
        rec["match"] = None
        rec["delta"] = None

    with RECORDS.open("a") as f:
        f.write(json.dumps(rec) + "\n")
    if i % 25 == 0 or not rec.get("match", True):
        flag = "" if rec.get("match") else "  <<< MISMATCH"
        print(f"[{i}/{len(todo)} {time.time()-t0:.0f}s] {name:30} real={rb} sandbox={sb}{flag}", flush=True)

print(f"\nDONE in {time.time()-t0:.0f}s", flush=True)

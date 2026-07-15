#!/usr/bin/env python3
"""frx emitted-name audit -- the byte-pair-orientation regression gate.

WHAT THIS GUARDS (discovered 2026-07-11, the action byte-rotation hunt):
the hw_reg_set byte-pair orientation is H = the LOW bit of each pair
(AH=0x1, AL=0x2, BH=0x4, BL=0x8, CH=0x10, CL=0x20, DH=0x40, DL=0x80).
Several tools carried the pairwise-SWAPPED names for B/C/D (bl<->bh,
cl<->ch, dl<->dh):

  * watcom10.0a tools/reglists.py REG_NAME (never got the 2026-06-10 fix)
  * watcom10.0a tools/rover_divergence.py NAME (re-introduced 2026-06-14;
    rover_fit imports from it) -- every byte-class k/lever they reported
    before 2026-07-11 was inverted on the PS-parse side
  * c2/commands/rover_hints.py _NAME (the live `Rover:` hint engine)

The sim<->frx validation (7028/7028) could NOT catch this: both sides go
through the same mask->NAME table, so a systematic swap cancels.  Only an
EMITTED-BYTES cross-check exposes it -- which needs the frx ground-truth
probe (FindRegister FOUND-return) paired with the fr stream, parsed since
c2.regalloc.trace v55.

THE CHECK: for every byte-exact function in the target TU(s), pair
routine['fr'] with routine['frx'] (done at parse time -> fr['truth']),
collect the truth names of byte-class CONST-STORE picks (rescls==1 --
the 2026-07-11 fr site-identity extension), and require every VISIBLE
byte scratch pick in the function's disasm (xor R,R / mov R,imm followed
by mov [g],R) to be covered by the truth multiset.  On a byte-exact
function PS bytes == RC bytes, so this validates the naming against the
compiler's actual output.  A pairwise-swapped table fails immediately on
any function using D/B/C bytes.

Result 2026-07-11 (action.c TU): 46 functions with visible byte picks,
46 OK, 0 bad.

Usage:  uv run python docs/codegen-experiments/frx-emitted-name-audit.py [file.c ...]
        (default: action.c)
"""
import re
import subprocess
import sys
from collections import Counter, deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from c2 import regalloc
from c2.commands.decomp_verify import PS_CFLAGS  # noqa: F401  (flag SoT)
from c2.regalloc.reglists import REG_NAME

SRC = Path(__file__).resolve().parents[2] / "decomp" / "src"
INCLUDE = Path(__file__).resolve().parents[2] / "decomp" / "include"


def cls_of_tc(tc):
    return {0: "byte", 1: "byte", 2: "word", 3: "word",
            4: "dword", 5: "dword"}.get(tc)


def trace_tu(cfile: Path):
    files = {"TARGET.C": cfile.read_text(errors="replace")}
    for h in INCLUDE.glob("*.h"):
        files[h.name.upper()] = h.read_text(errors="replace")
    return regalloc.trace_compile(files, main="TARGET.C")


def visible_byte_picks(fn: str) -> list:
    out = subprocess.run(["uv", "run", "c2", "disasm", fn],
                         capture_output=True, text=True, timeout=180).stdout
    lines = [re.sub(r"\s+", " ", ln) for ln in out.splitlines()]
    vis = []
    for j, ln in enumerate(lines):
        m = re.search(r"(xor ([a-d][lh]), \2|mov ([a-d][lh]), 0x?[0-9a-f]+$)", ln)
        if not m:
            continue
        reg = m.group(2) or m.group(3)
        for jj in (j + 1, j + 2):
            if jj < len(lines) and re.search(
                    rf"mov byte ptr \[0x[0-9a-f]+\], {reg}\b", lines[jj]):
                vis.append(reg)
                break
    return vis


def main(tus):
    import json
    vj = Path(__file__).resolve().parents[2] / ".c2-cache" / "verify.json"
    doc = json.loads(vj.read_text())
    ok = bad = skip = 0
    for tu in tus:
        cfile = SRC / tu
        td = trace_tu(cfile)
        src_lines = cfile.read_text(errors="replace").splitlines()
        # function name -> body line range (cheap: def line .. next def)
        exact = [f for f in doc["functions"]
                 if f.get("file", "").endswith(tu) and f.get("diff_byte_count") == 0]
        for f in exact:
            nm = f["name"]
            # locate body lines
            lo = next((i + 1 for i, ln in enumerate(src_lines)
                       if re.match(rf"\w[\w\s\*]*\b{re.escape(nm)}\s*\(", ln)), None)
            if lo is None:
                continue
            hi = lo + 400
            rt = None
            for r in td["routines"]:
                fr = r.get("fr", [])
                if fr and sum(1 for x in fr
                              if x.get("line") and lo <= x["line"] <= hi) >= 1:
                    rt = r
                    break
            if rt is None:
                continue
            truth = [x.get("truth") for x in rt.get("fr", [])
                     if x.get("truth") and x.get("rescls") == 1
                     and cls_of_tc(x["type_class"]) == "byte"]
            vis = visible_byte_picks(nm)
            if not vis:
                skip += 1
                continue
            if Counter(vis) - Counter(truth):
                bad += 1
                print(f"  BAD {nm}: visible {vis} truth {truth}")
            else:
                ok += 1
    print(f"ok: {ok}  bad: {bad}  no-visible: {skip}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or ["action.c"]))

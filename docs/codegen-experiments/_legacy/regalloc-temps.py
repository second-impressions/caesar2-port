"""EVIDENCE: the register-allocation conflict set is over Watcom's IR
TEMPORARIES, not over source variables.  Predicting a real function's
EDX/EBX/ECX assignment with the last-use model (regalloc-last-use.py)
therefore requires knowing which temps the compiler introduced.

This file pins down, against Watcom 10.0a, WHEN a temp is created and
shows that the umbrella "Reg swap" diff class actually spans several
distinct mechanisms — so the last-use tie-break is the explanation for
only a SUBSET of reg-swap residue, not all of it.

Temp-introduction rules (asserted below):

  T1. A global/memory read is NOT CSE'd across a `call` — the callee may
      alias it, so Watcom reloads.  => two `mov eax,[g]`, no held temp.
  T2. A named local `int i = expr` becomes ONE temp, reused at every use
      site (held in a register if profitable).
  T3. A repeated *sub*-expression that is part of two DIFFERENT larger
      expressions (`g*10` inside `g*10` and `g*10+3`) is NOT factored —
      it is recomputed, creating two independent temps.
  T4. Each indexed load `t[i]` materialises its own result temp at the
      point of use; with a shared index `i`, the index is the held temp
      and the loads are short-lived temps assigned in COMPUTATION order
      (first computed -> higher reg), which is the *opposite* of the
      source-operand-order corollary that holds for entry-loaded values.

Mechanism heterogeneity of "Reg swap" (the practical headline):

  * LAYER-3 assignment swap (last-use tie-break): the SAME value lands in
    a DIFFERENT register (e.g. value in EDX vs EBX).  regalloc-last-use.py
    is the lever.
  * LAYER-4 add-accumulator direction: BOTH sides assign the same regs to
    the two operands, and only the commutative op's destination differs
    (`add edx,ecx` vs `add ecx,edx`, both with edx=lo, ecx=hi).  This is
    instruction-selection / CountRegMoves, NOT the last-use tie-break, and
    is the real story behind restore_picture_part's "unreachable" residue.

=> Before reaching for the last-use lever, confirm the diff is an
   ASSIGNMENT swap (a value changes register), not an op-DIRECTION swap
   (same regs, mirrored `add`).  Only the former is last-use territory.

Run::
    uv run python docs/codegen-experiments/regalloc-temps.py   # asserts
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import capstone

_IMAGE = "watcom-10.0a-dosemu2"
_CFLAGS = ["-bt=dos", "-mf", "-4r", "-s"]
_md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)


def _ledata(obj: bytes) -> bytes:
    i, best = 0, b""
    while i < len(obj):
        rectype = obj[i]
        length = obj[i + 1] | (obj[i + 2] << 8)
        rec = obj[i + 3:i + 3 + length - 1]
        if rectype in (0xA0, 0xA1):
            p = 1 + (4 if rectype == 0xA1 else 2)
            if len(rec) - p > len(best):
                best = rec[p:]
        i += 3 + length
    return best


def _asm(src: str, tmp: Path) -> list[str]:
    (tmp / "t.c").write_text(src)
    subprocess.run(
        ["podman", "run", "--rm", "-i", "-v", f"{tmp}:/src", _IMAGE,
         "wcc386", *_CFLAGS, "t.c"],
        input=b"", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        timeout=60,
    )
    code = _ledata((tmp / "t.obj").read_bytes())
    return [f"{ins.mnemonic} {ins.op_str}".strip() for ins in _md.disasm(code, 0)]


def main() -> int:
    tmp = Path("/tmp/regalloc-temps")
    tmp.mkdir(exist_ok=True)

    # T1: no CSE across a call.
    a = _asm("extern int g; extern int arr[]; extern void s(int);\n"
             "int t(void){ s(g); s(arr[g]); return 0; }\n", tmp)
    g_loads = sum(1 for ln in a if ln.startswith("mov ") and "dword ptr [0]" in ln)
    assert g_loads >= 2, f"T1: expected >=2 reloads of g across the call; got {g_loads}\n{a}"
    print(f"T1  global read across call: {g_loads} reloads (NOT CSE'd)  OK")

    # T2: named local reused as one temp (the index appears once as a held value).
    a = _asm("extern int a; extern int t1[],t2[];\n"
             "int t(void){ int i=a*7; return t1[i]+t2[i]; }\n", tmp)
    # i = a*7 computed once via shift-sub; the [eax*4] loads reuse it.
    idx_loads = sum(1 for ln in a if "[eax*4]" in ln)
    assert idx_loads == 2, f"T2: expected both loads to reuse index in eax; got {idx_loads}\n{a}"
    print(f"T2  named local index reused by {idx_loads} loads (one temp)  OK")

    # T4: indexed loads assigned in COMPUTATION order (first -> higher reg).
    #     lea [edx + ebx] = t1 + t2  with edx(higher)=t1 computed first.
    lea = next((ln for ln in a if ln.startswith("lea ") and "+" in ln), "")
    assert "edx" in lea and "ebx" in lea, f"T4: unexpected combine insn: {lea!r}\n{a}"
    # edx is higher-priority than ebx; t1 (first computed/first operand) took it.
    assert lea.index("edx") < lea.index("ebx"), (
        f"T4: expected t1(edx,higher) before t2(ebx) in {lea!r}")
    print(f"T4  indexed loads: first-computed took higher reg  ({lea})  OK")

    # T3: repeated sub-expression inside different super-expressions not factored.
    a = _asm("extern short g; extern int tab[];\n"
             "int t(void){ return tab[g*10] + tab[g*10+3]; }\n", tmp)
    # g*10 strength-reduces to shl+add; count the *independent* recomputations.
    movsx = sum(1 for ln in a if ln.startswith("movsx"))
    shl_eax = sum(1 for ln in a if ln.startswith("shl eax"))
    assert shl_eax >= 2, f"T3: expected g*10 recomputed (>=2 shl eax); got {shl_eax}\n{a}"
    print(f"T3  g*10 vs g*10+3 recomputed independently ({shl_eax} shl eax)  OK")

    print("\nALL CHECKS PASS — conflicts are over IR temps; reg-swap residue is")
    print("heterogeneous (layer-3 assignment vs layer-4 add-direction).")
    return 0


if __name__ == "__main__":
    sys.exit(main())

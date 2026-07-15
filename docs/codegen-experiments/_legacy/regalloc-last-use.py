"""PROOF: for multi-use values, the Watcom 10.0a level-3 tie-break correlates
with LAST-USE order ("dies first wins the better register"), NOT first-use
order.

This refines regalloc-tiebreak.py, whose `store a,b,c,d,e` evidence used
single-use values where first-use == last-use and therefore could not
distinguish the two.

NOTE on the framing: the *fundamental* mechanism is the name-node POINTER
order used by `regalloc.c::ConfBefore` (see `docs/wcc386-re/regalloc-model.md`
§3).  Last-use order is a proxy for that key -- it agrees because UpdateLive
creates conflict nodes as it walks backwards (last-encountered = name-node
allocated earliest = head of equal-savings run).  When the use itself is
pinned by semantics, the lever shifts from "reorder the use" (Rule 28a) to
"reorder the two locals' declaration lines" (Rule 115).  Every assertion
below remains correct for the use-position lever; what Rule 115 added is the
second handle for the residue case.

Mechanism (algorithm structure from the **OW v1 reference checkout**,
~/git/open-watcom/owp4v1copy/bld/cg/c -- NOT 10.0a source, which is not
public; ~5 years younger, used as a reference for the algorithm shape and
confirmed against the 10.0a binary behaviourally):

  * liveinfo.c::UpdateLive walks instructions BACKWARDS
    (`ins = ins->head.prev`) and calls FindConflictNode on each operand.
    A name's conflict_node is therefore CREATED at its first *backward*
    encounter == the name's LAST use in program order.
  * conflict.c::AddConflictNode PREPENDS the new node:
        new->next_conflict = ConfList;  ConfList = new;
    so ConfList ends up ordered by ascending last-use position
    (the value whose last use is earliest sits nearest the head).
  * regalloc.c::SortConflicts sorts by `conf->savings` with a STRICT
    predicate (ConfBefore: c1->savings > c2->savings), and SortList's
    ShellSort never swaps equal keys, so equal-savings nodes keep that
    last-use order.
  * regalloc.c::AssignConflicts walks ConfList head->tail calling
    GiveRegister; the FIRST node processed grabs the higher-priority
    register (DoubleRegs = EAX, EDX, EBX, ECX, ESI, EDI, EBP).

Net: among equal-savings values, the one that DIES FIRST (earliest
last use) gets the higher-priority register.

ACTIONABLE LEVER: to move value X into the higher register, make X's
LAST use come earlier in the statement stream (move the rival's trailing
use later).  Within a single deciding instruction `A op B`, operands are
walked i=0,1, so B's conflict is created last and prepended to the head
=> the LATER operand B takes the higher register.  (Both follow the same
"conflict created last == ConfList head == higher reg" rule.)

Run::
    uv run python docs/codegen-experiments/regalloc-last-use.py   # asserts
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
    """Return the largest LEDATA/LEDATA32 code chunk from an OMF object."""
    i = 0
    best = b""
    while i < len(obj):
        rectype = obj[i]
        length = obj[i + 1] | (obj[i + 2] << 8)
        rec = obj[i + 3:i + 3 + length - 1]
        if rectype in (0xA0, 0xA1):
            p = 1  # skip seg index (1 byte for our tiny single-seg objs)
            p += 4 if rectype == 0xA1 else 2
            if len(rec) - p > len(best):
                best = rec[p:]
        i += 3 + length
    return best


def _compile(src: str, tmp: Path) -> list[str]:
    (tmp / "t.c").write_text(src)
    subprocess.run(
        ["podman", "run", "--rm", "-i", "-v", f"{tmp}:/src", _IMAGE,
         "wcc386", *_CFLAGS, "t.c"],
        input=b"", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        timeout=60,
    )
    code = _ledata((tmp / "t.obj").read_bytes())
    return [f"{ins.mnemonic} {ins.op_str}".strip() for ins in _md.disasm(code, 0)]


def _reg_of_global(asm: list[str], which: str) -> str:
    """Which register receives the n-th `mov rX, dword ptr [0]` load?

    Both globals link at offset 0 here, so we identify them by load order:
    the source declares `int a=ga, b=gb;` -> first load is a, second is b.
    """
    loads = [ln for ln in asm if ln.startswith("mov ") and "dword ptr [0]" in ln]
    idx = 0 if which == "a" else 1
    return loads[idx].split(",")[0].split()[1]


# Priority within DoubleRegs (int class): EAX, EDX, EBX, ECX, ESI, EDI, EBP.
_PRIO = {r: i for i, r in enumerate(
    ["eax", "edx", "ebx", "ecx", "esi", "edi", "ebp"])}


def main() -> int:
    tmp = Path("/tmp/regalloc-last-use")
    tmp.mkdir(exist_ok=True)

    # a: used at positions 1 and 4; b: used at positions 2 and 3.
    #   first-use:  a(1) < b(2)  => a would get the higher reg
    #   last-use:   b(3) < a(4)  => b gets the higher reg
    src_ab = ("extern int ga, gb;\n"
              "int t(void){ int a=ga,b=gb,r=0; r+=a; r+=b; r+=b; r+=a; return r; }\n")
    asm = _compile(src_ab, tmp)
    ra, rb = _reg_of_global(asm, "a"), _reg_of_global(asm, "b")
    # b dies first -> b must be the higher-priority register.
    assert _PRIO[rb] < _PRIO[ra], (
        f"last-use model violated: a={ra} b={rb}; expected b higher\n"
        + "\n".join(asm))
    print(f"[1] a uses(1,4) b uses(2,3): a={ra} b={rb}  -> b (dies first) higher  OK")

    # Symmetric swap: now a dies first.
    src_ba = ("extern int ga, gb;\n"
              "int t(void){ int a=ga,b=gb,r=0; r+=b; r+=a; r+=a; r+=b; return r; }\n")
    asm = _compile(src_ba, tmp)
    ra, rb = _reg_of_global(asm, "a"), _reg_of_global(asm, "b")
    assert _PRIO[ra] < _PRIO[rb], (
        f"last-use model violated: a={ra} b={rb}; expected a higher\n"
        + "\n".join(asm))
    print(f"[2] b uses(1,4) a uses(2,3): a={ra} b={rb}  -> a (dies first) higher  OK")

    # Operand-order corollary on the deciding expression: in `X+Y` the
    # operands are walked i=0,1 in the backward pass, so Y's conflict is
    # created last and prepended to the head => the LATER operand Y takes
    # the higher register.
    asm = _compile(
        "extern int ga, gb; extern void s(int);\n"
        "int t(void){ int a=ga,b=gb; s(a); s(b); return a+b; }\n", tmp)
    ra, rb = _reg_of_global(asm, "a"), _reg_of_global(asm, "b")
    assert _PRIO[rb] < _PRIO[ra], f"return a+b: expected b higher; a={ra} b={rb}"
    asm2 = _compile(
        "extern int ga, gb; extern void s(int);\n"
        "int t(void){ int a=ga,b=gb; s(a); s(b); return b+a; }\n", tmp)
    ra2, rb2 = _reg_of_global(asm2, "a"), _reg_of_global(asm2, "b")
    assert _PRIO[ra2] < _PRIO[rb2], f"return b+a: expected a higher; a={ra2} b={rb2}"
    print(f"[3] return a+b -> b={rb}(hi) ; return b+a -> a={ra2}(hi)  "
          "(later operand takes higher reg)  OK")

    print("\nALL PROOFS PASS — level-3 tie-break is LAST-USE (dies-first) order.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

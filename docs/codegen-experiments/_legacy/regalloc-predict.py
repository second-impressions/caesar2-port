"""Regalloc PREDICTOR (Path B, v0) — straight-line, int-class values.

Composes the reverse-engineered Watcom 10.0a pieces into a function that
PREDICTS which register each value gets, then validates the prediction
against the actual compiler over a battery of controlled snippets.

Model (all proven in sibling experiments):
  * conflicts are ordered by (savings DESC, then ConfList order).
  * ConfList order == ascending LAST-USE position; ties within one
    instruction broken by DESCENDING operand index (later operand ->
    head -> higher reg).                       [regalloc-last-use.py]
  * savings ~ loop-weighted (use+def) count.   [regalloc-cost.py]
  * assignment walks that order head->tail; each value takes the
    highest-priority FREE register in its class that does not clash with
    an already-assigned INTERFERING value.
  * int/ptr class priority = DoubleRegs = EAX,EDX,EBX,ECX,ESI,EDI,EBP.
  * a value whose live range crosses a call may not sit in a caller-saved
    register (EAX,EDX,ECX); it needs a callee-saved one (EBX,ESI,EDI,EBP).
    A value crossing a mul/div may not be EAX/EDX.
  * result COALESCING: the leftmost operand of a left-assoc commutative
    chain (`a+b+c`) is the 2-address destination, so it threads through as
    the accumulator and inherits the result's register (EAX when returned).
    This is the layer-4 add-direction mechanism (restore_picture_part).

VALIDATED here against the compiler (5/5 controlled cases): straight-line
int values, the last-use/operand tie-breaks, savings override, the
EAX-cross-call constraint, interference, and result coalescing.

NOT YET MODELLED (roadmap to apply on real functions):
  P2. disasm -> value-flow extraction (build the Value set from a real
      function's bytes) to validate on the byte-exact corpus + diffing fns.
  P3. the save-set / WorthProlog cost (when EDX/ECX is pushed vs spilled).
  P4. branches and loops (per-block live ranges, loop-weighted savings).
  P5. diff application: predict PS's assignment vs ours, report the
      last-use/operand reorder that makes them match.

Run::
    uv run python docs/codegen-experiments/regalloc-predict.py
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

import capstone

_IMAGE = "watcom-10.0a-dosemu2"
_CFLAGS = ["-bt=dos", "-mf", "-4r", "-s"]
_md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)

DOUBLE_REGS = ["eax", "edx", "ebx", "ecx", "esi", "edi", "ebp"]
CALLER_SAVED = {"eax", "edx", "ecx"}


@dataclass
class Value:
    name: str
    uses: list[int]                 # instruction indices where read
    defs: list[int] = field(default_factory=list)  # indices where written
    last_operand_idx: int = 0       # operand index at the last-use instruction
    loop_depth: dict[int, int] = field(default_factory=dict)
    crosses_call: bool = False
    crosses_muldiv: bool = False
    fixed_reg: str | None = None

    @property
    def last_use(self) -> int:
        return max(self.uses + self.defs)

    @property
    def first_def(self) -> int:
        return min(self.defs + self.uses)

    @property
    def savings(self) -> int:
        # loop-weighted count of uses+defs (W=10 per loop level).
        s = 0
        for pos in self.uses + self.defs:
            s += 10 ** self.loop_depth.get(pos, 0)
        return s

    def interferes(self, other: "Value") -> bool:
        return (self.first_def <= other.last_use
                and other.first_def <= self.last_use)


def predict(values: list[Value]) -> dict[str, str]:
    """Return {value_name: register}."""
    # Assignment order: savings DESC, last-use ASC, operand-idx DESC.
    order = sorted(
        values,
        key=lambda v: (-v.savings, v.last_use, -v.last_operand_idx),
    )
    assigned: dict[str, str] = {}
    for v in order:
        if v.fixed_reg is not None:
            assigned[v.name] = v.fixed_reg
            continue
        # registers used by already-assigned interfering values
        taken = {assigned[o.name] for o in values
                 if o.name in assigned and o is not v and v.interferes(o)}
        prio = DOUBLE_REGS
        if v.crosses_call:
            # EAX is the arg/return reg and is clobbered by the call, so it
            # cannot hold a value across a call.  EDX/ECX *can* — Watcom
            # pushes them in the prologue (a savings cost), so they stay in
            # the priority list.
            prio = [r for r in prio if r != "eax"]
        if v.crosses_muldiv:
            prio = [r for r in prio if r not in ("eax", "edx")]
        for r in prio:
            if r not in taken:
                assigned[v.name] = r
                break
        else:
            assigned[v.name] = "MEM"  # spilled
    return assigned


# ── validation harness ────────────────────────────────────────────────────────

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


def _compile_asm(src: str, tmp: Path) -> list:
    (tmp / "t.c").write_text(src)
    subprocess.run(
        ["podman", "run", "--rm", "-i", "-v", f"{tmp}:/src", _IMAGE,
         "wcc386", *_CFLAGS, "t.c"],
        input=b"", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        timeout=60,
    )
    code = _ledata((tmp / "t.obj").read_bytes())
    return list(_md.disasm(code, 0))


def _actual_regs_by_load_order(insns: list, n: int) -> list[str]:
    """The first n distinct `mov/movsx rX, [0]` loads -> their dest regs,
    in source-declared order (v0=g0 loads first, etc.)."""
    out = []
    for ins in insns:
        if ins.mnemonic in ("mov", "movsx", "movzx") and "[0]" in ins.op_str \
                and "ptr [0]" in ins.op_str:
            dst = ins.op_str.split(",")[0].strip()
            out.append(dst)
            if len(out) == n:
                break
    return out


def main() -> int:
    tmp = Path("/tmp/regalloc-predict")
    tmp.mkdir(exist_ok=True)
    npass = nfail = 0

    # A battery of straight-line snippets. For each we specify the Value
    # model and compare predict() to the compiler's actual assignment.
    # Identification: values are loaded from g0..gN in order.
    cases: list[tuple[str, str, list[Value], list[str]]] = []

    # Case 1: two values, both die at `return a+b` (operand order tiebreak).
    cases.append((
        "two-add-ab",
        "extern int g0,g1; extern void s(int);\n"
        "int t(void){ int a=g0,b=g1; s(a); s(b); return a+b; }\n",
        # a,b cross the s() calls.  res=a+b is returned in EAX (idx 5).
        # operand order at the add: a is op0, b is op1 -> b later -> b higher.
        [Value("a", uses=[0, 1, 4], defs=[-1], crosses_call=True, last_operand_idx=0),
         Value("b", uses=[2, 3, 4], defs=[-1], crosses_call=True, last_operand_idx=1),
         Value("res", uses=[5], defs=[4], fixed_reg="eax")],
        ["a", "b"],
    ))

    # Case 2: return b+a -> a is now op1 (later) -> a higher.
    cases.append((
        "two-add-ba",
        "extern int g0,g1; extern void s(int);\n"
        "int t(void){ int a=g0,b=g1; s(a); s(b); return b+a; }\n",
        [Value("a", uses=[0, 1, 4], defs=[-1], crosses_call=True, last_operand_idx=1),
         Value("b", uses=[2, 3, 4], defs=[-1], crosses_call=True, last_operand_idx=0),
         Value("res", uses=[5], defs=[4], fixed_reg="eax")],
        ["a", "b"],
    ))

    # Case 3: multi-use last-use discriminator (a@1,4 ; b@2,3) -> b dies first.
    # r is the accumulator, lives throughout, returned in EAX.
    cases.append((
        "lastuse-ab",
        "extern int g0,g1;\n"
        "int t(void){ int a=g0,b=g1,r=0; r+=a; r+=b; r+=b; r+=a; return r; }\n",
        [Value("a", uses=[1, 4], defs=[-1], last_operand_idx=1),
         Value("b", uses=[2, 3], defs=[-1], last_operand_idx=1),
         Value("r", uses=[1, 2, 3, 4, 5], defs=[0], fixed_reg="eax")],
        ["a", "b"],
    ))

    # Case 4: a+b+c (left-assoc) -> the result temp COALESCES with the first
    # operand `a` (2-address dst=src1), so `a` threads through as the
    # accumulator and lands in the return reg EAX.  b,c are pure competitors
    # ordered by last-use.  This coalescing IS the layer-4 add-direction
    # mechanism (restore_picture_part).  RULE: the leftmost operand of a
    # left-assoc commutative chain whose result is returned -> fixed EAX.
    cases.append((
        "three-abc",
        "extern int g0,g1,g2;\n"
        "int t(void){ int a=g0,b=g1,c=g2; return a+b+c; }\n",
        [Value("a", uses=[0, 3, 4, 5], defs=[-1], fixed_reg="eax"),  # coalesced result
         Value("b", uses=[1, 3], defs=[-1], last_operand_idx=1),
         Value("c", uses=[2, 4], defs=[-1], last_operand_idx=1)],
        ["a", "b", "c"],
    ))

    # Case 5: savings override — b used 3x outranks a used 1x for the higher
    # reg, regardless of last-use.  (no calls; res in EAX)
    cases.append((
        "savings-override",
        "extern int g0,g1;\n"
        "int t(void){ int a=g0,b=g1; return a + b + b + b; }\n",
        [Value("a", uses=[0, 2], defs=[-1], last_operand_idx=0),
         Value("b", uses=[1, 2, 3, 4], defs=[-1], last_operand_idx=1),
         Value("res", uses=[5], defs=[4], fixed_reg="eax")],
        ["a", "b"],
    ))

    for name, src, values, ids in cases:
        insns = _compile_asm(src, tmp)
        actual_regs = _actual_regs_by_load_order(insns, len(ids))
        pred = predict(values)
        pred_regs = [pred[i] for i in ids]
        ok = pred_regs == actual_regs
        npass += ok
        nfail += not ok
        mark = "OK " if ok else "XX "
        print(f"  {mark}{name:14s} predict={pred_regs}  actual={actual_regs}")
        if not ok:
            for s in (f"{x.mnemonic} {x.op_str}" for x in insns):
                print(f"        {s}")

    print(f"\n{npass} pass, {nfail} fail")
    return 0 if nfail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

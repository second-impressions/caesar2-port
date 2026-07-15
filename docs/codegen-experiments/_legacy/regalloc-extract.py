"""Regalloc predictor P2 — disasm -> value-flow extraction + the GAP it found.

Builds the `Value` set (register lifetimes: birth, uses, last-use, call/mul
crossing, operand index) straight from a function's PS.EXE bytes via
capstone detail, then runs the v0 predictor (regalloc-predict.py) and
compares to the actual register assignment.

RESULT (honest): on straight-line byte-exact functions the v0 predictor
reproduces only ~3% of register assignments.  The extractor is correct;
the v0 ASSIGNMENT model is too weak.  Worked example act_house1:

    mov eax, [const]   ; v1 (const)   -> EAX
    mov [g1], eax
    xor ecx, ecx       ; v0 (zero)    -> ECX   (NOT eax, NOT edx!)
    mov [g2], ecx

v0 and v1 have NON-overlapping live ranges, so a greedy "highest free
register with interference" allocator reuses EAX for the zero.  Watcom
does NOT: each conflict (name) is assigned its OWN register through
GiveBestReg, whose choice is driven by CountRegMoves + GivenRegisters +
WorthProlog, none of which the v0 model has.  And the zero lands in ECX,
not the higher-priority EDX, so it isn't even pure DoubleRegs order.

CONCLUSION: the last-use CONFLICT-ORDERING is proven (regalloc-last-use.py),
but turning the predictor into something that reproduces real functions
requires faithfully porting GiveBestReg (regalloc.c) — CountRegMoves,
GivenRegisters bias, TooGreedy, WorthProlog and the spill/save-set cost —
not just a greedy colourer.  That is the real size of Path B's P2/P3.

This file is the extraction substrate + the measurement that sizes the gap.

Run::
    uv run python docs/codegen-experiments/regalloc-extract.py
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import capstone

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

from c2.commands.disasm import disasm_function  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "regalloc_predict", Path(__file__).with_name("regalloc-predict.py"))
_rp = importlib.util.module_from_spec(_spec)
sys.modules["regalloc_predict"] = _rp
_spec.loader.exec_module(_rp)
Value, predict = _rp.Value, _rp.predict

_md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
_md.detail = True

_SUB = {"al": "eax", "ah": "eax", "ax": "eax", "eax": "eax",
        "bl": "ebx", "bh": "ebx", "bx": "ebx", "ebx": "ebx",
        "cl": "ecx", "ch": "ecx", "cx": "ecx", "ecx": "ecx",
        "dl": "edx", "dh": "edx", "dx": "edx", "edx": "edx",
        "si": "esi", "esi": "esi", "di": "edi", "edi": "edi",
        "bp": "ebp", "ebp": "ebp", "sp": "esp", "esp": "esp"}
_GP = {"eax", "ebx", "ecx", "edx", "esi", "edi", "ebp"}
_MULDIV = {"mul", "imul", "div", "idiv"}


def _reg_rw(ins):
    rd, wr = ins.regs_access()
    rds = {_SUB.get(ins.reg_name(r)) for r in rd} & _GP
    wrs = {_SUB.get(ins.reg_name(r)) for r in wr} & _GP
    return rds, wrs


def _opidx(reg, ins):
    first = ins.op_str.split(",")[0]
    forms = [k for k, v in _SUB.items() if v == reg]
    return 0 if any(f in first for f in forms) else 1


def extract(insns):
    insns = list(insns)
    open_val, closed, call_idx, mul_idx = {}, [], [], []

    def close(reg):
        v = open_val.pop(reg, None)
        if v is not None:
            v["last_use"] = max(v["uses"]) if v["uses"] else v["birth"]
            closed.append(v)

    for i, ins in enumerate(insns):
        m = ins.mnemonic
        if m == "call":
            call_idx.append(i)
        if m in _MULDIV:
            mul_idx.append(i)
        rd, wr = _reg_rw(ins)
        ops = ins.op_str.split(",")
        self_zero = m in ("xor", "sub") and len(ops) == 2 and ops[0].strip() == ops[1].strip()
        if not self_zero:
            for r in rd:
                v = open_val.get(r)
                if v is not None:
                    v["uses"].append(i)
                    v["opi"] = _opidx(r, ins)
        for r in wr:
            close(r)
            open_val[r] = {"reg": r, "birth": i, "uses": [], "opi": 0}
    for r in list(open_val):
        close(r)
    for v in closed:
        lo, hi = v["birth"], v["last_use"]
        v["crosses_call"] = any(lo < c <= hi for c in call_idx)
        v["crosses_muldiv"] = any(lo < c <= hi for c in mul_idx)
    return closed


def _match(name):
    try:
        addr, _size, lines = disasm_function(name)
    except Exception:
        return None
    code = b"".join(l.bytes_ for l in lines)
    insns = list(_md.disasm(code, addr))
    if any(i.mnemonic.startswith("j") for i in insns):
        return None  # straight-line only for v0
    vals = extract(insns)
    vobjs, truth = [], {}
    for k, v in enumerate(vals):
        nm = f"v{k}"
        truth[nm] = v["reg"]
        vobjs.append(Value(nm, uses=v["uses"] or [v["birth"]], defs=[v["birth"]],
                           last_operand_idx=v.get("opi", 0),
                           crosses_call=v["crosses_call"], crosses_muldiv=v["crosses_muldiv"],
                           fixed_reg="eax" if v["reg"] == "eax" else None))
    pred = predict(vobjs)
    comp = [(t, pred[nm]) for nm, t in truth.items() if t != "eax"]
    if not comp:
        return None
    return sum(t == p for t, p in comp), len(comp)


def main() -> int:
    state = Path("/tmp/st.json")
    if not state.exists():
        print("need /tmp/st.json (c2 decomp-verify --json); skipping batch.")
        return 0
    names = [f["name"] for f in json.load(state.open())["functions"]
             if f.get("diff_byte_count", 0) == 0 and f.get("size", 0) < 120]
    tot_m = tot_n = nfn = 0
    for n in names[:80]:
        r = _match(n)
        if r is None:
            continue
        m, c = r
        tot_m += m
        tot_n += c
        nfn += 1
    if tot_n:
        print(f"straight-line byte-exact fns: {nfn}   per-value match: "
              f"{tot_m}/{tot_n} = {100 * tot_m / tot_n:.0f}%")
    print("=> v0 greedy model is INSUFFICIENT for real code; needs GiveBestReg "
          "(CountRegMoves/GivenRegisters/WorthProlog).  See module docstring.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

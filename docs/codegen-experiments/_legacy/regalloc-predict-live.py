"""Regalloc predictor — LIVE-ORACLE validation (Path B, the working predictor).

The offline predictor (`regalloc-predict.py`) is only ~3% on real code because
it must *compute* the interference set (`conf->with.regs`) from value-flow, and
that approximation is wrong on real functions.  But `c2 regtrace` gives us the
**live** `with.regs` straight out of the compiler's `GiveBestReg` — so the only
remaining unknown is the per-conflict register SELECTION.

This experiment validates the selection model:

    chosen(conf) = first candidate in conf->tree->regs (DoubleRegs priority
                   order) whose register does NOT overlap conf->with.regs

i.e. GiveBestReg's pick in the common case where CountRegMoves scores 0 for
every free candidate (no MOV Rn=>Rn to save).  This is exactly `_chosen_reg`
in `c2/commands/regtrace.py`.

VALIDATION (no disasm needed — pure self-consistency on the live trace):
every register that appears in ANY conflict's `with.regs` must be the predicted
`chosen` of some other conflict (the interference set must be explained by the
model's own assignments).  If a register is "taken but never chosen", the model
mispredicts that conflict.

Result (pm_map0.c TU, after the 8-candidate mkhook fix on 2026-06-01):
**fully self-consistent — all 7 GP registers incl EBP explained, 93/93
conflicts**.  Before the fix the hook truncated candidate lists to 6 regs,
hiding EBP on EBP-using functions (get_pseudo_map) and leaving EBP
"unexplained".

So the greedy CountRegMoves==0 model reproduces the live allocator's
interference structure exactly.  The remaining gap (the ~3% offline number is
the value-flow extractor, NOT this selection rule) is the CountRegMoves
tie-break, which only moves a pick when a free candidate would eliminate a
register-to-register move — capturing those inputs needs the IR move/op
structure dumped from the hook (next instrumentation step; see
watcom10.0a repo docs/wcc386-re/regalloc-predictor-plan.md).

Run::
    # 1. capture a trace:  uv run c2 regtrace <fn> --file <f>.c
    # 2. validate:         uv run python docs/codegen-experiments/regalloc-predict-live.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# hw_reg_set encodings (10.0a); full-register membership is (enc & wr) == enc.
REG_ENC = {
    "EAX": 0x1000003, "EDX": 0x80000c0, "EBX": 0x200000c, "ECX": 0x4000030,
    "ESI": 0x10000100, "EDI": 0x20000200, "EBP": 0x400, "ESP": 0x800,
}
GP = ["EAX", "EDX", "EBX", "ECX", "ESI", "EDI", "EBP"]  # ESP always reserved

_TRACE = (Path(__file__).resolve().parents[2]
          / "watcom10.0a repo docs/wcc386-re/qemu-harness/work/regtrace.json")


def chosen_reg(cand: list[str], withregs: int) -> str:
    """GiveBestReg's pick in the CountRegMoves==0 case: first candidate (in the
    captured DoubleRegs priority order) whose register is free in `withregs`."""
    for c in cand:
        e = REG_ENC.get(c)
        if e is not None and (e & withregs) == 0:
            return c
    return "MEM"  # all candidates taken -> spill


# CountRegMoves opcodes (1994 wcc386, behaviorally decoded; see regalloc-symbols.md
# § "CG opcode enum").  Low integer ops match the OW source enum exactly.
_OP_MOV = 0x26
# ADD, EXT_ADD, MUL, EXT_MUL, AND, OR, XOR (the commutative set).  Supersedes the
# earlier {0x04,0x05,0x08,0x0d,0x0e,0x0f} (wrong opcode assumption).
_OP_COMMUTATIVE = {0x01, 0x02, 0x05, 0x06, 0x09, 0x0a, 0x0b}


def count_reg_moves(row: dict, reg_enc: int) -> int:
    """CountRegMoves(conf, reg) over the captured ins_walk: how many register-
    register moves assigning hw register `reg_enc` to this conflict's value
    would eliminate.  MOV match -> +tree_size (proxied to 2), commutative
    OP match -> +half (proxied to 1).  Mirrors cg/c/regalloc.c::CountRegMoves
    for the 386 path (no SUPER_OPTIMAL recursion at PS's opt level)."""
    V = {row["tree_temp"], row["tree_alt"]} - {0}
    SIZE, HALF = 2, 1
    count = 0
    for ins in row["ins_walk"]:
        op, res, rr = ins["opcode"], ins["result"], ins["result_reg"]
        o0, o0r, o1, o1r = ins["op0"], ins["op0_reg"], ins["op1"], ins["op1_reg"]
        if op == _OP_MOV:
            if (o0 in V and rr == reg_enc) or (res in V and o0r == reg_enc):
                count += SIZE
        elif op in _OP_COMMUTATIVE:
            if rr == reg_enc and (o0 in V or o1 in V):
                count += HALF
            elif res in V and (o0r == reg_enc or o1r == reg_enc):
                count += HALF
    return count


_INS_CAP = 16  # mkhook ins_walk cap; ranges longer than this are TRUNCATED.


def give_best_reg(row: dict) -> str:
    """Full GiveBestReg model over live inputs: among candidates free in
    with.regs, pick max CountRegMoves; ties -> candidate order (the captured
    DoubleRegs priority).

    CountRegMoves is only trusted when the conflict's whole instruction range was
    captured.  For range_len >= _INS_CAP the ins_walk is truncated, so the move
    count is unreliable -- fall back to the greedy (first-free) pick, which the
    end-to-end check confirms is correct for those (loop-spanning) values.
    (GivenRegisters tie-break not modelled; only matters on exact CRM ties.)"""
    wr = row["withregs"]
    truncated = row.get("range_len", 0) >= _INS_CAP
    best, best_saves = "MEM", -1
    for c in row["cand"]:
        e = REG_ENC.get(c)
        if e is None or (e & wr):
            continue
        saves = 0 if truncated else count_reg_moves(row, e)
        if saves > best_saves:
            best, best_saves = c, saves
    return best


def distinct_conflicts(rows: list[dict]) -> dict[int, dict]:
    """One row per conflict, FIRST sighting.  RegAlloc re-presents conflicts
    across passes (ExpandOps/FixChoices/AssignConflicts); the end-to-end check
    (col: actual EDX = first sighting w/ only EAX taken, not the later
    higher-savings re-presentation w/ EAX+EDX taken->EBX) shows the FIRST
    sighting -- the initial savings-desc assignment -- is the one that sticks,
    not the last.  (This corrects the earlier 'last sticks' assumption.)"""
    byconf: dict[int, dict] = {}
    for r in rows:
        if r.get("fn") == "GiveBestReg" and r["conf"] not in byconf:
            byconf[r["conf"]] = r
    return byconf


def validate(rows: list[dict]) -> tuple[bool, dict]:
    byconf = distinct_conflicts(rows)
    pred = {c: chosen_reg(r["cand"], r["withregs"]) for c, r in byconf.items()}
    chosen = set(pred.values())
    taken = set()
    for r in byconf.values():
        for reg, e in REG_ENC.items():
            if reg == "ESP":
                continue
            if (e & r["withregs"]) == e:
                taken.add(reg)
    unexplained = sorted(taken - chosen)
    cand_lens = sorted({len(r["cand"]) for r in byconf.values()})
    return (not unexplained), {
        "conflicts": len(byconf),
        "cand_lengths": cand_lens,
        "model_chooses": sorted(chosen - {"MEM"}),
        "taken_in_withregs": sorted(taken),
        "unexplained": unexplained,
        "full_8_candidates": cand_lens and max(cand_lens) >= 8,
    }


# End-to-end fixtures: model prediction vs the register the variable ACTUALLY
# gets in our compiler's output (from `c2 decomp-verify -v` / `c2 disasm` of the
# recompiled function).  This is the direct model->reality check that the (still
# blocked) live chosen-register hook would automate.  Extend as functions are
# traced + their actual register map read off the disasm.
_ACTUAL_REGS = {
    # get_pm_from_actual (pm_map0.c): verified from the recompiled disasm.
    "get_pm_from_actual": {"col": "EDX", "pm_val": "EAX", "row": "ECX"},
}


def end_to_end(rows: list[dict]) -> list[tuple[str, str, str, bool]]:
    """Compare give_best_reg() to the known actual register for named conflicts.
    Returns [(var, predicted, actual, ok)]."""
    byconf = distinct_conflicts(rows)
    out = []
    expected = {}
    for fixture in _ACTUAL_REGS.values():
        expected.update(fixture)
    for r in byconf.values():
        v = r.get("var")
        if v in expected:
            pred = give_best_reg(r)
            out.append((v, pred, expected[v], pred == expected[v]))
    return out


def main() -> int:
    if not _TRACE.exists():
        print(f"no trace at {_TRACE}\n"
              "run `uv run c2 regtrace <fn> --file <f>.c` first.")
        return 1
    rows = json.loads(_TRACE.read_text())
    ok, info = validate(rows)
    for k, v in info.items():
        print(f"  {k:22s} {v}")
    print()

    # CountRegMoves divergence: where the full model picks a different register
    # than the greedy (CountRegMoves==0) model — the cases CountRegMoves decides.
    if rows and "ins_walk" in rows[0]:
        byconf = distinct_conflicts(rows)
        div = 0
        examples = []
        for r in byconf.values():
            g = chosen_reg(r["cand"], r["withregs"])
            f = give_best_reg(r)
            if g != f:
                div += 1
                if r.get("var") and len(examples) < 6:
                    crm = {c: count_reg_moves(r, REG_ENC[c]) for c in r["cand"]
                           if c in REG_ENC and not (REG_ENC[c] & r["withregs"])}
                    examples.append((r["var"], g, f,
                                     {c: v for c, v in crm.items() if v}))
        print(f"  CountRegMoves overrides greedy on {div}/{len(byconf)} conflicts")
        for var, g, f, crm in examples:
            print(f"    {var:<14} greedy={g} -> CRM={f}   scores={crm}")
        print()

        # end-to-end: model prediction vs the actual compiled register.
        e2e = end_to_end(rows)
        if e2e:
            ok = sum(1 for _, _, _, k in e2e if k)
            print(f"  end-to-end (model vs actual compiled reg): {ok}/{len(e2e)} match")
            for var, pred, actual, k in e2e:
                print(f"    {var:<14} predict={pred:<5} actual={actual:<5} "
                      f"{'OK' if k else 'MISMATCH'}")
            print()
    if ok:
        print("SELF-CONSISTENT: every interference-set register is reproduced by "
              "the greedy chosen_reg model.")
        if not info["full_8_candidates"]:
            print("WARNING: candidate lists shorter than 8 — the mkhook capture "
                  "may be truncating EBP/ESP again.")
        return 0
    print(f"MISPREDICT: {info['unexplained']} appear in with.regs but the model "
          "never chooses them (CountRegMoves tie-break or capture truncation).")
    return 1


if __name__ == "__main__":
    sys.exit(main())

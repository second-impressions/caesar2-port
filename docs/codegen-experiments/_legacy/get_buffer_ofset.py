"""``get_buffer_ofset`` lever hunt -- decomp-bound CRM extraction.

Lever-hunting use case for cgex's decomp-bound mode + CRM extraction.
The function compiles to 28 bytes of diff under our current source; PS
keeps the accumulator ``r`` in callee-save EBX while our build keeps it
in EAX.  ``decomp-verify``'s output names the symptom (Rule 49b
zext-idiom asymmetry).  ``regtrace --explain`` shows ``r`` chose EAX
with savings 9.  Neither answers the underlying question: WHY does
GiveBestReg pick EAX, and what source change MOVES the score that
drives the pick?

This experiment answers that question MECHANICALLY by extracting the
CountRegMoves score per register for ``r`` under each source variant.
Run::

    uv run python docs/codegen-experiments/get_buffer_ofset.py

The CRM table that prints tells you EXACTLY which source perturbations
move which scores -- so the lever hunt is principled, not random.

Hypotheses tested:

* ``baseline``               : current decomp source.
* ``explicit_b0_temp``       : add a named ``int b0 = ...`` intermediate.
* ``single_expression``      : collapse to one TN_ASSIGN tree.
* ``lsb_first``              : reverse byte order.
* ``struct_typed_buffer``    : the user's hypothesis -- PS's original
                               ``text_buffer`` may have been a struct
                               array, not ``char[]``.  Test by casting
                               to a struct pointer and accessing the
                               same offsets as fields.
* ``three_locals``           : three named local byte vars + return expr.
* ``return_via_temp``        : ``return (r);`` vs ``return r;`` and a
                               trailing ``r += 0`` to bias CRM scores.

Background:
  - watcom-codegen-patterns.md "Rule 49 clear-first zext idiom" -- this
    function is explicitly mentioned as "lever not yet found, NOT
    impossible".
  - docs/wcc386-re/regalloc-model.md §3 -- the CRM + DoubleRegs
    tie-break that decides GiveBestReg.
"""
from __future__ import annotations

import sys
from pathlib import Path
from c2.commands.cgex import Experiment

CAESAR2_ROOT = Path(__file__).resolve().parent.parent.parent
LIB32_C = CAESAR2_ROOT / "decomp" / "src" / "lib32.c"

# AST-based whole-function swap: the named FuncDef in lib32.c is
# replaced verbatim by each trial's body.  pycparser locates the
# FuncDef so brace nesting / comments / etc. are robust.
exp = Experiment(
    name="get_buffer_ofset",
    ps_function="get_buffer_ofset",
    decomp_file=str(LIB32_C),
    decomp_function="get_buffer_ofset",
)

exp.add("baseline", """
int get_buffer_ofset(int idx)
{
    int off = idx * 4;
    int r;

    r = (unsigned char)text_buffer[off + 0xa];
    r <<= 16;
    r += (unsigned char)text_buffer[off + 9] << 8;
    r += (unsigned char)text_buffer[off + 8];
    return r;
}
""", note="current decomp source")

exp.add("explicit_b0_temp", """
int get_buffer_ofset(int idx)
{
    int off = idx * 4;
    int r;
    int b0 = (unsigned char)text_buffer[off + 0xa];

    r = b0;
    r <<= 16;
    r += (unsigned char)text_buffer[off + 9] << 8;
    r += (unsigned char)text_buffer[off + 8];
    return r;
}
""", note="explicit b0 temp -- adds `r = b0` IR MOV")

exp.add("single_expression", """
int get_buffer_ofset(int idx)
{
    int off = idx * 4;
    int r;

    r = ((unsigned char)text_buffer[off + 0xa] << 16)
      + ((unsigned char)text_buffer[off + 9] << 8)
      + (unsigned char)text_buffer[off + 8];
    return r;
}
""", note="single expression -- one TN_ASSIGN tree")

exp.add("lsb_first", """
int get_buffer_ofset(int idx)
{
    int off = idx * 4;
    int r;

    r = (unsigned char)text_buffer[off + 8];
    r += (unsigned char)text_buffer[off + 9] << 8;
    r += (unsigned char)text_buffer[off + 0xa] << 16;
    return r;
}
""", note="LSB-first byte accumulation")

# The user's hypothesis: PS's text_buffer may have been a STRUCT array.
# `text_buffer[idx * 4 + 0xa]` would then be `((struct *)text_buffer +
# idx)->field_at_offset_0xa`.  Address calculation IDENTICAL but the
# IR shape is different -- struct field access is a TN_LEAF on the
# field name with offset baked into addrfold, NOT an index +
# displacement.
exp.add("struct_typed_buffer", """
struct __buf_entry { unsigned char x[16]; };

int get_buffer_ofset(int idx)
{
    struct __buf_entry *e = (struct __buf_entry *)text_buffer + idx;
    int r;

    r = e->x[0xa];
    r <<= 16;
    r += (int)e->x[9] << 8;
    r += e->x[8];
    return r;
}
""", note="text_buffer treated as struct array -- field access path")

exp.add("three_locals", """
int get_buffer_ofset(int idx)
{
    int off = idx * 4;
    unsigned char b0 = text_buffer[off + 0xa];
    unsigned char b1 = text_buffer[off + 9];
    unsigned char b2 = text_buffer[off + 8];
    int r;

    r = ((int)b0 << 16) + ((int)b1 << 8) + b2;
    return r;
}
""", note="three named locals + return expression")

# Hypothesis: forcing r to be the result of a compound op (`r += 0`)
# right before return adds an IR ADD where r is both result AND op0.
# CRM bonus from commutative ops is conditional on result_reg / op_reg
# patterns -- the trailing `r += 0` might bias the score subtly.
exp.add("trailing_zero_add", """
int get_buffer_ofset(int idx)
{
    int off = idx * 4;
    int r;

    r = (unsigned char)text_buffer[off + 0xa];
    r <<= 16;
    r += (unsigned char)text_buffer[off + 9] << 8;
    r += (unsigned char)text_buffer[off + 8];
    r += 0;     /* CRM bias probe -- adds an IR ADD, no semantic effect */
    return r;
}
""", note="trailing `r += 0` to bias commutative-op CRM bonus")


def main() -> int:
    print("Compiling all trials (decomp-bound mode -- edits lib32.c per "
          "trial, then restores)...", file=sys.stderr)
    print()
    # decomp_diff() runs decomp-verify per trial.  Slow (each calls into
    # the full build pipeline), but reflects real decomp environment.
    print(f"{'trial':<28s} {'diff':>6s}  note")
    print("─" * 76)
    for trial_name, t in exp.trials.items():
        try:
            diff, size = exp.decomp_diff(trial_name)
            print(f"{trial_name:<28s} {diff:>6d}  {t.note}")
        except Exception as e:
            print(f"{trial_name:<28s} {'FAIL':>6s}  {e}")
    print()
    print("━" * 76)
    print("CountRegMoves scores per (variable, register) per trial:")
    print("━" * 76)
    exp.crm_table(vars_filter=["r", "off", "idx", "b0", "b1", "b2", "e"])
    print()
    print("━" * 76)
    print("How to read this table:")
    print("━" * 76)
    print("  CRM scores are the +2/+1 bonuses CountRegMoves accumulates per")
    print("  candidate register based on the captured ins_walk.  GiveBestReg")
    print("  picks max-CRM among free candidates; ties resolve by DoubleRegs")
    print("  order (EAX first).  EAX:2 on `r` in baseline comes from the")
    print("  return MOV -- the calling convention places the return value in")
    print("  EAX (technically EAX+EDX as a register-set, hence the EDX:2).")
    print()
    print("  To flip `r` off EAX, look for a trial where EBX (or another")
    print("  callee-save) scores STRICTLY HIGHER than EAX:2.  Equal scores")
    print("  still go to EAX by DoubleRegs first-free.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

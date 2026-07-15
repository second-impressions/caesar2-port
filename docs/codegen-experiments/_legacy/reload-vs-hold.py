"""Rule 116 — the named-intermediate marker: reload (inline) vs hold (named temp).

Question this proves: given a temporary holding an intermediate value in the
PS.EXE disassembly, can you tell whether the C *source* named that temp
(`int t = EXPR; … t …`) or whether the compiler manufactured it from an inline
expression?  Answer: **yes, for memory-rooted values used ≥2 times**, and the
source form is byte-recoverable.  For register-only arithmetic intermediates and
for any single-use value, naming is byte-neutral (no marker — write it either
way).

The mechanism (read from the OW v1.0 reference checkout, confirmed against the
10.0a binary and the live allocator via `c2 regtrace`):

  * A named local `int t = G;` is ONE coalesced CG value (`N_TEMP`) severed from
    its memory home — the allocator must HOLD it (callee-save reg + push, or a
    private stack slot under pressure); it can never re-read `[G]`.
  * An inline memory read stays an `N_MEMORY` reference tied to its home.  Two
    inline reads merge only if `cse.c::ReDefinedBy` proves nothing kills the
    value between them; a `__watcall` call KILLS aliasable globals, so two inline
    reads across a call never coalesce → the compiler RELOADS `[G]` each time.
  * Whether a held memory value is *worth* a register is `regsave.c::CalcSavings`
    = Σ(uses)·W^depth − spill/prolog cost (W=10 per loop level).  So the
    reload↔hold crossover is purely use-count × loop-weight: 1 use never clears
    the prolog cost (byte-neutral); ≥2 uses make the two source forms diverge.

Live-allocator ground truth (`c2 regtrace`, byte-exact functions):
  * `running_pop_tax`  (all-inline) → 5 conflicts, ALL anonymous `(temp)`,
    ins-range 2-5, savings 2-4, re-materialised into scratch EAX/EDX.
  * `test_for_any_admin` (named `eax`/`stride`/…) → named conflicts, ins-range
    64 (loop-spanning), savings 421/310/.../11, held in callee-save ESI/EDI.

Causal proof (whole-project verifier): the byte-exact inline `running_pop_tax`
breaks to a 22-byte diff the instant a named `int pass = pop_income_pass_count;`
temp is introduced; reverting to the inline form is byte-exact again.

This file asserts the cgex half (forms diverge iff memory-rooted & used ≥2×) and
the reload/hold disassembly shapes.  Run::

    uv run c2 cgex run reload-vs-hold
    uv run python docs/codegen-experiments/reload-vs-hold.py   # asserts
"""
from c2.commands.cgex import Experiment, _rel32_disp_offset

# Shared TU: a global, a row array, two void sinks (a __watcall call clobbers the
# caller-saved regs, forcing the reload-vs-hold question across each call).
_PRE = (
    "extern void use(int);\n"
    "extern void use2(int);\n"
    "extern int gv, ga;\n"
    "typedef struct { int x, y, hp, t; } row;\n"
    "extern row rows[2000];\n"
)
_DEFS = (
    "int gv, ga;\n"
    "typedef struct { int x, y, hp, t; } row;\n"
    "row rows[2000];\n"
    "void use(int x){}\n"
    "void use2(int x){}\n"
)

exp = Experiment(
    name="reload-vs-hold", ps_function=None, chk=False,
    prelude=_PRE, extra_defs=_DEFS,
)


def _inline_global(n):
    return "void f(void){ " + " ".join("use(gv);" for _ in range(n)) + " }"


def _named_global(n):
    return ("void f(void){ int t = gv; "
            + " ".join("use(t);" for _ in range(n)) + " }")


def _inline_elem(n):
    return "void f(int i){ " + " ".join("use(rows[i].hp);" for _ in range(n)) + " }"


def _named_elem(n):
    return ("void f(int i){ int t = rows[i].hp; "
            + " ".join("use(t);" for _ in range(n)) + " }")


# register-only arithmetic intermediate (no memory home) — expect byte-neutral
_INLINE_ARITH = "void f(int a, int b){ use(a*7+b); use2(a*7+b); }"
_NAMED_ARITH  = "void f(int a, int b){ int t = a*7+b; use(t); use2(t); }"

for _n in (1, 2, 3, 4):
    exp.add(f"inl_global_{_n}", _inline_global(_n), note=f"inline gv ×{_n}")
    exp.add(f"nam_global_{_n}", _named_global(_n),  note=f"named  gv ×{_n}")
    exp.add(f"inl_elem_{_n}",   _inline_elem(_n),   note=f"inline rows[i].hp ×{_n}")
    exp.add(f"nam_elem_{_n}",   _named_elem(_n),    note=f"named  rows[i].hp ×{_n}")
exp.add("inl_arith", _INLINE_ARITH, note="inline a*7+b ×2 (register-only)")
exp.add("nam_arith", _NAMED_ARITH,  note="named  a*7+b ×2 (register-only)")


def _masked(fn):
    """Mask LE fixups + intra-image rel32 disps so only real codegen differs."""
    bm = bytearray(fn.bytes_)
    for off in fn.fixups:
        rel = off - fn.base
        if 0 <= rel < len(bm):
            bm[rel] = 0
    for ins in fn.insns:
        m = _rel32_disp_offset(ins)
        if m is None:
            continue
        d = ins.rel_off + m
        for k in range(4):
            if d + k < len(bm):
                bm[d + k] = 0
    return bytes(bm)


def _same(a, b):
    fa, fb = exp.trial_function(a), exp.trial_function(b)
    if fa is None or fb is None:
        return None
    return _masked(fa) == _masked(fb)


def _load_count(trial, mem_substr):
    """How many times a memory home is READ (source operand) in a trial."""
    fn = exp.trial_function(trial)
    c = 0
    for ins in fn.insns:
        ops = ins.op_str
        if mem_substr in ops and not ops.strip().startswith(mem_substr):
            c += 1
    return c


def verify():
    exp.run()
    print("=== Rule 116: reload (inline) vs hold (named temp) ===\n")

    checks = {}

    # 1. Single use: naming is byte-NEUTRAL (no marker) for every value class.
    checks["global ×1: named ≡ inline (byte-neutral)"]  = _same("inl_global_1", "nam_global_1")
    checks["elem   ×1: named ≡ inline (byte-neutral)"]   = _same("inl_elem_1",   "nam_elem_1")

    # 2. Memory-rooted value used ≥2×: named ≠ inline at EVERY count (marker present).
    checks["global ×2/3/4: named ≠ inline (marker)"] = (
        _same("inl_global_2", "nam_global_2") is False
        and _same("inl_global_3", "nam_global_3") is False
        and _same("inl_global_4", "nam_global_4") is False
    )
    checks["elem ×2/3/4: named ≠ inline (marker)"] = (
        _same("inl_elem_2", "nam_elem_2") is False
        and _same("inl_elem_3", "nam_elem_3") is False
        and _same("inl_elem_4", "nam_elem_4") is False
    )

    # 3. Register-only arithmetic intermediate: byte-neutral even multi-use
    #    (the compiler builds the same temp whether or not you name it).
    checks["arith ×2: named ≡ inline (no memory home → no marker)"] = _same("inl_arith", "nam_arith")

    # 4. The disassembly shapes that justify the marker:
    #    inline RELOADS the home at each use; named loads ONCE and holds.
    checks["inline global ×3 reloads home (≥3 reads)"] = _load_count("inl_global_3", "[0x") >= 3
    checks["named  global ×3 holds  home (1 read)"]    = _load_count("nam_global_3", "[0x") == 1
    checks["inline elem  ×3 reloads home (≥3 reads)"]  = _load_count("inl_elem_3", "[edx + ") >= 3
    checks["named  elem  ×3 holds  home (1 read)"]     = _load_count("nam_elem_3", "[edx + ") == 1

    for k, v in checks.items():
        print(f"  [{'PASS' if v else 'FAIL'}] {k}")
    print("\n" + ("ALL PROOFS PASS" if all(checks.values()) else "SOME PROOFS FAILED"))
    return all(checks.values())


if __name__ == "__main__":
    import sys
    sys.exit(0 if verify() else 1)

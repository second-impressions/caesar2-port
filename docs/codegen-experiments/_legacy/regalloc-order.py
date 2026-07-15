"""Prove the Watcom 10.0a integer register-allocation ORDER empirically, and
tie it to the register-order tables found inside ``wcc386-10.0a.exe``.

Why this exists
---------------
The 10.0a 32-bit integer allocation order is

    DoubleRegs @ va 0x821A8 = EAX, EDX, EBX, ECX, ESI, EDI, EBP   (EBX before ECX)

(reverse-engineered from wcc386-10.0a.exe, ``watcom10.0a repo docs/wcc386-re/``).  This
experiment confirms that order behaviourally and connects it to the
Rule-28 family.

What it proves
--------------
1. **The consumption ladder.**  Pile up N int values that must all survive a
   call; the registers the allocator consumes appear in the order
   ``EDX, EBX, ECX, ESI, EDI, EBP`` (EAX is the return/call-clobbered reg).
   Prepending EAX → ``EAX, EDX, EBX, ECX, ESI, EDI, EBP`` == the binary's
   DoubleRegs table, byte-for-byte (**EBX before ECX**).

2. **Rule 28b (IDIV divisor).**  The ``totalXpercent`` shape (`a*b/100`)
   places the product in EBX and the divisor in ECX — exactly PS.EXE — which
   only matches because EBX outranks ECX in 10.0a.

3. **`Reg64Order` is a *different* table.**  ``rl.h`` maps 4-byte ints to
   ``RL_DOUBLE -> DoubleRegs``, NOT to ``Reg64Order``
   (``EAX,EBX,ESI,EDI,EDX,ECX,EBP`` @ va 0x81EE8).  Both tables are present in
   the binary; they govern different things.  Rule 28a is an **ESI/EDI** swap
   (ESI<EDI in both tables); Rule 28b is the **EBX/ECX** case that the
   DoubleRegs order (EBX before ECX) explains.

Run::

    uv run c2 cgex run regalloc-order            # table of trials
    uv run python docs/codegen-experiments/regalloc-order.py   # full proof + asserts
"""

from c2.commands.cgex import Experiment

CALLEE_SAVE = ("ebx", "ecx", "edx", "esi", "edi", "ebp")

exp = Experiment(
    name="regalloc-order",
    ps_function=None,            # synthetic probes; no single PS reference
    chk=False,
    externs={"g": "extern int g(int n);"},  # named param: cgex _stub_for needs it
    extra_defs="int gs; int pr;\n",         # storage for leaf_global's globals
)


# ── 1. The consumption ladder: N simultaneous cross-call int values ──
def _ladder(n: int) -> str:
    decls = " ".join(f"int x{i}=g({i});" for i in range(n))
    uses = "+".join(f"x{i}" for i in range(n))
    return f"int t(int a){{ {decls} g(0); return {uses}+g(1); }}"


for _n in range(1, 7):
    exp.add(f"ladder{_n}", _ladder(_n),
            note=f"{_n} cross-call int value(s)")


# ── 2. Rule 28b: IDIV divisor (totalXpercent shape) ──
exp.add("idiv_divisor", "int t(int a,int b){ a*=b; return a/100; }",
        note="Rule28b: product->EBX, divisor->ECX (==PS)")


# ── 3b. Callee-save economics: no observable caller/callee-save bonus ──
# 10.0a has no caller/callee-save bias in CountRegMoves that matters: in
# __watcall the no-push registers (EAX + used param regs) are EXACTLY the
# prefix EAX,EDX,EBX,ECX of DoubleRegs, so list order already prefers them —
# a bonus could never reorder a prefix preference.  Probe: a
# void(void) cross-call value has NO free register (EAX is call-clobbered), and
# the allocator takes EDX (DoubleRegs[1]) *paying a push* rather than dodging it.
exp.add("void_xcall", "int t(void){ int x=g(0); g(9); return x+g(1); }",
        note="void(void): value takes EDX paying a push (follows list order)")

# ── 3. Leaf global cached as cmp+addend (Rule 1 / do_promotion shape) ──
exp.add("leaf_global", """
extern int gs, pr;
int t(int level){
    gs = 3;
    if (pr < 10) { level += pr; if (level <= 10) pr = level; }
    return level;
}
""", note="leaf: loaded global -> first non-EAX callee-save")


# ───────────────────────── standalone proof ─────────────────────────
def _regs_used(exp_, trial):
    """Set of callee-save registers the trial's prologue pushes."""
    fn = exp_.trial_function(trial)
    if fn is None:
        return None
    out = []
    for i in fn.insns:
        if i.mnemonic == "push" and i.op_str in CALLEE_SAVE:
            out.append(i.op_str)
        elif i.mnemonic not in ("push",):
            break   # prologue pushes only
    return out


def verify():
    exp.run()
    print("=== Watcom 10.0a integer register-allocation order — proof ===\n")

    # 1. Ladder -> incremental consumption order
    prev = set()
    consumption = []
    print("consumption ladder (registers used as live values accumulate):")
    for n in range(1, 7):
        used = set(_regs_used(exp, f"ladder{n}"))
        added = used - prev
        prev = used
        tag = ",".join(sorted(added)) if added else "-"
        consumption.append(next(iter(added)) if len(added) == 1 else tag)
        print(f"  N={n}: pushes={sorted(used)}   newly added: {tag}")
    order = ["eax"] + consumption       # EAX is the return/clobbered reg
    print(f"\n  => allocation order: {', '.join(r.upper() for r in order)}")
    expect = ["eax", "edx", "ebx", "ecx", "esi", "edi", "ebp"]
    binary = "EAX,EDX,EBX,ECX,ESI,EDI,EBP (DoubleRegs @ va 0x821A8 in wcc386-10.0a.exe)"
    ok_order = order == expect
    print(f"  binary table: {binary}")
    print(f"  MATCH: {ok_order}")
    # EBX strictly before ECX in the allocation order
    ebx_before_ecx = order.index("ebx") < order.index("ecx")
    print(f"  EBX before ECX: {ebx_before_ecx}")

    # 2. Rule 28b
    div = _regs_used(exp, "idiv_divisor")
    ok_28b = set(div) == {"ebx", "ecx"} and exp.has_pattern("idiv_divisor", "idiv ecx")
    print(f"\nRule28b idiv_divisor: pushes={div}, 'idiv ecx' present={exp.has_pattern('idiv_divisor','idiv ecx')}")
    print(f"  product->EBX + divisor->ECX (matches PS.EXE totalXpercent): {ok_28b}")

    # 3. Leaf global
    leaf = _regs_used(exp, "leaf_global")
    ok_leaf = leaf == ["ebx"]
    print(f"\nleaf_global (do_promotion shape): pushes={leaf}  (Rule 1: EBX): {ok_leaf}")

    # 3b. Callee-save economics (the '-oh' bonus is moot)
    vx = _regs_used(exp, "void_xcall")
    ok_econ = vx == ["edx"]
    print(f"\nvoid_xcall: pushes={vx}  (takes EDX paying a push, no free-reg dodge): {ok_econ}")
    print("  => no observable caller/callee-save bonus: the no-push registers")
    print("     (EAX + param regs) are the DoubleRegs prefix, so list order subsumes it.")

    print("\n" + ("ALL PROOFS PASS"
                   if all([ok_order, ebx_before_ecx, ok_28b, ok_leaf, ok_econ])
                   else "SOME PROOFS FAILED"))


if __name__ == "__main__":
    verify()

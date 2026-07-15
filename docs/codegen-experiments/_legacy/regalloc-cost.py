"""The exact `CalcSavings` cost model for Watcom 10.0a (the savings/sort weights).

Algorithm structure read from the **OW v1.0 reference checkout** (NOT 10.0a
source, which is not public; ~5 years younger) -- `bld/cg/c/regsave.c`,
`bld/cg/intel/c/i86regsv.c`, `bld/cg/h/savings.h`, `savcode.h`.  Numeric
constants confirmed against the 10.0a binary by experiment to the exact value;
where v1 and 10.0a would diverge, the 10.0a behaviour wins.

The model
---------
A conflict (live range) gets `savings = save - cost` (clamped to
[0, 0xFFFFFFFF)), summed block-by-block with a loop-depth multiplier:

    save = Σ_blocks ( uses·use_save + defs·def_save + idx·index_save ) · W^depth
    cost = Σ_blocks ( spill_loads·load_cost + spill_stores·store_cost ) · W^depth

Conflicts are then assigned registers in descending-savings order
(equal savings -> layer-3 tie-break, see regalloc-tiebreak.py and
watcom10.0a repo docs/wcc386-re/regalloc-model.md §3).  A callee-saved register additionally
costs `push_cost + pop_cost` in `WorthProlog`.

Exact constants for PS (`-4r` = 486, default opt OptSize=50)
------------------------------------------------------------
  W (loop_weight) = (LOOP_FACTOR·time)/TOTAL_WEIGHT = (20·128)/256 = **10**
      -> W^depth: depth1 ×10, depth2 ×100, … capped at MAX_LOOP=5 (10^5)
      (flag corollary: -ot -> time=256 -> W=20; -os -> time=0 -> W=1, no loop weighting)
  COST(s,t) = (s·size + t·time)/256 = (s+t)/2 at default (size=time=128)
  486:  use_save=1  def_save=1  load_cost=2  store_cost=2  push_cost=1  pop_cost=1
        index_save = load_cost = 2
  MAX_LOOP=5   TOTAL_WEIGHT=256   LOOP_FACTOR=20   MAX_SAVE=0xFFFFFFFF

Behavioural confirmation (asserted below): a value used once per iteration of a
loop outranks a straight-line value for a register up to ~W uses; the crossover
lands at 10 (depth 1) and 100 (depth 2), matching W^depth = 10^depth.

Run::
    uv run c2 cgex run regalloc-cost
    uv run python docs/codegen-experiments/regalloc-cost.py   # asserts
"""
from c2.commands.cgex import Experiment

exp = Experiment(
    name="regalloc-cost", ps_function=None, chk=False,
    externs={"g": "extern int g(int v);"},
    prelude="extern int gi[60]; extern int n;\n",
    extra_defs="int gi[60]; int n;\n",
)


# A = used once per iteration of a loop (savings ≈ W per depth level).
# B = used K times straight-line (savings ≈ K).  Both cross a call so neither is
# EAX; the higher-savings value takes the earlier callee-saved register.
def _d1(k):
    b = "+".join("B" for _ in range(k))
    return (f"int t(void){{ int A=gi[0],B=gi[1],s=0,i; g(0); "
            f"for(i=0;i<n;i++){{ s+=A; }} return s+({b}); }}")


def _d2(k):
    b = "+".join("B" for _ in range(k))
    return (f"int t(void){{ int A=gi[0],B=gi[1],s=0,i,j; g(0); "
            f"for(i=0;i<n;i++) for(j=0;j<n;j++){{ s+=A; }} return s+({b}); }}")


for _k in (9, 10, 11):
    exp.add(f"d1_b{_k}", _d1(_k), note=f"depth-1 loop vs {_k} straight-line uses")
for _k in (95, 100, 105):
    exp.add(f"d2_b{_k}", _d2(_k), note=f"depth-2 loop vs {_k} straight-line uses")


def _a_wins(exp_, trial):
    """True if A (gi[0]) got an earlier register than B (gi[1])."""
    fn = exp_.trial_function(trial)
    if fn is None:
        return None
    order = ["eax", "edx", "ebx", "ecx", "esi", "edi", "ebp"]
    ra = rb = None
    for i in fn.insns:
        op = i.op_str.replace("0x", "")
        if i.mnemonic in ("mov", "add") and op.endswith(", dword ptr [0]") and ra is None:
            ra = i.op_str.split(",")[0].strip()
        if i.mnemonic in ("mov", "add") and op.endswith(", dword ptr [4]") and rb is None:
            rb = i.op_str.split(",")[0].strip()
    if ra not in order or rb not in order:
        return None
    return order.index(ra) < order.index(rb)


def verify():
    exp.run()
    print("=== CalcSavings loop-weight confirmation (W=10 per depth) ===\n")
    res = {t: _a_wins(exp, t) for t in exp.trials}
    for t, v in res.items():
        print(f"  {t:<9s} loop value outranks straight-line: {v}")
    checks = {
        "depth-1: loop beats 9 & 10 straight-line uses": res["d1_b9"] and res["d1_b10"],
        "depth-1: loop loses to 11 (crossover = 10 = W)": res["d1_b11"] is False,
        "depth-2: loop beats 95 straight-line uses": res["d2_b95"],
        "depth-2: loop loses to 100 (crossover = 100 = W^2)": res["d2_b100"] is False,
    }
    print()
    for k, v in checks.items():
        print(f"  [{'PASS' if v else 'FAIL'}] {k}")
    print("\n" + ("ALL PROOFS PASS" if all(checks.values()) else "SOME PROOFS FAILED"))


if __name__ == "__main__":
    verify()

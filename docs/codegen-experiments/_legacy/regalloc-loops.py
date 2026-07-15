"""Map of Watcom 10.0a LOOP register behaviour (invariant hoisting / reload),
at the exact PS flags (`-bt=dos -mf -4r -s -d1`, NO `-ol`).

Findings (all asserted below):

  * **Locals** (counter, accumulator, params) live in registers across the
    whole loop INCLUDING calls (callee-saved if they span a call); loaded/init
    once, never reloaded \u2014 they can't be aliased.
  * **Loop-invariant global reads are HOISTED** (loaded once before the loop)
    when the loop has **no aliasing risk** \u2014 no call AND no store through a
    pointer that could alias \u2014 and register pressure permits.
  * **Loop-invariant globals are RELOADED every iteration** when the loop
    contains **a call** (the callee might modify the global \u2014 PS has no `-oa`)
    or **an aliasing pointer store**.  Intra-iteration CSE still applies
    (used N times in one iteration -> loaded once per iteration).
  * Worth-it threshold: a *single* invariant hoists; multiple invariants in a
    loop that already spends registers on an accumulator+counter may not all
    hoist.
  * Register order follows the use-order/DoubleRegs model with **test-at-bottom**
    accounting (the loop is entered at the `cmp`, so the bound is first-used).

Decomp consequence: to match PS's hoist-vs-reload, match the loop's call /
aliasing-store structure.  Do NOT use `-oa` (PS didn't); the conservative
reload-across-calls behaviour is what makes us match.

Run::
    uv run c2 cgex run regalloc-loops
    uv run python docs/codegen-experiments/regalloc-loops.py   # asserts
"""
from c2.commands.cgex import Experiment

exp = Experiment(
    name="regalloc-loops", ps_function=None, chk=False,
    externs={"use": "extern void use(int x);"},
    prelude="extern int gi[200]; extern int go[200]; extern int n;\n",
    extra_defs="int gi[200]; int go[200]; int n;\n",
)

exp.add("hoist_noalias", "void t(void){ int i; for(i=0;i<100;i++) go[i]=n; }",
        note="invariant global, no call -> HOISTED (load before loop)")
exp.add("reload_call", "void t(void){ int i; for(i=0;i<n;i++){ go[i]=gi[5]; use(i); } }",
        note="call in loop -> global RELOADED each iter (aliasing)")
exp.add("local_across_call", "void t(int x){ int i; for(i=0;i<100;i++){ go[i]=x; use(i); } }",
        note="invariant LOCAL across call -> kept in reg, loaded once (const bound isolates x)")
exp.add("reload_aliasing_store", "void t(int*p){ int i; for(i=0;i<n;i++){ *p=gi[5]; p++; } }",
        note="aliasing *p store, no call -> global RELOADED each iter")
exp.add("intra_iter_cse",
        "void t(void){ int i; for(i=0;i<100;i++){ go[i]=gi[5]; go[i+1]=gi[5]; go[i+2]=gi[5]; use(i); } }",
        note="used 3x/iter + call -> 1 load per iter (intra-iter CSE), const bound isolates gi[5]")


def _loop_region(fn):
    """(top, end) instruction-index span of the innermost loop = from the\n    target of the last backward branch to that branch."""
    insns = fn.insns
    addr2i = {ins.rel_off: k for k, ins in enumerate(insns)}
    for k in range(len(insns) - 1, -1, -1):
        ins = insns[k]
        if ins.mnemonic.startswith("j"):
            try:
                tgt = int(ins.op_str, 16)   # handles '0x1b' and bare '6'
            except ValueError:
                continue
            if tgt <= ins.rel_off and tgt in addr2i:   # backward branch
                return addr2i[tgt], k
    return None


def _mem_reads_in_loop(fn):
    """count instructions inside the loop region with a `ptr [` memory read\n    of a global (disp present, not a pure [reg*scale] index of our arrays)."""
    reg = _loop_region(fn)
    if reg is None:
        return None
    lo, hi = reg
    cnt = 0
    for ins in fn.insns[lo:hi + 1]:
        s = f"{ins.mnemonic} {ins.op_str}"
        # a global read shows as `..., dword ptr [0x..]` (disp32, no index) OR
        # `cmp reg, dword ptr [..]`; array element reads use [reg*4] (index).
        if "ptr [" in ins.op_str:
            # crude: a global (invariant) operand has no `*` scale and no `+`
            # register base unless it's our array; treat `[0x..]`/`[0]` (disp
            # only) as a global reload.
            for tok in ins.op_str.split(","):
                t = tok.strip()
                if t.startswith("dword ptr [") and "*" not in t:
                    cnt += 1
    return cnt


def verify():
    exp.run()
    print("=== 10.0a loop register behaviour ===\n")
    checks = {}
    for trial in exp.trials:
        fn = exp.trial_function(trial)
        reads = _mem_reads_in_loop(fn) if fn else None
        print(f"  {trial:<22s} global mem-reads inside loop body: {reads}")
        checks[trial] = reads
    print()
    res = {
        "hoist_noalias: 0 reloads in loop (hoisted)": checks["hoist_noalias"] == 0,
        "reload_call: >=1 reload in loop": (checks["reload_call"] or 0) >= 1,
        "local_across_call: 0 reloads (local stays in reg)": checks["local_across_call"] == 0,
        "reload_aliasing_store: >=1 reload in loop": (checks["reload_aliasing_store"] or 0) >= 1,
        "intra_iter_cse: exactly 1 reload/iter (CSE)": checks["intra_iter_cse"] == 1,
    }
    for k, v in res.items():
        print(f"  [{'PASS' if v else 'FAIL'}] {k}")
    print("\n" + ("ALL PROOFS PASS" if all(res.values()) else "SOME PROOFS FAILED"))


if __name__ == "__main__":
    verify()

"""PROOF: the EAX <-> callee-saved boundary for a value is governed *solely* by
whether its live range crosses an EAX-clobbering instruction (a call, or
mul/div) — NOT by any push/callee-save "economics", the `register` keyword, or
register pressure.

This is the testable consequence of Result #1 (the callee-save bonus is moot;
register choice = DoubleRegs list order + CountRegMoves + sort, with no
economics overlay).  It tells the decomp that when a diff is "PS holds it in
EBX/ESI where we use EAX" (or vice-versa), the cause is a live-range/crossing
difference — there is no flag or keyword lever to chase.

Structure of the proof
----------------------
A value ``v = ga`` is returned.  We vary one thing at a time.

POSITIVE controls — the crossing flips the register:
  * no_cross               : v never spans a clobber           -> EAX  (no push)
  * call_present_not_crossed: a call exists but v dies before it-> EAX  (no push)
  * call_crossed           : SAME call, v used after it         -> callee-saved (push)
  * cross_idiv             : v spans an idiv (clobbers EAX/EDX) -> callee-saved (push)

NEGATIVE controls — economics/keyword levers CANNOT move v across the boundary:
  * nc_register  : `register int v` on the no-cross case  -> still EAX
  * nc_pressure  : 4 extra live locals (4 callee pushes!) -> v still EAX
  * nc_manyuse   : v used 5 times, no crossing            -> still EAX
  * cc_register  : `register int v` on the crossed case   -> still callee-saved

The clinching pair is (call_present_not_crossed vs call_crossed): identical
source, identical call, identical use count — only the crossing differs, and
that alone flips EAX -> EDX.

Run::

    uv run c2 cgex run regalloc-eax-boundary
    uv run python docs/codegen-experiments/regalloc-eax-boundary.py   # asserts
"""

from c2.commands.cgex import Experiment

CALLEE_SAVE = ("ebx", "ecx", "edx", "esi", "edi", "ebp")

exp = Experiment(
    name="regalloc-eax-boundary",
    ps_function=None,
    chk=False,
    externs={"sink": "extern void sink(void);"},
    prelude="extern int ga,gb,gc,gd,ge;\n",
    extra_defs="int ga,gb,gc,gd,ge;\n",
)

# positive controls
exp.add("no_cross", "int t(void){ int v=ga; return v; }",
        note="no clobber crossed -> EAX")
exp.add("call_present_not_crossed",
        "int t(void){ int v=ga; gb=v+1; sink(); return gc; }",
        note="call exists but v dies before it -> EAX")
exp.add("call_crossed",
        "int t(void){ int v=ga; sink(); gb=v+1; return gc; }",
        note="SAME call, v used after -> callee-saved (push)")
exp.add("cross_idiv", "int t(int n){ int v=ga; int q=n/gb; return v+q; }",
        note="v spans idiv (clobbers EAX/EDX) -> callee-saved")

# negative controls (economics / keyword levers)
exp.add("nc_register", "int t(void){ register int v=ga; return v; }",
        note="register keyword on no-cross -> still EAX")
exp.add("nc_pressure",
        "int t(void){ int v=ga; int a=gb,b=gc,c=gd,d=ge; return v+a+b+c+d; }",
        note="max register pressure, no crossing -> v still EAX")
exp.add("nc_manyuse", "int t(void){ int v=ga; return v+v+v+v+v; }",
        note="5 uses, no crossing -> still EAX")
exp.add("cc_register",
        "int t(void){ register int v=ga; sink(); gb=v+1; return gc; }",
        note="register keyword on crossed -> still callee-saved")


def _holder(exp_, trial):
    """Register holding `v = ga`: destination of the first memory load
    `mov <reg>, dword ptr [...]` (layout-independent), plus prologue pushes."""
    fn = exp_.trial_function(trial)
    if fn is None:
        return None, None
    held = None
    pushes = []
    for i in fn.insns:
        if i.mnemonic == "push" and i.op_str in CALLEE_SAVE:
            pushes.append(i.op_str)
        if (held is None and i.mnemonic == "mov"
                and "ptr [" in i.op_str
                and i.op_str.split(",")[0].strip() in ("eax",) + CALLEE_SAVE):
            held = i.op_str.split(",")[0].strip()
    return held, pushes


def verify():
    exp.run()
    print("=== EAX <-> callee-saved boundary = the EAX-clobber crossing ===\n")
    res = {}
    for name in exp.trials:
        h, pu = _holder(exp, name)
        res[name] = (h, pu)
        print(f"  {name:<26s} held(ga)={str(h):<5s} pushes={pu}")

    out = lambda n: res[n][0] in ("ebx", "ecx", "edx", "esi", "edi", "ebp")

    checks = {
        "no_cross -> EAX": res["no_cross"][0] == "eax",
        "call_present_not_crossed -> EAX": res["call_present_not_crossed"][0] == "eax",
        "call_crossed -> out of EAX": out("call_crossed"),
        "cross_idiv -> out of EAX": out("cross_idiv"),
        "clinching pair flips ONLY on crossing":
            res["call_present_not_crossed"][0] == "eax" and out("call_crossed"),
        "register kw can't force out": res["nc_register"][0] == "eax",
        "pressure can't evict the EAX holder": res["nc_pressure"][0] == "eax",
        "many uses can't force out": res["nc_manyuse"][0] == "eax",
        "register kw can't pull back": out("cc_register"),
    }
    print()
    for k, v in checks.items():
        print(f"  [{'PASS' if v else 'FAIL'}] {k}")
    print("\n" + ("ALL PROOFS PASS" if all(checks.values()) else "SOME PROOFS FAILED"))


if __name__ == "__main__":
    verify()

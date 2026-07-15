"""PROOF + map of the Watcom 10.0a register-ASSIGNMENT layer: given a type's
register class (Module 1) and the EAX-clobber boundary, *which value gets which
register* is decided by:

    1. descending SAVINGS  (~ number of uses, loop-weighted)         [savings rank]
    2. ties broken by ConfBefore on the name-node POINTER address    [name-ptr key]
    3. OVERRIDES: hard constraints (var-shift->ECX, idiv->EAX/EDX) and
       move-elimination (a value consumed as argN is placed in argN's reg).

NOTE on framing: this script was written when item 2 was thought to be
"first-use order" outright.  The actual micro-mechanism for the 10.0a
equal-savings tie-break is **under investigation** -- upstream OW v1/v2
`ConfBefore` is strict savings comparison (no secondary key), so the
deterministic tie order in 10.0a must come from either (H1) a hidden
secondary key in 10.0a's `ConfBefore` or (H2) ShellSort instability +
`AddConflictNode` pre-sort order.  Both H1 and H2 produce the order this
script asserts (for the single-use values it tests), so every assertion
below still holds.  Full model + the second source-level lever (Rule 115,
which this script does NOT cover -- decl-order, when the use is pinned) is
in `watcom10.0a repo docs/wcc386-re/regalloc-model.md` §3.  In project usage, the Rule-28
family is flipped by EITHER reordering the deciding use (Rule 28a, item 2
below) OR swapping the two tied locals' declaration order (Rule 115).

Findings (all asserted below against Watcom 10.0a):
  * use-order tie-break: with equal savings, values take EDX,EBX,ECX,ESI,EDI
    (int priority) strictly in first-use order.  `store a,b,c,d,e` -> D,B,C,SI,DI.
  * savings override: a value used more times jumps ahead of an earlier-used
    one (3-use beats first-used 1-use for EDX).
  * move-elim override: `f2(a,b)` places b in EDX (arg2) eliminating the shuffle,
    flipping the pure use-order.
  * hard constraint: a variable shift count is forced to ECX regardless.

Run::
    uv run c2 cgex run regalloc-tiebreak
    uv run python docs/codegen-experiments/regalloc-tiebreak.py   # asserts
"""
import re
from c2.commands.cgex import Experiment

FAM = {'al':'A','ah':'A','ax':'A','eax':'A','bl':'B','bh':'B','bx':'B','ebx':'B',
       'cl':'C','ch':'C','cx':'C','ecx':'C','dl':'D','dh':'D','dx':'D','edx':'D',
       'si':'SI','esi':'SI','di':'DI','edi':'DI','bp':'BP','ebp':'BP'}

exp = Experiment(
    name="regalloc-tiebreak", ps_function=None, chk=False,
    externs={"sink": "extern void sink(void);", "f2": "extern int f2(int a,int b);"},
    prelude="extern int gi[40]; extern int go[40];\n",
    extra_defs="int gi[40]; int go[40];\n",
)

# tie-break by first-use order (each value used once, identically -> equal savings)
def _store(order):
    decls = "".join("int %s=gi[%d];" % (v, i) for v, i in [('a',0),('b',1),('c',2),('d',3),('e',4)])
    stores = "".join("go[%d]=%s;" % (i, v) for v, i in order)
    return "int t(void){ %s sink(); %s }" % (decls, stores)

LO = [('a',0),('b',1),('c',2),('d',3),('e',4)]
exp.add("use_abcde", _store(LO),                       note="use order a,b,c,d,e -> D,B,C,SI,DI")
exp.add("use_edcba", _store(LO[::-1]),                 note="use order e,d,c,b,a -> regs follow use order")
exp.add("use_caebd", _store([LO[2],LO[0],LO[4],LO[1],LO[3]]), note="use order c,a,e,b,d")

# savings (use-count) override of use-order
exp.add("sav_tie",   "int t(void){int a=gi[0];int b=gi[1];sink();go[0]=a;go[1]=b;}",
        note="1use/1use tie -> a(first)=EDX")
exp.add("sav_b3",    "int t(void){int a=gi[0];int b=gi[1];sink();go[0]=a;go[1]=b;go[2]=b;go[3]=b;}",
        note="b used 3x -> b=EDX despite a first")

# move-elimination override
exp.add("moveelim", "int t(void){int a=gi[0];int b=gi[1];sink();return f2(a,b);}",
        note="b placed in EDX (arg2) -> move eliminated")

# hard constraint
exp.add("hard_shift", "int t(int x){int n=gi[0];sink();return x<<n;}",
        note="var shift count forced to ECX")


def _loads(fn):
    """[(mem_off, FAM)] for each `mov FAM, dword ptr [off]` load, in program order."""
    out = []
    for i in fn.insns:
        s = f"{i.mnemonic} {i.op_str}"
        if i.mnemonic in ("mov", "movsx", "movzx") and ", dword ptr [" in i.op_str:
            dst = i.op_str.split(",", 1)[0].strip()
            m = re.search(r"\[(0x[0-9a-f]+|\d+)\]", i.op_str.split(",", 1)[1])
            if m and dst in FAM:
                off = int(m.group(1), 16) if m.group(1).startswith("0x") else int(m.group(1))
                out.append((off, FAM[dst]))
    return out


def _regmap(exp_, trial):
    fn = exp_.trial_function(trial)
    if fn is None:
        return {}
    o2v = {0:'a',4:'b',8:'c',0xc:'d',0x10:'e'}
    seen = {}
    for off, fam in _loads(fn):
        if off in o2v and o2v[off] not in seen:
            seen[o2v[off]] = fam
    return seen


def _has(exp_, trial, pat):
    return exp_.has_pattern(trial, pat)


def verify():
    exp.run()
    print("=== 10.0a register-assignment layer ===\n")
    checks = {}

    # 1. use-order tie-break: regs in use order are always D,B,C,SI,DI
    for trial, order in [("use_abcde", "abcde"), ("use_edcba", "edcba"),
                         ("use_caebd", "caebd")]:
        rm = _regmap(exp, trial)
        seq = [rm.get(v, "?") for v in order]
        ok = seq == ["D", "B", "C", "SI", "DI"]
        checks[f"{trial}: use order {order} -> D,B,C,SI,DI"] = ok
        print(f"  {trial:<10s} use {order} -> {' '.join(seq)}   {'OK' if ok else 'FAIL'}")

    # 2. savings override
    tie = _regmap(exp, "sav_tie"); b3 = _regmap(exp, "sav_b3")
    print(f"\n  sav_tie a/b 1use: {tie}   sav_b3 (b x3): {b3}")
    checks["tie -> a=EDX (first use)"] = tie.get("a") == "D"
    checks["b x3 -> b=EDX (savings beats use-order)"] = b3.get("b") == "D"

    # 3. move-elim override
    me = _regmap(exp, "moveelim")
    print(f"\n  moveelim: {me}  (b in EDX=arg2 => move eliminated)")
    checks["move-elim: b=EDX (arg2)"] = me.get("b") == "D"
    checks["move-elim flips use-order: a=EBX"] = me.get("a") == "B"

    # 4. hard constraint
    hs = _has(exp, "hard_shift", "shl eax, cl")
    print(f"\n  hard_shift: var count forced to ECX ('shl eax, cl' present): {hs}")
    checks["var-shift count -> ECX"] = hs

    print()
    for k, v in checks.items():
        print(f"  [{'PASS' if v else 'FAIL'}] {k}")
    print("\n" + ("ALL PROOFS PASS" if all(checks.values()) else "SOME PROOFS FAILED"))


if __name__ == "__main__":
    verify()

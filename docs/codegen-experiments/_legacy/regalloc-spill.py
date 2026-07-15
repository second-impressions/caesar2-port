"""Register-exhaustion / spill threshold and sub-word (char) ordering for
Watcom 10.0a, at the PS flags.

Findings (asserted):
  * **7 GP integer registers** are allocatable (EAX,EDX,EBX,ECX,ESI,EDI,EBP).
  * A value that **crosses a call** can't use EAX -> **6** cross-call values fit
    in registers (EDX,EBX,ECX,ESI,EDI,EBP); the **7th spills to the stack**
    (`sub esp,4` per spilled value).
  * Values that **don't cross a call** can use EAX too -> **7** fit, **8th** spills.
  * **char** (cross-call) packs into byte sub-registers in DoubleRegs parent
    order: **DL, DH, BL, BH, CL, CH** (no AL/AH across a call; never SI/DI/BP).

Run::
    uv run c2 cgex run regalloc-spill
    uv run python docs/codegen-experiments/regalloc-spill.py   # asserts
"""
from c2.commands.cgex import Experiment

exp = Experiment(
    name="regalloc-spill", ps_function=None, chk=False,
    externs={"g": "extern int g(int v);"},
    prelude="extern int gi[40]; extern int go[40];"
            " extern signed char gc[40]; extern signed char goc[40];\n",
    extra_defs="int gi[40]; int go[40]; signed char gc[40]; signed char goc[40];\n",
)


def _xcall(n):   # n values defined by a call (cross the next call), stored after
    d = " ".join(f"int x{i}=g({i});" for i in range(n))
    u = "".join(f"go[{i}]=x{i};" for i in range(n))
    return f"void t(void){{ {d} g(99); {u} }}"


def _nocall(n):  # n values, no call between def and use
    d = " ".join(f"int x{i}=gi[{i}];" for i in range(n))
    u = "".join(f"go[{i}]=x{i};" for i in range(n))
    return f"void t(void){{ {d} {u} }}"


for _n in (6, 7):
    exp.add(f"xcall{_n}", _xcall(_n), note=f"{_n} cross-call values")
for _n in (7, 8):
    exp.add(f"nocall{_n}", _nocall(_n), note=f"{_n} non-cross-call values")

exp.add("char5",
        "void t(void){ " + " ".join(f"signed char c{i}=gc[{i}];" for i in range(5))
        + " g(0); " + "".join(f"goc[{i}]=c{i};" for i in range(5)) + " }",
        note="5 cross-call char values -> DL,DH,BL,BH,CL")


def _spilled(exp_, trial):
    """stack bytes reserved for spills = the `sub esp, N` immediate (0 if none)."""
    fn = exp_.trial_function(trial)
    if fn is None:
        return None
    for i in fn.insns:
        if i.mnemonic == "sub" and i.op_str.startswith("esp,"):
            return int(i.op_str.split(",")[1].strip(), 16)
    return 0


def _byteregs(exp_, trial):
    fn = exp_.trial_function(trial)
    seq = []
    for i in fn.insns:
        for tok in i.op_str.replace(",", " ").split():
            if tok in ("al", "ah", "bl", "bh", "cl", "ch", "dl", "dh") and tok not in seq:
                seq.append(tok)
    return seq


def verify():
    exp.run()
    print("=== register exhaustion / spill + char ordering ===\n")
    s = {t: _spilled(exp, t) for t in ("xcall6", "xcall7", "nocall7", "nocall8")}
    for t, v in s.items():
        print(f"  {t:<9s} stack bytes for spills: {v}")
    chars = _byteregs(exp, "char5")
    print(f"  char5 byte-regs in use order: {chars}")
    checks = {
        "6 cross-call values: no spill": s["xcall6"] == 0,
        "7 cross-call values: 1 spill (sub esp,4)": s["xcall7"] == 4,
        "7 non-cross-call values: no spill (EAX usable)": s["nocall7"] == 0,
        "8 non-cross-call values: 1 spill": s["nocall8"] == 4,
        "char order = DL,DH,BL,BH,CL": chars == ["dl", "dh", "bl", "bh", "cl"],
    }
    print()
    for k, v in checks.items():
        print(f"  [{'PASS' if v else 'FAIL'}] {k}")
    print("\n" + ("ALL PROOFS PASS" if all(checks.values()) else "SOME PROOFS FAILED"))


if __name__ == "__main__":
    verify()

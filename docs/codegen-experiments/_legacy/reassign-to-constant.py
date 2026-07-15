#!/usr/bin/env python3
"""Reassign-to-constant relieves cross-call register pressure (Rule 155).

Discovered closing ``forum_industry_screen`` (619b -> 145b, commits
d83a329 + 2132646).  The lever is *not* the Rule 26 setcc-vs-branch
choice -- in that function BOTH the throwaway and the reassign form
folded to the identical ``setne dl; add edx,0x4b``.  The win was pure
register-pressure relief: reassigning a local to a constant in a branch
kills its *original* live range, dropping a cross-call value and (when
the function sits in the spill window) one stack slot.

This script isolates the lever from the forum_industry_screen context
and asserts the three facts that define it:

  1. Both forms fold to the SAME ``setcc`` (so Rule 26 stays silent --
     this is a different lever, proven by the spill delta alone).
  2. At the spill threshold the throwaway form reserves a spill slot
     (``sub esp, 4``) the reassign form does not.
  3. The lever is ROBUST across pressure (n = 2..9 all fire): the
     throwaway's boolean temp is always the spill-triggering extra
     cross-call value; the reassign form never adds it.  (An earlier
     hypothesis of a narrow "pressure window" was an artefact of a
     buggy probe with a different call structure.)

Run:  uv run python docs/codegen-experiments/reassign-to-constant.py
      (prints ALL PROOFS PASS on success)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from c2.commands.oracle import compile_snippet

PRELUDE = (
    "int call1(int a,int b,int c,int d){ return a+b+c+d; }\n"
    "int gi[16]; int go[16];\n"
)


def _fn(body: str):
    b = compile_snippet(PRELUDE + body)
    assert b.ok, f"build failed:\n{b.output[-400:]}"
    return b.function("f")


def _spill_bytes(fn) -> int:
    """stack bytes reserved for spills = the `sub esp, N` immediate (0 if none)."""
    for ins in fn.insns:
        if ins.mnemonic == "sub" and ins.op_str.startswith("esp,"):
            return int(ins.op_str.split(",")[1].strip(), 16)
    return 0


def _has_setcc(fn) -> bool:
    return any(i.mnemonic.startswith("set") for i in fn.insns)


def _variant(n_vals: int, mode: str) -> str:
    """n_vals cross-call ints v0..v{n-1} + flag h.  Two calls; h used in the 2nd."""
    defs = " ".join(f"int v{i}=gi[{i}];" for i in range(n_vals))
    h = f"int h=gi[{n_vals}];"
    # first call: 4 args, drawing from the defs (pad with 0 if fewer than 4).
    # The point is just that ALL defs are live across this call.
    args = [f"v{i}" for i in range(min(4, n_vals))] + ["0"] * (4 - min(4, n_vals))
    call1 = f"call1({','.join(args)});"
    if mode == "throwaway":
        use = f"call1((h != 1) + 0x4b, v0, v1, 0);"
    elif mode == "reassign":
        use = "if (h == 1) h = 0x4b; else h = 0x4c; call1(h, v0, v1, 0);"
    else:
        raise ValueError(mode)
    return f"void f(int i){{ {defs} {h} {call1} {use} go[i]=0; }}"


CHECKS = []


def check(label, ok, detail=""):
    CHECKS.append((label, ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}{('  -- ' + detail) if detail and not ok else ''}")
    return ok


def main() -> int:
    print("Reassign-to-constant pressure-relief proof (Rule 155):")

    # ── 1. Both forms fold to setcc (NOT a Rule 26 case) ─────────────
    n = 6  # in the spill window (see fact 3)
    ft, fr = _fn(_variant(n, "throwaway")), _fn(_variant(n, "reassign"))
    check(
        "both forms emit setcc (Rule 26 stays silent)",
        _has_setcc(ft) and _has_setcc(fr),
        f"throwaway setcc={_has_setcc(ft)} reassign setcc={_has_setcc(fr)}",
    )

    # ── 2. At the threshold, throwaway spills, reassign does not ──────
    st, sr = _spill_bytes(ft), _spill_bytes(fr)
    check(
        "throwaway spills (sub esp,4), reassign does not (sub esp,0)",
        st == 4 and sr == 0,
        f"throwaway={st:#x} reassign={sr:#x}",
    )
    check(
        "reassign is smaller (fewer spill load/store)",
        len(fr.bytes_) < len(ft.bytes_),
        f"throwaway={len(ft.bytes_)}b reassign={len(fr.bytes_)}b",
    )

    # ── 3. Robust across pressure: the lever fires at every n ≥ 2 ───
    #    (the throwaway's boolean temp is always the spill-triggering extra
    #    cross-call value; the reassign form never adds it).  Confirmed for
    #    n = 2..9 in /tmp probing; we assert n=2 and n=8 here.
    for n_check in (2, 8):
        ft_n = _fn(_variant(n_check, "throwaway"))
        fr_n = _fn(_variant(n_check, "reassign"))
        check(
            f"lever fires at n={n_check}: throwaway spills +4, reassign 0",
            _spill_bytes(ft_n) == _spill_bytes(fr_n) + 4 and _spill_bytes(fr_n) == 0,
            f"throwaway={_spill_bytes(ft_n):#x} reassign={_spill_bytes(fr_n):#x}",
        )

    print()
    if all(ok for _, ok in CHECKS):
        print("ALL PROOFS PASS")
        print("\nLever: a throwaway boolean-expression call arg `(c != K) + N`")
        print("keeps c's original live across preceding calls (the boolean temp")
        print("is a 7th cross-call value -> spill).  Reassigning c to a constant")
        print("`if(c==K)c=N1;else c=N2; call(...,c)` lets c's original die at the")
        print("compare; the constant result is short-lived.  Robust across")
        print("pressure (n=2..9 all fire); forum_industry_screen 619->145b.")
        return 0
    print("\nSOME PROOFS FAILED")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

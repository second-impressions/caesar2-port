#!/usr/bin/env python3
"""Const-store form is deterministic (Rule 110) — self-asserting proof.

The layer-4 "const-store idiom" was listed as an OPEN trigger: PS sometimes
materialises a constant in a register and stores it (`xor bl,bl; mov [m],bl`)
and sometimes emits an immediate store (`mov byte[m],imm`).  This script
compiles controlled snippets with the project oracle (Watcom 10.0a, PS flags)
and asserts the two independent mechanisms that fully decide the FORM:

The FORM depends on the destination ADDRESSING MODE:

  A. DIRECT GLOBAL `[disp32]` or INDEXED-GLOBAL `[reg*scale + global_disp]`
     (incl. PS's folded `global[idx].field`):
       * storing 0 -> ALWAYS register-materialised (xor reg,reg; mov [m],reg),
         even single-use (a gen-level zero rule, independent of cachecon);
       * storing a NONZERO constant -> register iff referenced >= 2 times
         (cachecon.c::ConstToTemp), else immediate (c6/c7).  Call args never
         count; a store counts; a register-operand compare counts; a pure
         memory-immediate compare does not.
  B. POINTER / BASE+OFFSET `[reg + disp]` (a cached `p->field`):
       * ALWAYS immediate (mov [reg+disp], imm) -- both 0 and nonzero,
         regardless of count.

So when PS folds a global into the address (form A, register-0) but recomp
caches a pointer (form B, immediate-0) the const-store form differs *because
the addressing differs* -- that is a Rule 73 (cached-pointer) issue, fixed by
inlining the pointer (which fixes both addressing and form).  Which register
the temp gets is plain regalloc (NOT asserted here).

Run:  uv run python docs/codegen-experiments/const-store.py
      (prints ALL PROOFS PASS on success)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from c2.commands.oracle import compile_snippet

PRELUDE = (
    "unsigned char ga, gb, gc;\n"
    "int gi, gj, gk;\n"
    "struct S { int a, b, c; };\n"
    "struct S sarr[50];\n"
    "int other(int x){ return x; }\n"
)


def gen(body: str) -> str:
    b = compile_snippet(PRELUDE + body)
    assert b.ok, f"build failed:\n{b.output[-400:]}"
    cands = [(n, f) for n, f in b.functions.items() if n.startswith("f_")]
    assert cands, "no f_ function"
    return cands[0][1].disasm_text()


def has(text: str, *needles: str) -> bool:
    return all(n in text for n in needles)


CHECKS = []


def check(label, body, predicate):
    text = gen(body)
    ok = predicate(text)
    CHECKS.append((label, ok))
    if not ok:
        print(f"  FAIL {label}\n{text}\n")
    return ok


# ── Mechanism 1: zero is always register-materialised ──────────────
# single byte store of 0 -> xor + mov reg (NOT c6 immediate)
check(
    "byte g=0 single -> register (xor)",
    "void f(void){ ga = 0; }",
    lambda t: has(t, "xor") and "c6 05" not in t,
)
# single int store of 0 -> xor + mov reg (NOT c7 immediate)
check(
    "int g=0 single -> register (xor)",
    "void f(void){ gi = 0; }",
    lambda t: has(t, "xor") and "c7 05" not in t,
)

# ── Addressing mode A vs B (the discriminator) ─────────────────────
# indexed-GLOBAL store of 0 -> register (form A): `xor`, store via register
# (asm ends `, edx`, never an immediate `, 0`).
check(
    "global sarr[i].b=0 (indexed) -> register (xor)",
    "void f(int i){ sarr[i].b = 0; }",
    lambda t: "xor" in t and "], 0" not in t,
)
# POINTER-deref store of 0 -> IMMEDIATE (form B): `mov [reg+disp], 0`, no xor.
check(
    "ptr p->b=0 (base+disp) -> immediate, NOT register",
    "void f(struct S *p){ p->b = 0; }",
    lambda t: "], 0" in t and "xor" not in t,
)
check(
    "ptr p->a=0;b=0;c=0 -> all immediate (no shared reg)",
    "void f(struct S *p){ p->a = 0; p->b = 0; p->c = 0; }",
    lambda t: t.count("], 0") >= 3 and "xor" not in t,
)
# POINTER-deref nonzero -> IMMEDIATE even x2 (cachecon doesn't reach form B)
check(
    "ptr p->a=5;b=5 -> immediate x2 (not cached)",
    "void f(struct S *p){ p->a = 5; p->b = 5; }",
    lambda t: t.count("], 5") >= 2 and "mov     edx, 5" not in t,
)

# ── Mechanism 2: nonzero in form A is cachecon (ref-count >= 2) ────
# single nonzero store -> immediate (c6 byte / c7 int)
check(
    "byte g=5 single -> immediate (c6)",
    "void f(void){ ga = 5; }",
    lambda t: "c6 05" in t,
)
check(
    "int g=5 single -> immediate (c7)",
    "void f(void){ gi = 5; }",
    lambda t: "c7 05" in t,
)
# two nonzero stores of same value -> register (cached CONST_TEMP)
check(
    "int g=5;h=5 (2 stores) -> register",
    "void f(void){ gi = 5; gj = 5; }",
    lambda t: "c7 05" not in t and t.count("mov") >= 2 and ("mov     edx, 5" in t or "mov edx, 5" in t or ", 5" in t and "89" in t),
)
# store + register-operand compare of same value -> register (cached into edx,
# then reused as the cmp operand)
check(
    "int g=5 + (h==5) reg-compare -> register",
    "int f(void){ gi = 5; if (gj == 5) gk = 1; return gk; }",
    lambda t: "mov     edx, 5" in t and "cmp     edx," in t,
)
# two memory-immediate compares -> NOT cached (immediate compares)
check(
    "two mem-immediate (g==5),(h==5) -> immediate, not cached",
    "int f(void){ if (gi == 5) gk = 1; if (gj == 5) gk = 2; return gk; }",
    lambda t: t.count("cmp") >= 2 and ", 5" in t and "mov     edx, 5" not in t,
)
# constant used only as a call arg never counts toward caching
check(
    "const only in call args -> not cached (immediate args)",
    "void f(void){ other(5); other(5); }",
    lambda t: "mov     edx, 5" not in t,  # pushed/loaded as arg, not a shared temp
)


def main() -> int:
    print("Const-store form proof (Rule 110):")
    for label, ok in CHECKS:
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}")
    if all(ok for _, ok in CHECKS):
        print("\nALL PROOFS PASS")
        return 0
    print("\nSOME PROOFS FAILED")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

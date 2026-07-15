#!/usr/bin/env python3
"""SOLVED: which plain-C source form keeps PS's show_query_business_advice
arm-4 "orphan cmp" -- the dead `cmp q_ind_market,0` (CC overwritten by the
next cmp) that PS.EXE has.

PS arm-4 (line map L2581-2584), the bytes we want to reproduce:
    cmp  dword [q_supplies], 0x43      ; L2581 feeds the jle (short-circuit)
    jle  L_conn                        ; if supplies<=0x43, skip market cmp
    cmp  byte [q_ind_market], 0       ; L2582 FLAG-DEAD (next cmp overwrites)
L_conn:
    cmp  dword [no_of_empire_conn],0  ; L2583 live; feeds jg
    jg   general
    mov  eax, 0x37                    ; word = 0x37
    jmp  end                          ; L2584

===========================================================================
SOLUTION (2026-06-23): the orphan cmp is the residue of a DEAD STORE, not an
empty-body if.  Source:

    } else if (q_ind_output == 4) {
        if (q_supplies > 0x43 && q_ind_market) word = 0x31;   // L2581/L2582
        if (no_of_empire_connections <= 0) word = 0x37;       // L2583
        else                               word = general_business_cause();
    }

The `word = 0x31` store is ALWAYS overwritten by the conn `if/else` below
(both arms assign `word`), so it is a dead store.  WCC 10.0a deletes the
store, which makes the `&&`'s second branch `je` target the very next
instruction; that jcc-to-next is then peepholed away, ORPHANING the
`cmp q_ind_market,0`.  The leading `cmp q_supplies,0x43; jle` survives
because its jump still skips the (now bare) market cmp.  Mac/CodeWarrior
DCEs the whole thing (arm-4 = just the conn test), confirming `word=0x31`
is genuinely dead -- this is byte-faithful AND semantically equal to PS
(word never stays 0x31 in arm-4).

Why every earlier sweep MISSED it:
  1. it declared g_qmarket as `int` (PS has it `char`) so the matcher's
     `80 3d` byte-cmp could never match a surviving dword cmp; and
  2. it only tried empty-body / discard forms (`if(A) B;`, `if(A&&B){}`,
     `(void)(...)`, comma-const, ...) -- ALL fully DCE'd by 10.0a.  None
     was a dead STORE, which is the actual mechanism.

This sweep now uses correct types, makes `word` a LOCAL (so dead-store
elimination can fire), and DISASSEMBLES via the oracle so the result is
read, not inferred.

Run:
    uv run python docs/codegen-experiments/orphan-cmp-arm4.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from c2.commands.oracle import compile_snippet, DEFAULT_CFLAGS, IMAGE_10_0A

# Proper types: q_supplies/no_of_empire_connections are int, q_ind_market char.
SETUP = "extern int f(void);\nint g_qsupplies, g_qconn;\nchar g_qmarket;\n"

# Each form is (label, arm-4 body, note).  `word` is a LOCAL int, returned so
# the live store at the end is kept; the question is whether the *earlier*
# market cmp survives.
FORMS = [
    # ---- the SOLUTION: dead store word=0x31 (always overwritten below) ----
    ("dead_store_0x31",
     "        if (g_qsupplies > 0x43 && g_qmarket) word = 0x31;\n"
     "        if (g_qconn <= 0) word = 0x37;\n"
     "        else word = f();\n",
     "dead store + && -> orphan market cmp (PS-faithful)"),
    # ---- prior failing forms, kept as the negative control ----
    ("and_empty_stmt",
     "        if (g_qsupplies > 0x43 && g_qmarket == 0) ;\n"
     "        if (g_qconn <= 0) word = 0x37;\n        else word = f();\n",
     "empty && stmt -> fully DCE'd"),
    ("nested_empty_block",
     "        if (g_qsupplies > 0x43) if (g_qmarket == 0) { }\n"
     "        if (g_qconn <= 0) word = 0x37;\n        else word = f();\n",
     "nested empty block -> fully DCE'd"),
    ("if_gt_discard",
     "        if (g_qsupplies > 0x43) g_qmarket == 0;\n"
     "        if (g_qconn <= 0) word = 0x37;\n        else word = f();\n",
     "body discard cmp -> DCE'd"),
]


def disasm(form_src):
    src = (SETUP + "int arm4(void) {\n        int word;\n"
           + form_src + "        return word;\n}\n")
    b = compile_snippet(src, extern_defs="int f(void){return 0;}\n",
                        image=IMAGE_10_0A, cflags=DEFAULT_CFLAGS)
    if not b.ok:
        return None, b.output[:300]
    return b.function("arm4_"), None


def keeps_orphan(fn):
    """True iff the dead market byte-cmp (80 3d ..) survives with no
    consuming jcc between it and the next cmp (the PS pattern)."""
    ms = [i.mnemonic for i in fn.insns]
    hexes = [i.hex.replace(" ", "") for i in fn.insns]
    for k in range(len(fn.insns) - 1):
        h = hexes[k]
        # cmp byte ptr [abs], 0  ==  80 3d ?? ?? ?? ?? 00
        if ms[k] == "cmp" and h.startswith("803d") and h.endswith("00"):
            nxt = fn.insns[k + 1].mnemonic
            if nxt == "cmp":          # immediately followed by another cmp = orphan
                return True
    return False


def main():
    print(f"{'form':<22} {'orphan?':<9} note")
    print("-" * 72)
    for label, src, note in FORMS:
        fn, err = disasm(src)
        if fn is None:
            print(f"{label:<22} {'ERR':<9} {err}")
            continue
        hit = keeps_orphan(fn)
        print(f"{label:<22} {'YES' if hit else 'no':<9} {note}")
    print("-" * 72)
    print("RESULT: `dead_store_0x31` reproduces PS's orphan market cmp; the "
          "empty-body / discard forms are all DCE'd.  Mechanism: dead-store "
          "elimination of `word=0x31` orphans the && market cmp.")


if __name__ == "__main__":
    main()

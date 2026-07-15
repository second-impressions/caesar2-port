"""Rule 53 candidate — `(y & 1) != 0` materialises a 0/1 boolean via
`setne; movzx`, while bare `y & 1` emits a plain `and` and inherits
the upper bits of the source register.

PS function `three_by_three` (127 b @ 0x35DC0) emits this prologue:

    push ebx,ecx,edx,esi,edi,ebp
    mov ebx, eax
    mov ecx, edx
    test dl, 1
    setne al
    mov edi, eax
    and edi, 0xff           ; ← Rule 49-style zext from setne result

The `setne; movzx`-via-and pattern is the Watcom 10.0a fingerprint of
"materialise the boolean test result into a 0/1 register".

If the C source had used bare `y & 1` instead, Watcom emits:

    mov edi, edx
    and edi, 1

— i.e. it does NOT go through `setne`, because `y & 1` is already
a value (0 or 1), not a boolean.

This experiment compares both forms to confirm the codegen
difference is consistent.
"""

from c2.commands.cgex import Experiment

exp = Experiment(
    name="parity-bool",
    chk=False,
    externs={
        "show_one_ptr":
            "extern void show_one_ptr(int x, int y);",
    },
)


# ── trial 1: baseline — `(y & 1) != 0` (the form that matches PS) ─
exp.add(
    "neq0",
    """
void three_by_three(int x, int y)
{
    int parity = (y & 1) != 0;

    show_one_ptr(x, y);
    show_one_ptr(x - parity, y + 1);
    show_one_ptr(x - parity + 1, y + 1);
}
""",
    note="(y & 1) != 0  →  setne; movzx",
)


# ── trial 2: bare `y & 1` ─────────────────────────────────────────
exp.add(
    "bare_and",
    """
void three_by_three(int x, int y)
{
    int parity = y & 1;

    show_one_ptr(x, y);
    show_one_ptr(x - parity, y + 1);
    show_one_ptr(x - parity + 1, y + 1);
}
""",
    note="y & 1  →  mov; and reg, 1 (no setne)",
)


# ── trial 3: double-negation `!!(y & 1)` ──────────────────────────
exp.add(
    "double_neg",
    """
void three_by_three(int x, int y)
{
    int parity = !!(y & 1);

    show_one_ptr(x, y);
    show_one_ptr(x - parity, y + 1);
    show_one_ptr(x - parity + 1, y + 1);
}
""",
    note="!!(y & 1)  →  setne path (same as != 0)",
)


# ── trial 4: ternary `(y & 1) ? 1 : 0` ────────────────────────────
exp.add(
    "ternary",
    """
void three_by_three(int x, int y)
{
    int parity = (y & 1) ? 1 : 0;

    show_one_ptr(x, y);
    show_one_ptr(x - parity, y + 1);
    show_one_ptr(x - parity + 1, y + 1);
}
""",
    note="(y & 1) ? 1 : 0  →  setne path (same as != 0)",
)

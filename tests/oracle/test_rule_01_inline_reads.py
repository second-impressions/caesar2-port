"""Rule 1 — Use a global twice inline rather than caching it in a local.

Verifies the rule against actual Watcom 10.0a output using the oracle
harness (see ``c2/commands/oracle.py``).

## What the rule predicts

Given a small ``__watcall`` function that reads a single global twice,

* writing the global *inline* at every read produces a save/restore of
  **EBX** as a value-pool register, with one cached `mov ebx, [global]`.
* writing the same logic with an explicit ``int local = global;``
  produces a save/restore of **EDX** as a temp-pool register, with the
  same cached `mov edx, [global]` shape.

Both forms are 36 bytes for ``do_promotion``; the only difference is
the register choice, and the EBX form matches PS.EXE's bytes
exactly (after fixup masking).

## Why we set this up this way

* ``do_promotion`` is the canonical example in
  ``docs/watcom-codegen-patterns.md`` Rule 1.
* PS.EXE bytes for ``do_promotion`` are at 0x55B1E (36 bytes).
  We don't compare against PS.EXE here \u2014 the rule's claim is
  about the *shape* of the codegen for two different C
  formulations, and that's what we check.
* The ``defs.c`` file holds the tentative definitions of the
  externs.  Defining them in the primary TU would let Watcom
  use direct ``cmp [imm], imm8`` memory operands (12-byte
  function in 386 codegen) instead of caching, because
  same-TU symbols have known DGROUP offsets.  That's a real
  effect we want to keep out of this rule's scope \u2014 see
  ``test_oracle_default_flags.py::test_dash_3r_inlines_globals``
  for the contrasting case.
"""

from __future__ import annotations

import pytest

from c2.commands.oracle import compile_snippet


_RIGHT = """\
extern int player_rank;
extern int game_state;

void do_promotion(int level)
{
    game_state = 3;
    if (player_rank < 10) {
        level += player_rank;
        if (level <= 10)
            player_rank = level;
    }
}
"""

_WRONG = """\
extern int player_rank;
extern int game_state;

void do_promotion(int level)
{
    int rank;
    game_state = 3;
    rank = player_rank;
    if (rank < 10) {
        level += rank;
        if (level <= 10)
            player_rank = level;
    }
}
"""

_DEFS = "int player_rank; int game_state;\n"


def _compile_pair(image):
    right = compile_snippet(_RIGHT, image=image, extern_defs=_DEFS,
                            label="rule1-right")
    wrong = compile_snippet(_WRONG, image=image, extern_defs=_DEFS,
                            label="rule1-wrong")
    assert right.ok, f"right build failed:\n{right.output}"
    assert wrong.ok, f"wrong build failed:\n{wrong.output}"
    return right.function("do_promotion"), wrong.function("do_promotion")


def test_right_form_uses_ebx(watcom_10_0a):
    """`do_promotion` without a local var should `push ebx` and cache in EBX."""
    right, _ = _compile_pair(watcom_10_0a)
    # Prologue / epilogue should save EBX, not EDX.
    assert right.has_insn("push", "ebx"), right.disasm_text()
    assert right.has_insn("pop",  "ebx"), right.disasm_text()
    assert not right.has_insn("push", "edx"), right.disasm_text()
    # The global should be loaded into EBX once.
    assert right.has_insn("mov", "ebx, dword ptr"), right.disasm_text()
    # And reused as the source of the add.
    assert right.has_insn("add", "eax, ebx"), right.disasm_text()


def test_wrong_form_uses_edx(watcom_10_0a):
    """`int rank = player_rank;` should switch the cache register to EDX."""
    _, wrong = _compile_pair(watcom_10_0a)
    assert wrong.has_insn("push", "edx"), wrong.disasm_text()
    assert wrong.has_insn("pop",  "edx"), wrong.disasm_text()
    assert not wrong.has_insn("push", "ebx"), wrong.disasm_text()
    assert wrong.has_insn("mov", "edx, dword ptr"), wrong.disasm_text()
    assert wrong.has_insn("add", "eax, edx"), wrong.disasm_text()


def test_size_is_identical(watcom_10_0a):
    """Both forms compile to the same size; only the register differs."""
    right, wrong = _compile_pair(watcom_10_0a)
    assert right.size() == wrong.size(), (
        f"size mismatch: right={right.size()} wrong={wrong.size()}"
    )
    assert right.size() == 36, (
        f"expected canonical 36-byte do_promotion, got {right.size()}"
    )


def test_right_form_matches_psexe_structure(watcom_10_0a):
    """The right form should match PS.EXE's instruction shape after masking.

    We can't compare to PS.EXE bytes directly here (PS.EXE's globals
    are at very different addresses), but we *can* compare insn
    mnemonics + operand shapes.
    """
    right, _ = _compile_pair(watcom_10_0a)
    # Strip operand details that differ between standalone snippet
    # and PS.EXE (memory addresses).  We compare the instruction
    # *shape* (mnemonic + operand kind).
    expected = [
        "push ebx",
        "mov dword ptr [...], 3",
        "mov ebx, dword ptr [...]",
        "cmp ebx, 0xa",
        "jge 0x...",
        "add eax, ebx",
        "cmp eax, 0xa",
        "jg 0x...",
        "mov dword ptr [...], eax",
        "pop ebx",
        "ret",
    ]
    actual = [_normalize(i.line) for i in right.insns]
    assert actual == expected, (
        f"\nexpected:\n  " + "\n  ".join(expected)
        + f"\nactual:\n  " + "\n  ".join(actual)
    )


import re as _re

_PTR_RE = _re.compile(r"dword ptr \[[^\]]+\]")
_JMP_RE = _re.compile(r"^(j[a-z]+|jmp)\s+0x[0-9a-fA-F]+$")


def _normalize(line: str) -> str:
    """Collapse memory operands and jump targets to a stable shape.

    * ``dword ptr [<addr>]`` → ``dword ptr [...]``
    * ``jXX 0x<addr>``       → ``jXX 0x...``  (target is link-positional)

    Small numeric immediates (`0xa`, `3`) are kept as-is — they're
    semantic, not link noise.
    """
    line = _PTR_RE.sub("dword ptr [...]", line)
    if (m := _JMP_RE.match(line)):
        line = f"{m.group(1)} 0x..."
    return line

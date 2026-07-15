"""Rule 28 - Whole-function callee-save register swap.

## Trigger

A void(void)-shaped function with one or more long-lived 32-bit
locals.  PS.EXE picks one callee-save register (e.g. EDI) for the
long-lived value, while the recomp picks a different callee-save
register (e.g. ESI).  Every place the value is used produces a 1-2
byte diff, scattered throughout the function body.

The function-level marker is the prologue: PS pushes one register
where the recomp pushes another, with the same total push count:

    PS:                    Recomp:
      push ebx               push ebx
      push ecx               push ecx
      push edx               push edx
      push edi  <-- swap     push esi  <-- swap

## Mechanism

`bld/cg/c/regalloc.c:GiveBestReg` (lines 836-840 in OW v1.0.0,
verbatim in v2 master) walks the priority list `tree->regs` and
picks the first register with maximum `CountRegMoves` savings.
Tie-breaker: prefer registers already in `GivenRegisters` (i.e.
already pushed in the prologue).

The 32-bit priority list `Reg64Order` in
`bld/cg/intel/386/c/386rgtbl.c:50-58` (v1.0.0, identical in v2)
is

    EAX, EBX, ESI, EDI, EDX, ECX, BP, SP

so by default the first long-lived 32-bit local lands in ESI;
subsequent ones stick to ESI by the GivenRegisters tie-breaker.

PS sometimes lands in EDI instead because PS\u2019s `CountRegMoves`
count was higher for EDI.  Without a source-level lever to bias
the savings, the recomp picks ESI everywhere, producing a
function-wide pseudo-swap.

## Detector

`_find_rule_28_swap` is a function-level pre-scan: it inspects
the leading consecutive `push <callee-save-reg>` instructions and
returns ``(ps_reg, rc_reg)`` if exactly ONE register differs
between the two prologue push lists.

`detect_rule_28` is a per-row check: a diff row fires Rule 28
when the PS and recomp asm are identical under the (ps_reg,
rc_reg) substitution, and at least one swap-pair register name
appears on either side.

## Right C: source-level lever (Rule 24-style)

There is no general fix.  Try:

* Adding/removing a named local that aliases a parameter or
  long-lived value (Rule 24a).
* Splitting a multi-use expression into a temp.
* Changing the order of declarations.

Each of these biases the savings calculation toward a different
callee-save register.

This is the SAME mechanism as Rule 24 / Rule 27, just observable
as a function-wide rename rather than a single spill swap.
"""

from __future__ import annotations

import pytest

from c2.commands.rule_hints import (
    _find_rule_28_swap,
    _find_rule_28b_extras,
    _row_is_pure_swap,
    _scan_prologue_pushes,
    detect_rule_28,
    detect_rule_28b,
    detect_hints,
)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _ins(rel_off: int, raw: bytes, asm: str):
    """Build an InsnT tuple matching what _render_diff produces."""
    return (rel_off, len(raw), raw, asm)


def _rows(ps_insns, rc_insns, diff_set):
    """Build (ps, rc, is_diff) rows from parallel insn lists.

    `diff_set` is a set of row indices that are diffs (others are equal).
    """
    n = max(len(ps_insns), len(rc_insns))
    out = []
    for i in range(n):
        ps = ps_insns[i] if i < len(ps_insns) else None
        rc = rc_insns[i] if i < len(rc_insns) else None
        out.append((ps, rc, i in diff_set))
    return out


# ── Prologue scanner ──────────────────────────────────────────────────────────


def test_scan_prologue_pushes_simple():
    insns = [
        _ins(0, b"\x53", "push ebx"),
        _ins(1, b"\x51", "push ecx"),
        _ins(2, b"\x52", "push edx"),
        _ins(3, b"\x57", "push edi"),
        _ins(4, b"\xc3", "ret"),
    ]
    pushes, start, end = _scan_prologue_pushes(insns)
    assert pushes == ["ebx", "ecx", "edx", "edi"]
    assert (start, end) == (0, 4)


def test_scan_prologue_pushes_stops_at_non_push():
    insns = [
        _ins(0, b"\x53", "push ebx"),
        _ins(1, b"\xc3", "ret"),
        _ins(2, b"\x51", "push ecx"),  # ignored — past the prologue
    ]
    pushes, start, end = _scan_prologue_pushes(insns)
    assert pushes == ["ebx"]
    assert (start, end) == (0, 1)


def test_scan_prologue_pushes_stops_at_non_callee_save():
    insns = [
        _ins(0, b"\x53", "push ebx"),
        _ins(1, b"\x6a\x00", "push 0"),  # immediate, not a register
    ]
    pushes, _, _ = _scan_prologue_pushes(insns)
    assert pushes == ["ebx"]


def test_scan_prologue_pushes_handles_empty():
    assert _scan_prologue_pushes([]) == ([], 0, 0)
    assert _scan_prologue_pushes([None]) == ([], 0, 0)


def test_scan_prologue_pushes_skips_stack_check_preamble():
    """`push <imm>; call <abs>; push <reg>...` — the imm/call pair is
    Watcom\u2019s `__CHK` invocation and should be skipped before
    counting register pushes."""
    insns = [
        _ins(0, b"\x68\x0c\x00\x00\x00", "push 0xc"),
        _ins(5, b"\xe8\x00\x00\x00\x00", "call 0x10"),
        _ins(10, b"\x53", "push ebx"),
        _ins(11, b"\x51", "push ecx"),
        _ins(12, b"\x90", "nop"),
    ]
    pushes, start, end = _scan_prologue_pushes(insns)
    assert pushes == ["ebx", "ecx"]
    # Register pushes start AFTER the stack-check preamble.
    assert (start, end) == (2, 4)


# ── Pair-swap detector ────────────────────────────────────────────────────────


def test_find_swap_pure_pair_esi_edi():
    ps = [_ins(i, b"\x00", asm) for i, asm in enumerate(
        ["push ebx", "push ecx", "push edx", "push edi"])]
    rc = [_ins(i, b"\x00", asm) for i, asm in enumerate(
        ["push ebx", "push ecx", "push edx", "push esi"])]
    rows = _rows(ps, rc, {3})
    assert _find_rule_28_swap(rows) == ("edi", "esi")


def test_find_swap_pure_pair_other_direction():
    ps = [_ins(i, b"\x00", asm) for i, asm in enumerate(
        ["push ebx", "push ecx", "push edx", "push esi"])]
    rc = [_ins(i, b"\x00", asm) for i, asm in enumerate(
        ["push ebx", "push ecx", "push edx", "push edi"])]
    rows = _rows(ps, rc, {3})
    assert _find_rule_28_swap(rows) == ("esi", "edi")


def test_find_swap_no_diff_returns_none():
    ps = [_ins(i, b"\x00", asm) for i, asm in enumerate(
        ["push ebx", "push ecx", "push edx", "push esi"])]
    rc = [_ins(i, b"\x00", asm) for i, asm in enumerate(
        ["push ebx", "push ecx", "push edx", "push esi"])]
    rows = _rows(ps, rc, set())
    assert _find_rule_28_swap(rows) is None


def test_find_swap_asymmetric_rejected():
    """Different push counts → Rule 28b territory, not handled here."""
    ps = [_ins(i, b"\x00", asm) for i, asm in enumerate(
        ["push ebx", "push ecx", "push edx", "push edi", "push ebp"])]
    rc = [_ins(i, b"\x00", asm) for i, asm in enumerate(
        ["push ebx", "push ecx", "push edx"])]
    rows = _rows(ps, rc, {3, 4})
    assert _find_rule_28_swap(rows) is None


def test_find_swap_multi_diff_rejected():
    """Two regs differ → not a clean single-pair swap."""
    ps = [_ins(i, b"\x00", asm) for i, asm in enumerate(
        ["push ebx", "push esi", "push edi"])]
    rc = [_ins(i, b"\x00", asm) for i, asm in enumerate(
        ["push ebx", "push ebp", "push ecx"])]
    rows = _rows(ps, rc, {1, 2})
    assert _find_rule_28_swap(rows) is None


# ── Per-row swap-equivalence check ────────────────────────────────────────────


def test_row_pure_swap_simple():
    ps = _ins(0, b"\x57", "push edi")
    rc = _ins(0, b"\x56", "push esi")
    assert _row_is_pure_swap(ps, rc, "edi", "esi", False, False)


def test_row_pure_swap_with_immediate():
    ps = _ins(0, b"\xbf\xe0\x00\x00\x00", "mov edi, 0xe0")
    rc = _ins(0, b"\xbe\xe0\x00\x00\x00", "mov esi, 0xe0")
    assert _row_is_pure_swap(ps, rc, "edi", "esi", False, False)


def test_row_pure_swap_with_fixup_address():
    """Fixup-affected addresses are allowed to differ."""
    ps = _ins(0, b"\x89\x3d\x00\x00\x00\x00",
              "mov dword ptr [0x348a4], edi")
    rc = _ins(0, b"\x89\x35\x00\x00\x00\x00",
              "mov dword ptr [0x40120], esi")
    assert _row_is_pure_swap(ps, rc, "edi", "esi", True, True)


def test_row_pure_swap_rejects_branch_distance():
    """Different branch displacements without fixup → Rule 16, not 28."""
    ps = _ins(0, b"\x74\x0c", "je 0x69")
    rc = _ins(0, b"\x74\x0e", "je 0x6b")
    assert not _row_is_pure_swap(ps, rc, "edi", "esi", False, False)


def test_row_pure_swap_rejects_no_swap_reg():
    """Row with no swap-pair register → Rule 28 doesn't apply."""
    ps = _ins(0, b"\x40", "inc eax")
    rc = _ins(0, b"\x48", "dec eax")
    assert not _row_is_pure_swap(ps, rc, "edi", "esi", False, False)


def test_row_pure_swap_rejects_different_constants():
    ps = _ins(0, b"\x83\xc7\x01", "add edi, 1")
    rc = _ins(0, b"\x83\xc6\x02", "add esi, 2")
    assert not _row_is_pure_swap(ps, rc, "edi", "esi", False, False)


def test_row_pure_swap_rejects_other_reg_diff():
    """Diff is in a non-swap register — Rule 28 should NOT fire."""
    ps = _ins(0, b"\x89\xc6", "mov esi, eax")
    rc = _ins(0, b"\x89\xd6", "mov esi, edx")
    assert not _row_is_pure_swap(ps, rc, "edi", "esi", False, False)


# ── End-to-end via detect_hints ───────────────────────────────────────────────


def test_detect_hints_fires_rule_28_on_swap_rows():
    """Three diff rows: prologue push, body load, epilogue pop.

    All three should fire Rule 28 once the prologue swap is detected.
    """
    ps = [
        _ins(0, b"\x53", "push ebx"),
        _ins(1, b"\x57", "push edi"),                    # diff
        _ins(2, b"\xbf\xe0\x00\x00\x00", "mov edi, 0xe0"),  # diff (body)
        _ins(7, b"\x5f", "pop edi"),                    # diff (epilogue)
        _ins(8, b"\x5b", "pop ebx"),
        _ins(9, b"\xc3", "ret"),
    ]
    rc = [
        _ins(0, b"\x53", "push ebx"),
        _ins(1, b"\x56", "push esi"),                    # diff
        _ins(2, b"\xbe\xe0\x00\x00\x00", "mov esi, 0xe0"),  # diff (body)
        _ins(7, b"\x5e", "pop esi"),                    # diff (epilogue)
        _ins(8, b"\x5b", "pop ebx"),
        _ins(9, b"\xc3", "ret"),
    ]
    rows = _rows(ps, rc, {1, 2, 3})
    hints = detect_hints(rows, 0, 0, set(), set())
    rule_28_count = sum(1 for h in hints if h is not None and h.rule == "Rule 28")
    assert rule_28_count == 3, (
        f"Expected 3 Rule 28 hits, got {rule_28_count}: "
        f"{[h.rule if h else None for h in hints]}"
    )


def test_detect_hints_no_rule_28_when_prologue_matches():
    """Same prologue → no swap → Rule 28 doesn't fire even on body diffs."""
    ps = [
        _ins(0, b"\x53", "push ebx"),
        _ins(1, b"\x56", "push esi"),
        _ins(2, b"\xbe\xe0\x00\x00\x00", "mov esi, 0xe0"),  # same body
        _ins(7, b"\x5e", "pop esi"),
        _ins(8, b"\x5b", "pop ebx"),
        _ins(9, b"\xc3", "ret"),
    ]
    # rc identical to ps → no diffs → Rule 28 can't and won't fire
    rows = _rows(ps, ps, set())
    hints = detect_hints(rows, 0, 0, set(), set())
    assert all(h is None for h in hints)


# ── Parametric: every callee-save pair ────────────────────────────────────────


@pytest.mark.parametrize("ps_reg,rc_reg", [
    ("edi", "esi"),
    ("esi", "edi"),
    ("edi", "ebp"),
    ("ebp", "edi"),
    ("esi", "ebp"),
    ("ebp", "esi"),
])
def test_swap_detection_for_pair(ps_reg, rc_reg):
    ps = [
        _ins(0, b"\x53", "push ebx"),
        _ins(1, b"\x00", f"push {ps_reg}"),
    ]
    rc = [
        _ins(0, b"\x53", "push ebx"),
        _ins(1, b"\x00", f"push {rc_reg}"),
    ]
    rows = _rows(ps, rc, {1})
    assert _find_rule_28_swap(rows) == (ps_reg, rc_reg)


# ── Rule 28b — asymmetric push count ──────────────────────────────────────────


def test_find_rule_28b_extras_ps_extra_ecx():
    """`totalXpercent` shape: PS pushes ebx+ecx, recomp pushes ebx."""
    ps = [
        _ins(0, b"\x68\x0c\x00\x00\x00", "push 0xc"),
        _ins(5, b"\xe8\x00\x00\x00\x00", "call 0x10"),
        _ins(10, b"\x53", "push ebx"),
        _ins(11, b"\x51", "push ecx"),
    ]
    rc = [
        _ins(0, b"\x68\x08\x00\x00\x00", "push 8"),
        _ins(5, b"\xe8\x00\x00\x00\x00", "call 0x10"),
        _ins(10, b"\x53", "push ebx"),
    ]
    rows = _rows(ps, rc, {0, 3})
    assert _find_rule_28b_extras(rows) == ({"ecx"}, set())


def test_find_rule_28b_extras_rc_extra_ebp():
    """Recomp uses an extra callee-save not in PS."""
    ps = [
        _ins(0, b"\x53", "push ebx"),
        _ins(1, b"\x57", "push edi"),
    ]
    rc = [
        _ins(0, b"\x53", "push ebx"),
        _ins(1, b"\x57", "push edi"),
        _ins(2, b"\x55", "push ebp"),
    ]
    rows = _rows(ps, rc, {2})
    assert _find_rule_28b_extras(rows) == (set(), {"ebp"})


def test_find_rule_28b_extras_rejects_symmetric_swap():
    """1-vs-1 asymmetric is Rule 28a territory, not 28b."""
    ps = [
        _ins(0, b"\x53", "push ebx"),
        _ins(1, b"\x57", "push edi"),
    ]
    rc = [
        _ins(0, b"\x53", "push ebx"),
        _ins(1, b"\x56", "push esi"),
    ]
    rows = _rows(ps, rc, {1})
    assert _find_rule_28b_extras(rows) is None


def test_find_rule_28b_extras_rejects_too_many_extras():
    """More than one extra register on either side → not flagged."""
    ps = [
        _ins(0, b"\x53", "push ebx"),
        _ins(1, b"\x57", "push edi"),
        _ins(2, b"\x55", "push ebp"),
    ]
    rc = [
        _ins(0, b"\x53", "push ebx"),
    ]
    rows = _rows(ps, rc, {1, 2})
    assert _find_rule_28b_extras(rows) is None


def test_find_rule_28b_extras_returns_none_when_equal():
    ps = [
        _ins(0, b"\x53", "push ebx"),
        _ins(1, b"\x57", "push edi"),
    ]
    rc = [
        _ins(0, b"\x53", "push ebx"),
        _ins(1, b"\x57", "push edi"),
    ]
    rows = _rows(ps, rc, set())
    assert _find_rule_28b_extras(rows) is None


def test_detect_rule_28b_fires_on_extra_push():
    ps = _ins(0xb, b"\x51", "push ecx")
    extras = ({"ecx"}, set())
    h = detect_rule_28b(ps, None, extras)
    assert h is not None
    assert h.rule == "Rule 28b"
    assert "ecx" in h.summary


def test_detect_rule_28b_fires_on_extra_pop():
    ps = _ins(0x1f, b"\x59", "pop ecx")
    extras = ({"ecx"}, set())
    h = detect_rule_28b(ps, None, extras)
    assert h is not None
    assert h.rule == "Rule 28b"


def test_detect_rule_28b_skips_unrelated_rows():
    """Body rows shouldn't fire Rule 28b — only push/pop rows that
    name an extra-pushed register."""
    ps = _ins(0x10, b"\x89\xc3", "mov ebx, eax")
    rc = _ins(0x10, b"\xbb\x64\x00\x00\x00", "mov ebx, 0x64")
    extras = ({"ecx"}, set())
    assert detect_rule_28b(ps, rc, extras) is None


def test_detect_rule_28b_respects_side():
    """When recomp has the extra, only recomp-side rows fire."""
    rc = _ins(0x2, b"\x55", "push ebp")
    extras = (set(), {"ebp"})
    h = detect_rule_28b(None, rc, extras)
    assert h is not None
    assert "recomp pushes extra ebp" in h.summary


def test_detect_hints_fires_28b_on_totalXpercent_shape():
    """End-to-end: stack-check preamble + asymmetric register pushes
    produce Rule 28b hints on the extra push and pop rows."""
    ps = [
        _ins(0, b"\x68\x0c\x00\x00\x00", "push 0xc"),         # diff (size)
        _ins(5, b"\xe8\x00\x00\x00\x00", "call 0x10"),
        _ins(10, b"\x53", "push ebx"),
        _ins(11, b"\x51", "push ecx"),                        # diff (extra)
        _ins(12, b"\x89\xc3", "mov ebx, eax"),                # body diff
        _ins(14, b"\x59", "pop ecx"),                         # diff (extra)
        _ins(15, b"\x5b", "pop ebx"),
        _ins(16, b"\xc3", "ret"),
    ]
    rc = [
        _ins(0, b"\x68\x08\x00\x00\x00", "push 8"),
        _ins(5, b"\xe8\x00\x00\x00\x00", "call 0x10"),
        _ins(10, b"\x53", "push ebx"),
        _ins(11, b"\x0f\xaf\xd0", "imul edx, eax"),
        _ins(14, b"\xbb\x64\x00\x00\x00", "mov ebx, 0x64"),
        _ins(19, b"\x5b", "pop ebx"),
        _ins(20, b"\xc3", "ret"),
    ]
    # Use difflib-style alignment so the rows match what the verifier
    # would produce.  Here we hand-build it: 28b fires on PS rows that
    # have ecx push/pop, regardless of how difflib paired them.
    rows = [
        (ps[0], rc[0], True),    # push 0xc vs push 8
        (ps[1], rc[1], False),   # call (same)
        (ps[2], rc[2], False),   # push ebx (same)
        (ps[3], rc[3], True),    # push ecx vs imul
        (ps[4], rc[4], True),    # mov ebx, eax vs mov ebx, 0x64
        (ps[5], None,  True),    # pop ecx (PS only)
        (ps[6], rc[5], False),   # pop ebx (same)
        (ps[7], rc[6], False),   # ret
    ]
    hints = detect_hints(rows, 0, 0, set(), set())
    rule_28b = sum(1 for h in hints if h is not None and h.rule == "Rule 28b")
    assert rule_28b == 2, (
        f"expected 2 Rule 28b hits (extra push ecx + extra pop ecx), "
        f"got {rule_28b}: "
        f"{[h.rule if h else None for h in hints]}"
    )

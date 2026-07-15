"""Tests for c2.commands.binir_shape_hints -- the per-source-line binir-IR
shape comparator that is integrated into ``decomp-verify`` output.

We exercise the public API (``detect``, ``to_json``) on synthetic row
streams that mirror what ``_build_diff_rows`` produces in
``decomp_verify.py``.  Each row dict has ``ln`` (source-line, only set
on the first instruction of each statement), and ``o`` / ``r`` -- raw
InsnT tuples ``(off, size, raw_bytes, asm)`` for PS / RC sides
respectively.
"""

from __future__ import annotations

from c2.commands.binir_shape_hints import detect, to_json


def _row(off, ln, ps_asm, rc_asm, kind="equal"):
    """Build a row dict matching the ``_build_diff_rows`` schema."""
    ps_insn = (off, 2, b"\x90\x90", ps_asm) if ps_asm else None
    rc_insn = (off, 2, b"\x90\x90", rc_asm) if rc_asm else None
    return {"off": off, "ln": ln, "kind": kind, "o": ps_insn, "r": rc_insn}


def test_no_lines_with_ir_verdict_when_no_source_lines():
    """Rows with no ``ln`` entries (all prolog) -> no_lines_with_ir."""
    rows = [
        _row(0, None, "push ebx", "push ebx"),
        _row(1, None, "push ecx", "push ecx"),
    ]
    h = detect(rows)
    assert h.verdict == "no_lines_with_ir"
    assert h.lines_compared == 0


def test_encoding_noise_when_all_lines_recover_identical_shapes():
    """PS and RC both produce a `cmp_jcc` op on the SAME source line ->
    binir says they're semantically equivalent.  The byte diff (eg
    different register names) is encoding noise."""
    rows = [
        # Same source line emits cmp + jne on both sides; only register
        # letters differ.
        _row(0,   123, "cmp ebx, 0x10", "cmp esi, 0x10", kind="replace"),
        _row(6,  None, "jne 0x20",       "jne 0x20"),
    ]
    h = detect(rows)
    assert h.verdict == "encoding_noise", h
    assert h.lines_compared == 1
    assert h.lines_identical == 1
    assert h.lines_divergent == 0
    assert "IDENTICAL" in h.note


def test_shape_divergence_when_one_side_has_extra_op():
    """PS emits a strength-reduced `mul_const` chain while RC emits a
    plain `imul` -- the recovered op kinds differ; binir flags it."""
    rows_diff = [
        # Source line 200: PS has a 5-ins shl/add/shl chain; RC has a single imul.
        _row(0, 200, "mov ecx, edx",   "mov eax, edx", kind="equal"),
        # PS side: 3-op chain (shl 2; add; shl 2) -> mul_const factor=20
        _row(2, None, "shl edx, 2",     None, kind="delete"),
        _row(5, None, "add edx, ecx",   None, kind="delete"),
        _row(7, None, "shl edx, 2",     None, kind="delete"),
        # RC side: single imul -- different IR shape
        _row(2, None, None, "imul eax, eax, 0x14", kind="insert"),
    ]
    h = detect(rows_diff)
    assert h.verdict == "shape_divergence"
    assert h.lines_compared == 1
    assert h.lines_divergent == 1
    assert h.divergences[0].line == 200
    # PS should have a mul_const recovery; RC has nothing recovered
    # (imul is not in binir's pattern set).
    assert "mul_const" in h.divergences[0].only_ps
    assert "200" in h.note


def test_forward_fills_line_attribution():
    """Rows after the first ``ln`` entry inherit until the next ``ln`` --
    the test relies on EACH line group producing at least one binir-
    recoverable op so the comparator counts both lines."""
    rows = [
        _row(0,   100, "mov eax, [m1]",  "mov eax, [m1]"),
        _row(6,  None, "test eax, eax",  "test eax, eax"),
        _row(8,  None, "je 0x30",        "je 0x30"),     # line 100: zero_test_jcc
        _row(10,  101, "mov ebx, [m2]",  "mov ebx, [m2]"),
        _row(16, None, "cmp ebx, 0x10",  "cmp ebx, 0x10"),
        _row(19, None, "jne 0x40",       "jne 0x40"),    # line 101: cmp_jcc
    ]
    h = detect(rows)
    assert h.lines_compared == 2, h
    assert h.verdict == "encoding_noise"


def test_to_json_serialises_full_state():
    rows = [
        _row(0,   50, "cmp ebx, 0x10",  "cmp esi, 0x10"),
        _row(6, None, "je 0x20",        "jne 0x20"),
    ]
    h = detect(rows)
    j = to_json(h)
    assert j["verdict"] == "encoding_noise"
    assert j["lines_compared"] == 1
    assert j["lines_identical"] == 1
    assert j["lines_divergent"] == 0
    assert isinstance(j["divergences"], list)
    assert "note" in j


def test_to_json_handles_none():
    assert to_json(None) is None


def test_lines_with_one_side_empty_are_skipped():
    """If a source line has rows only on PS side (pure delete) we can't
    compare semantically -- skip without flagging divergence."""
    rows = [
        _row(0,   77, "mov eax, [m1]", "mov eax, [m1]"),
        _row(6,   78, "ret",           None, kind="delete"),
    ]
    h = detect(rows)
    # Line 77 had matching IR; line 78 is pure delete (RC empty) -> skipped
    assert h.lines_compared <= 1
    # Specifically NOT shape_divergence since line 78 was skipped.
    assert h.verdict in ("encoding_noise", "no_lines_with_ir")

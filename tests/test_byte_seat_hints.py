"""Tests for the unified Byte-seat verdict (byte_seat_hints).

Exercises the always-on STATIC fast-path (PS asm + RC AST, no trace
image): the four-way classification of a `Byte-reg swap` row into
CASE A (collateral to a wider Reg swap), B (Rule 126 widen), C (Rule
127 de-name), or the `?` hedge when only the trace can split A vs D.
"""
from __future__ import annotations

import pycparser.c_ast as c_ast
import pytest

from c2.commands import byte_seat_hints, al_squat_hints, style_check, regalloc_hints
from c2.commands.c_source import parse_c
from c2.commands.rule_hints import RuleHint


def _byte_swap(ps: str, rc: str) -> RuleHint:
    return RuleHint(
        rule="Byte-reg swap",
        summary=f"byte-register identity swap (PS uses `{ps}`, recomp uses `{rc}`)",
        fix="",
    )


def _reg_swap(a: str, b: str) -> RuleHint:
    return RuleHint(rule="Reg swap", summary=f"register identity swap ({a}\u2194{b})", fix="")


def _insn(asm: str):
    # InsnT tuple shape: (off, size, raw_bytes, asm)
    return (0, len(asm), b"", asm)


@pytest.fixture(autouse=True)
def _no_trace(monkeypatch):
    """Force the static path: make the trace lookup unavailable."""
    def _boom(*a, **k):
        raise RuntimeError("no trace image in tests")
    monkeypatch.setattr(regalloc_hints, "_lookup", _boom)


def test_no_byte_swap_returns_none():
    assert byte_seat_hints.detect("f", [_reg_swap("eax", "edx")]) is None


def test_case_c_rover_reextend(monkeypatch):
    # PS re-extends a byte from a non-A reg -> Rule 127 (de-name).
    monkeypatch.setattr(style_check, "_source_index", lambda: {})
    ps = [_insn("mov al, ch"), _insn("and eax, 0xff")]
    v = byte_seat_hints.detect("f", [_byte_swap("ch", "al")], ps_insns=ps)
    assert v is not None and v.case == "C"
    assert any("Rule 127" in ln for ln in v.lines)


def test_case_a_collateral_static(monkeypatch):
    # Byte swap dl<->al whose parents edx/eax also appear as a Reg swap.
    monkeypatch.setattr(style_check, "_source_index", lambda: {})
    hints = [_byte_swap("dl", "al"), _reg_swap("edx", "eax")]
    v = byte_seat_hints.detect("f", hints, ps_insns=[])
    assert v is not None and v.case == "A"
    assert any("Collateral" in ln for ln in v.lines)


def test_case_b_int_widen(monkeypatch):
    # Bare-AND uchar shape (no shifts) + a byte swap, no collateral -> Rule 126.
    src = """
    void f(void) {
        unsigned char kind;
        unsigned char flags;
        kind = g[0] & 0xc0;
        flags = g[1] & 0x3;
        h(kind, flags);
    }
    """
    ast = parse_c(src, "t.c")
    idx = {n.decl.name: ("t.c", n, 0) for n in ast.ext
           if isinstance(n, c_ast.FuncDef) and n.decl.name}
    monkeypatch.setattr(style_check, "_source_index", lambda: idx)
    v = byte_seat_hints.detect("f", [_byte_swap("dh", "dl")], file="t.c", ps_insns=[])
    assert v is not None and v.case == "B"
    assert any("Rule 126" in ln for ln in v.lines)


def _cascade(*lines):
    from c2.commands import cascade_hints
    return cascade_hints.CascadeVerdict("f", list(lines))


def test_case_e_cascade_savings_gap_rule157(monkeypatch):
    # Byte swap al<->dl collateral to a dword swap eax<->edx that the cascade
    # replay search classifies as 'needs a SAVINGS change' -> Rule 157.
    monkeypatch.setattr(style_check, "_source_index", lambda: {})
    from c2.commands import cascade_hints
    monkeypatch.setattr(cascade_hints, "detect", lambda *a, **k: _cascade(
        "Cascade: EAX<->EDX needs a SAVINGS change: PS's order has dir "
        "(sav=121) allocating after v (sav=120) -- savings-major."))
    hints = [_byte_swap("al", "dl"), _reg_swap("eax", "edx")]
    v = byte_seat_hints.detect("f", hints, ps_insns=[])
    assert v is not None and v.case == "E"
    assert v.savings_pair == "EAX<->EDX"
    assert any("Rule 157" in ln for ln in v.lines)
    assert any("SAVINGS GAP" in ln for ln in v.lines)


def test_cascade_tie_reorder_is_not_rule157(monkeypatch):
    # Cascade says the collateral dword swap is REACHABLE by TIE-REORDER
    # (equal savings) -> NOT Rule 157 -> the reorderable collateral CASE A.
    monkeypatch.setattr(style_check, "_source_index", lambda: {})
    from c2.commands import cascade_hints
    monkeypatch.setattr(cascade_hints, "detect", lambda *a, **k: _cascade(
        "Cascade: EAX<->EDX REACHABLE by TIE-REORDER: allocate v after dir "
        "(both sav=120)."))
    hints = [_byte_swap("al", "dl"), _reg_swap("eax", "edx")]
    v = byte_seat_hints.detect("f", hints, ps_insns=[])
    assert v is not None and v.case == "A"
    assert not any("Rule 157" in ln for ln in v.lines)


def test_cascade_undecidable_is_not_rule157(monkeypatch):
    # cascade returns None (too many rows / suppressed) -> do NOT over-claim
    # E; fall through to the collateral CASE A classification.
    monkeypatch.setattr(style_check, "_source_index", lambda: {})
    from c2.commands import cascade_hints
    monkeypatch.setattr(cascade_hints, "detect", lambda *a, **k: None)
    hints = [_byte_swap("al", "dl"), _reg_swap("eax", "edx")]
    v = byte_seat_hints.detect("f", hints, ps_insns=[])
    assert v is not None and v.case == "A"
    assert not any("Rule 157" in ln for ln in v.lines)


def test_case_a_equal_savings_not_rule157(monkeypatch):
    # Equal savings (120 == 120) -> NO gap -> falls through to the normal
    # reorderable byte-tie path, NOT Rule 157.
    monkeypatch.setattr(style_check, "_source_index", lambda: {})
    rt = {"alloc": [
        {"savings": 120, "regclass_name": "byte", "reg_name": "DL",
         "reg": 2, "nameclass_name": "temp"},
        {"savings": 120, "regclass_name": "dword", "reg_name": "EAX",
         "reg": 0, "nameclass_name": "user"},
    ]}
    monkeypatch.setattr(regalloc_hints, "_lookup", lambda *a, **k: (rt, None, None))
    import c2.commands.gb_hints as gb_hints
    monkeypatch.setattr(gb_hints, "detect", lambda *a, **k: [])
    v = byte_seat_hints.detect("f", [_byte_swap("al", "dl")], ps_insns=[])
    assert v is not None and v.case != "E"
    assert not any("Rule 157" in ln for ln in v.lines)


def test_static_hedge_when_ambiguous(monkeypatch):
    # Byte swap, no asm/AST/collateral signal, no trace -> honest ? hedge.
    monkeypatch.setattr(style_check, "_source_index", lambda: {})
    v = byte_seat_hints.detect("f", [_byte_swap("bl", "ch")], ps_insns=[])
    assert v is not None and v.case == "?"
    assert any("regtrace" in ln for ln in v.lines)

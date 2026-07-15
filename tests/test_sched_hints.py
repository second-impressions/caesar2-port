"""Tests for the eval-order scheduling hint (sched_hints)."""
from __future__ import annotations

from c2.commands import sched_hints as sh


def _row(kind, o_asm, r_asm):
    o = (0, 0, b"", o_asm) if o_asm is not None else None
    r = (0, 0, b"", r_asm) if r_asm is not None else None
    return {"kind": kind, "o": o, "r": r}


def test_order_swap_value_before_addr():
    # PS: shl (value) at row 0, addr at rows 1-2; RC: shl at row 2 (after addr).
    pairs = [
        ("shl bl, 4", "movsx edx, word ptr [0xf96a]"),
        ("movsx edx, word ptr [0x858b0]", "imul edx, edx, 0x3a"),
        ("imul edx, edx, 0x3a", "shl cl, 4"),
        ("add byte ptr [ecx+edx+t], bl", "add byte ptr [edx+ebx+u], cl"),
    ]
    res = sh._order_swap(pairs)
    assert res is not None
    mnem, ps_before = res
    assert mnem == "shl"
    assert ps_before is True


def test_no_swap_same_order():
    pairs = [
        ("movsx edx, word ptr [m]", "movsx edx, word ptr [m]"),
        ("shl bl, 4", "shl cl, 4"),
    ]
    assert sh._order_swap(pairs) is None


def test_imul3_is_address_not_value():
    assert sh._is_addr_op("imul edx, edx, 0x3a")
    assert not sh._is_value_op("imul edx, edx, 0x3a")
    assert sh._is_value_op("shl bl, 4")
    assert sh._is_value_op("imul eax, edx")  # 2-op imul is a value mul


def test_detect_requires_name_and_rows():
    assert sh.detect(None, [], [], rows=[]) is None
    assert sh.detect("f", [], [], rows=None) is None


def test_detect_combines_disasm_and_source(monkeypatch):
    rows = [
        _row("replace", "shl bl, 4", "movsx edx, word ptr [m]"),
        _row("equal", "imul edx, edx, 0x3a", "imul edx, edx, 0x3a"),
        _row("replace", "add byte ptr [ecx+edx+t], bl", "shl cl, 4"),
    ]
    # source index says this function has a hoistable RMW at line 42
    monkeypatch.setattr(sh, "_rmw_index",
                        lambda: {"fn": [(42, "a[j]", frozenset({"<<"}))]})
    h = sh.detect("fn", [], [], rows=rows)
    assert h is not None
    assert h.value_mnem == "shl"
    assert h.sites == [(42, "a[j]")]
    txt = sh.render(h)
    assert "line 42" in txt
    assert "scheduling" in txt.lower()


def test_detect_no_mem_rmw_no_fire(monkeypatch):
    # value-op swap exists + source site exists, but NO indexed-memory RMW in
    # the diff -> the shift is unrelated, so the gate suppresses it.
    rows = [
        _row("replace", "shl bl, 4", "movsx edx, word ptr [m]"),
        _row("equal", "imul edx, edx, 0x3a", "imul edx, edx, 0x3a"),
        _row("replace", "mov eax, ebx", "shl cl, 4"),   # no `add [..], reg`
    ]
    monkeypatch.setattr(sh, "_rmw_index", lambda: {"fn": [(42, "a[j]")]})
    assert sh.detect("fn", [], [], rows=rows) is None


def test_detect_no_source_site_no_fire(monkeypatch):
    rows = [
        _row("replace", "shl bl, 4", "movsx edx, word ptr [m]"),
        _row("equal", "imul edx, edx, 0x3a", "imul edx, edx, 0x3a"),
        _row("replace", "add [..], bl", "shl cl, 4"),
    ]
    monkeypatch.setattr(sh, "_rmw_index", lambda: {})  # no sites
    assert sh.detect("fn", [], [], rows=rows) is None


def test_rmw_visitor_flags_compound_subscript():
    from c2.commands.c_source import classify_source
    src = """
void f(unsigned char *a, int j, int step) {
    a[j] += step << 4;
    a[0] += 1;            /* const index, trivial rhs -> skip */
    a[j] = step;          /* not RMW -> skip */
}
"""
    fd = classify_source(src, "t.c")
    v = sh._RMWVisitor()
    v.visit(fd.func_defs[0])
    # only `a[j] += step << 4` qualifies
    assert len(v.sites) == 1
    assert v.sites[0][1].replace(" ", "") == "a[j]"
    assert "<<" in v.sites[0][2]   # rhs operator captured


def test_detect_op_class_mismatch_no_fire(monkeypatch):
    # disasm shows `sar`, but the source RMW RHS is `<<` -> operator class
    # mismatch -> suppressed (the evolve_land_value false-positive case).
    rows = [
        _row("replace", "sar bl, 4", "movsx edx, word ptr [m]"),
        _row("equal", "imul edx, edx, 0x3a", "imul edx, edx, 0x3a"),
        _row("replace", "add byte ptr [ecx+edx+t], bl", "sar cl, 4"),
    ]
    monkeypatch.setattr(sh, "_rmw_index",
                        lambda: {"fn": [(42, "a[j]", frozenset({"<<"}))]})
    assert sh.detect("fn", [], [], rows=rows) is None


def test_to_json_roundtrip():
    h = sh.SchedHint(value_mnem="shl", ps_value_before_addr=True,
                     sites=[(42, "a[j]")])
    j = sh.to_json(h)
    assert j["value_mnem"] == "shl"
    assert j["sites"] == [{"line": 42, "lhs": "a[j]"}]
    assert sh.to_json(None) is None

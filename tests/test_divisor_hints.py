"""Tests for the Rule 5/5c divisor predictor (c2.commands.divisor_hints).

The classifier walks the per-routine IR forest and tags each O_DIV / O_MOD
with a kind + (optionally) a rule id.  Tests forge minimal trace records
to exercise each branch independently.
"""
from __future__ import annotations

from c2.ir import (
    IRForest, Name, Node,
    TN_LEAF, TN_BINARY, TN_CONS,
    N_CONSTANT, N_MEMORY, N_TEMP, N_REGISTER,
    build_forest,
)
from c2.commands.divisor_hints import (
    O_DIV, O_MOD,
    classify_routine, _classify_one,
    DivisorHint, render_lines,
)


# ---- trace-record helpers -------------------------------------------------

def nb(ptr, cls, sub=0, name_id=0, line=0):
    return ("nb", [f"{ptr:x}", str(cls), str(sub), f"{name_id:x}", str(line)])


def tl(ptr, cls, payload, tipe=0, line=0):
    return ("tl", [f"{ptr:x}", str(cls), f"{payload:x}", f"{tipe:x}", str(line)])


def tn(ptr, cls, op, left, right, tipe=0, line=0):
    return ("tn", [f"{ptr:x}", str(cls), str(op),
                    f"{left:x}", f"{right:x}", f"{tipe:x}", str(line)])


# ---- happy paths ----------------------------------------------------------

def test_literal_pow2_divide_flags_rule_5():
    # gA = x / 2 -- divisor is a TN_CONS leaf wrapping a constant name.
    rec = [
        nb(0x100, N_CONSTANT, sub=0x10, line=5),   # the constant `2`
        tl(0xA00, TN_CONS, 0x100, line=5),         # constant leaf
        nb(0x200, N_MEMORY, sub=5, line=5),        # x
        tl(0xA10, TN_LEAF, 0x200, line=5),         # x leaf
        tn(0xB00, TN_BINARY, op=O_DIV, left=0xA10, right=0xA00, line=5),
    ]
    ir = build_forest(rec)
    classes = classify_routine(ir)
    assert len(classes) == 1
    c = classes[0]
    assert c.op == "/"
    assert c.kind == "literal_const"
    assert c.rule == "5"
    assert c.line == 5


def test_temp_divisor_no_rule():
    # x / temp_y -- divisor is N_TEMP wrapped in TN_LEAF.  No matching mod
    # -> not Rule 5c either, just informational.
    rec = [
        nb(0x100, N_TEMP, line=5),
        tl(0xA00, TN_LEAF, 0x100, line=5),
        nb(0x200, N_MEMORY, line=5),
        tl(0xA10, TN_LEAF, 0x200, line=5),
        tn(0xB00, TN_BINARY, op=O_DIV, left=0xA10, right=0xA00, line=5),
    ]
    ir = build_forest(rec)
    classes = classify_routine(ir)
    assert classes[0].kind == "temp_divisor"
    assert classes[0].rule is None


def test_shared_temp_divisor_div_and_mod_triggers_rule_5c():
    # x / d  and  x % d   where d is an N_TEMP name shared between both
    # operations -- the strong Rule 5c signal.
    rec = [
        nb(0x100, N_TEMP, line=5),                 # the temp divisor `d`
        tl(0xA00, TN_LEAF, 0x100, line=5),         # d leaf
        nb(0x200, N_MEMORY, line=5),               # x
        tl(0xA10, TN_LEAF, 0x200, line=5),         # x leaf for div
        tn(0xB00, TN_BINARY, op=O_DIV, left=0xA10, right=0xA00, line=5),
        # And the modulo at L6:
        tl(0xA20, TN_LEAF, 0x100, line=6),         # SAME d (same payload)
        tl(0xA30, TN_LEAF, 0x200, line=6),         # x for mod
        tn(0xB10, TN_BINARY, op=O_MOD, left=0xA30, right=0xA20, line=6),
    ]
    ir = build_forest(rec)
    classes = classify_routine(ir)
    # Both div and mod show up; div gets Rule 5c.
    div_cls = [c for c in classes if c.op == "/"]
    assert len(div_cls) == 1
    assert div_cls[0].kind == "shared_temp_5c"
    assert div_cls[0].rule == "5c"


def test_paired_const_div_mod_is_info_only_not_5c():
    # `/16` and `%16` of the SAME constant name.  Honest predictor: this
    # COULD trigger Rule 5c post-CSE but usually doesn't in wcc386.  Flag
    # as paired_const_div_mod, rule=None (info), not Rule 5c.
    rec = [
        nb(0x100, N_CONSTANT, sub=0x10, line=7),   # constant `16`
        tl(0xA00, TN_CONS, 0x100, line=7),         # const leaf for div
        nb(0x200, N_MEMORY, line=7),               # x
        tl(0xA10, TN_LEAF, 0x200, line=7),         # x leaf
        tn(0xB00, TN_BINARY, op=O_DIV, left=0xA10, right=0xA00, line=7),
        tl(0xA20, TN_CONS, 0x100, line=8),         # SAME constant via 2nd leaf
        tl(0xA30, TN_LEAF, 0x200, line=8),         # x for mod
        tn(0xB10, TN_BINARY, op=O_MOD, left=0xA30, right=0xA20, line=8),
    ]
    ir = build_forest(rec)
    classes = classify_routine(ir)
    div = [c for c in classes if c.op == "/"][0]
    assert div.kind == "paired_const_div_mod"
    assert div.rule is None
    # The mod still shows up as literal_const info.
    mod = [c for c in classes if c.op == "%"][0]
    assert mod.kind == "literal_const"
    assert mod.rule is None


def test_memory_divisor():
    rec = [
        nb(0x100, N_MEMORY, line=5),
        tl(0xA00, TN_LEAF, 0x100, line=5),
        nb(0x200, N_MEMORY, line=5),
        tl(0xA10, TN_LEAF, 0x200, line=5),
        tn(0xB00, TN_BINARY, op=O_DIV, left=0xA10, right=0xA00, line=5),
    ]
    ir = build_forest(rec)
    c = classify_routine(ir)[0]
    assert c.kind == "memory_divisor"
    assert c.rule is None


def test_register_divisor():
    rec = [
        nb(0x100, N_REGISTER, line=5),
        tl(0xA00, TN_LEAF, 0x100, line=5),
        nb(0x200, N_MEMORY, line=5),
        tl(0xA10, TN_LEAF, 0x200, line=5),
        tn(0xB00, TN_BINARY, op=O_DIV, left=0xA10, right=0xA00, line=5),
    ]
    ir = build_forest(rec)
    c = classify_routine(ir)[0]
    assert c.kind == "reg_divisor"


def test_variable_divisor_when_right_is_a_subexpression():
    # x / (y + 1) -- right is a TN_BINARY, not a leaf.
    rec = [
        nb(0x100, N_MEMORY, line=5),               # x
        tl(0xA00, TN_LEAF, 0x100, line=5),
        nb(0x200, N_MEMORY, line=5),               # y
        tl(0xA10, TN_LEAF, 0x200, line=5),
        nb(0x300, N_CONSTANT, line=5),             # 1
        tl(0xA20, TN_CONS, 0x300, line=5),
        tn(0xB00, TN_BINARY, op=1, left=0xA10, right=0xA20, line=5),  # y+1
        tn(0xB10, TN_BINARY, op=O_DIV, left=0xA00, right=0xB00, line=5),
    ]
    ir = build_forest(rec)
    c = classify_routine(ir)
    div = [x for x in c if x.op == "/"][0]
    assert div.kind == "var_divisor"
    assert "BINARY" in div.note


# ---- multi-divide / ordering / rendering ----------------------------------

def test_multiple_divides_sort_by_line():
    rec = [
        # L7 div
        nb(0x100, N_CONSTANT, line=7), tl(0xA00, TN_CONS, 0x100, line=7),
        nb(0x200, N_MEMORY, line=7),   tl(0xA10, TN_LEAF, 0x200, line=7),
        tn(0xB00, TN_BINARY, op=O_DIV, left=0xA10, right=0xA00, line=7),
        # L5 div (earlier source line, emitted later in trace)
        nb(0x300, N_CONSTANT, line=5), tl(0xA20, TN_CONS, 0x300, line=5),
        nb(0x400, N_MEMORY, line=5),   tl(0xA30, TN_LEAF, 0x400, line=5),
        tn(0xB10, TN_BINARY, op=O_DIV, left=0xA30, right=0xA20, line=5),
    ]
    ir = build_forest(rec)
    classes = classify_routine(ir)
    assert [c.line for c in classes] == [5, 7]


def test_render_lines_compact():
    h = DivisorHint(func="f", divides=[
        type(_classify_one)(  # fake DivClass-like
        )  # noqa
    ]) if False else None
    # Use the real classifier for clean render output.
    rec = [
        nb(0x100, N_CONSTANT, line=5),
        tl(0xA00, TN_CONS, 0x100, line=5),
        nb(0x200, N_MEMORY, line=5),
        tl(0xA10, TN_LEAF, 0x200, line=5),
        tn(0xB00, TN_BINARY, op=O_DIV, left=0xA10, right=0xA00, line=5),
    ]
    ir = build_forest(rec)
    h = DivisorHint(func="f", divides=classify_routine(ir))
    lines = render_lines(h)
    assert any("Rule 5: 1" in l for l in lines)
    assert any("L5" in l and "/" in l and "Rule 5" in l for l in lines)


def test_routine_with_no_divides_returns_empty():
    rec = [
        nb(0x100, N_MEMORY, line=5),
        tl(0xA00, TN_LEAF, 0x100, line=5),
        tn(0xB00, 4, op=0, left=0xA00, right=0xA00, line=5),  # TN_ASSIGN
    ]
    ir = build_forest(rec)
    assert classify_routine(ir) == []

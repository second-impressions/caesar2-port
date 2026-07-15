"""Tests for the per-statement PS<->RC line-cue map (c2.commands.stmt_map)."""
from c2.commands import stmt_map as SM


def _row(kind, o_off=None, r_off=None):
    o = (o_off, 2, b"\x90\x90", "nop") if o_off is not None else None
    r = (r_off, 2, b"\x90\x90", "nop") if r_off is not None else None
    return {"kind": kind, "o": o, "r": r}


def test_stmt_map_one_to_one_and_split():
    rows = [
        _row("equal", 0, 0),      # prologue (no cue)
        _row("equal", 2, 2),      # PS L+3 starts, RC L+5 starts
        _row("equal", 4, 4),
        _row("equal", 6, 6),      # PS L+4 starts, RC L+6 starts
        _row("replace", 8, 8),    # RC L+7 ALSO starts here -> SPLIT
        _row("equal", 10, 10),    # PS L+6 / RC L+9
    ]
    ps = {2: "L+3", 6: "L+4", 10: "L+6"}
    rc = {2: "L+5", 6: "L+6", 8: "L+7", 10: "L+9"}
    h = SM.build("f", rows, ps, rc)
    assert h is not None
    assert len(h.segs) == 3
    assert h.n_one_to_one == 2
    seg2 = h.segs[1]
    assert seg2.ps_cue == "L+4"
    assert seg2.rc_cues == ["L+6", "L+7"]      # the SPLIT
    assert seg2.has_diff                        # replace row inside
    out = SM.render_lines(h)
    assert out and "SPLIT" in out[0]
    assert "3 PS statement(s), 2 map 1:1" in out[0]


def test_stmt_map_rc_continues_prev_line():
    rows = [
        _row("equal", 0, 0),      # PS L+3 / RC L+5
        _row("replace", 2, 2),    # PS L+4 starts; RC has NO cue (continues)
    ]
    ps = {0: "L+3", 2: "L+4"}
    rc = {0: "L+5"}
    h = SM.build("f", rows, ps, rc)
    odd = [s for s in h.segs if len(s.rc_cues) != 1]
    assert len(odd) == 1 and odd[0].ps_cue == "L+4"
    out = SM.render_lines(h)
    assert "RC continues prev line" in out[0]


def test_stmt_map_empty_rows():
    assert SM.build("f", [], {}, {}) is None


def test_structural_ops_excludes_leaves():
    from c2.tree_diff import TreeShape
    sh = TreeShape(op="BINARY:O_PLUS", children=[
        TreeShape(op="LEAF:MEMORY"), TreeShape(op="LEAF:CONSTANT")])
    ops = SM._structural_ops([sh])
    assert ops == {"BINARY:O_PLUS": 1}


def test_stmt_ir_suppresses_representation_artifacts():
    """A PS-only COMPARE recovered from `cmp+jcc` that our RC asm ALSO
    contains is a representation artifact (the forward tree folds truth
    tests) and must NOT be reported as PS-only."""
    from collections import Counter
    from c2 import binir
    from c2.tree_diff import shape_from_binir_ops
    from c2.commands.stmt_map import _structural_ops

    # identical cmp+jcc on both sides
    insns = [
        (0, 3, b"\x83\xfa\x20", "cmp edx, 0x20"),
        (3, 2, b"\x7d\x0c", "jge 0x11"),
    ]
    r_ops = _structural_ops(shape_from_binir_ops(binir.recover(insns)))
    rc_ops = _structural_ops(shape_from_binir_ops(binir.recover(insns)))
    f_ops = Counter()           # forward tree folded the truth test
    rev_only = (r_ops - f_ops) - rc_ops
    assert not rev_only

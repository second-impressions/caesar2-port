"""Tests for `c2 shape-recon` (witness-reconciliation shape inference).

Pure-function tests (alignment, similarity, classification) run always.
Witness-A/C tests that need PS.EXE artifacts skip when the data files
aren't present.  Witness-B (Mac) is never exercised here -- it requires
the Ghidra JVM and is covered by the live corpus run.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from c2.commands import shape_recon as sr
from c2.commands.shape_recon import (
    Statement, MacStmt, RcStmt, _jaccard, _construct_compat, _sim, _align,
    _rc_correspondence, build_skeleton, ps_statement_spine, witness_c,
)

_HAS_PS = Path("data/out/symbols.json").exists() and Path("data/out/le_code.bin").exists()
_PS_ONLY = pytest.mark.skipif(not _HAS_PS, reason="PS.EXE artifacts absent")

# A function known to exist with -d1 line records (the worked example).
_FN = "place2_a_building_base"


# ── pure helpers ────────────────────────────────────────────────────────


def test_jaccard():
    assert _jaccard([], []) == 0.0
    assert _jaccard(["a"], ["a"]) == 1.0
    assert _jaccard(["a", "b"], ["b", "c"]) == pytest.approx(1 / 3)
    assert _jaccard(["a"], ["b"]) == 0.0


def test_canon_ps_ops():
    from c2.commands.shape_recon import _canon_ps_ops
    got = set(_canon_ps_ops({
        "BINARY:O_TIMES": 4, "UNARY:O_CONVERT": 1,
        "COMPARE:O_CMP_LESS": 1, "BINARY:O_LSHIFT": 1,
        "PRE_GETS:O_AND": 1, "ASSIGN": 1}))
    assert got == {"mul", "cast", "cmp", "and", "assign"}


def test_mac_ops():
    from c2.commands.shape_recon import _mac_ops
    from c2.mac.clean import clean_decompile_ast
    raw = """
void f(void)
{
  int x;
  x = (a << 8) + b;
  if (c < 3) { g(); }
}
"""
    import pycparser.c_ast as ca
    fdef, _ = clean_decompile_ast(raw, globals_set=frozenset())
    body = fdef.body.block_items
    assign = next(n for n in body if isinstance(n, ca.Assignment))
    iff = next(n for n in body if isinstance(n, ca.If))
    assign_ops = set(_mac_ops(assign))   # x = (a<<8)+b
    assert "mul" in assign_ops and "add" in assign_ops and "assign" in assign_ops
    if_ops = set(_mac_ops(iff.cond))     # c < 3
    assert "cmp" in if_ops


def test_sim_expr_shape_helps_anchorless():
    # two statements with NO name anchors: the one whose computation shape
    # matches the Mac statement scores higher.
    s = _mk_stmt(0, c_ops={"BINARY:O_LSHIFT": 1, "BINARY:O_PLUS": 1})
    good = _mk_mac("assign")
    good.ops = ["mul", "add"]
    bad = _mk_mac("assign")
    bad.ops = ["div", "cmp"]
    assert _sim(s, good) > _sim(s, bad)


def test_construct_compat():
    branch_ops = {"COMPARE:O_NE": 1, "COND_BRANCH": 1}
    call_ops = {"CALL": 1}
    assign_ops = {"ASSIGN": 1, "BINARY:O_PLUS": 1}
    assert _construct_compat(branch_ops, "if") == 1.0
    assert _construct_compat(call_ops, "if") < 0.5       # call IR, if construct
    assert _construct_compat(call_ops, "call") == 1.0
    assert _construct_compat(assign_ops, "assign") == 1.0


def _mk_stmt(idx, calls=(), globs=(), cmp_consts=(), c_ops=None):
    return Statement(
        idx=idx, ps_line=idx, ps_line_rel=f"L+{idx}", byte_span=(idx, idx + 1),
        multi_stmt=False, backward=False, a_calls=list(calls),
        a_globals=list(globs), a_cmp_consts=list(cmp_consts),
        c_ops=c_ops or {})


def _mk_mac(construct, calls=(), globs=(), cmp_consts=(), consts=()):
    return MacStmt(construct=construct, nesting=[], calls=list(calls),
                   globals=list(globs), consts=list(consts),
                   cmp_consts=list(cmp_consts), types={}, line=0, expr="")


def test_sim_call_anchor_dominates():
    s = _mk_stmt(0, calls=["set_prov_ambient"])
    good = _mk_mac("call", calls=["set_prov_ambient"])
    bad = _mk_mac("call", calls=["unrelated"])
    assert _sim(s, good) > _sim(s, bad)
    assert _sim(s, good) >= 3.0


def test_sim_cmp_const_anchor():
    s = _mk_stmt(0, cmp_consts=[4], c_ops={"COMPARE:O_NE": 1, "COND_BRANCH": 1})
    good = _mk_mac("if", cmp_consts=[4])
    bad = _mk_mac("if", cmp_consts=[8])
    assert _sim(s, good) > _sim(s, bad)


def test_align_monotonic_and_correct():
    # three spine statements, three mac statements, anchors make the
    # diagonal the obvious alignment.
    spine = [
        _mk_stmt(0, calls=["fa"]),
        _mk_stmt(1, cmp_consts=[7], c_ops={"COMPARE:O_NE": 1}),
        _mk_stmt(2, globs=["g_x"]),
    ]
    macs = [
        _mk_mac("call", calls=["fa"]),
        _mk_mac("if", cmp_consts=[7]),
        _mk_mac("assign", globs=["g_x"]),
    ]
    m = _align(spine, macs)
    assert m.get(0, (None,))[0] == 0
    assert m.get(1, (None,))[0] == 1
    assert m.get(2, (None,))[0] == 2
    # monotonic: matched mac indices strictly increase with spine index
    matched = [m[i][0] for i in sorted(m)]
    assert matched == sorted(matched)


def test_align_skips_unanchored():
    # a spine statement with no anchors should not force a spurious match
    spine = [_mk_stmt(0, calls=["fa"]), _mk_stmt(1)]
    macs = [_mk_mac("call", calls=["fa"]), _mk_mac("other")]
    m = _align(spine, macs)
    assert m.get(0, (None,))[0] == 0
    # stmt 1 has no anchors -> sim with "other" is only the construct prior;
    # may or may not match, but must never match BACKWARD to mac 0.
    if 1 in m:
        assert m[1][0] >= 1


# ── RC correspondence (pure logic) ──────────────────────────────────────


def _rc(line, calls=(), cmp_consts=()):
    return RcStmt(construct="other", nesting=[], calls=list(calls), globals=[],
                  consts=[], cmp_consts=list(cmp_consts), types={}, line=line,
                  expr="", rel_off=line)


def test_rc_correspondence_split_and_1to1():
    # ps0 (anchored) should SPLIT: it owns rc0 (matched) + rc1 (anchored,
    # unmatched, attributed to ps0).  ps1 should be 1:1 with rc2.
    ps = [_mk_stmt(0, calls=["fa"], cmp_consts=[1]),
          _mk_stmt(1, calls=["fb"], cmp_consts=[2])]
    rc = [_rc(700, calls=["fa"]),        # -> ps0
          _rc(701, cmp_consts=[9]),      # anchored, unmatched -> attaches ps0
          _rc(702, calls=["fb"])]        # -> ps1
    _rc_correspondence(ps, rc)
    assert ps[0].rc_rel == "SPLIT"
    assert "L700" in ps[0].rc_cues and "L701" in ps[0].rc_cues
    assert ps[1].rc_rel == "1:1"
    assert ps[1].rc_cues == ["L702"]


def test_trajectory_reorder_vs_packing():
    from c2.commands.shape_recon import _trajectory
    # PS direction trajectory + - + ; RC + + + at the SAME offsets -> a real
    # reorder (choose_odd_tune-style): one switch that doesn't line up.
    ps = [(0, 10), (10, 11), (20, 9), (30, 12)]
    rc = [(0, 100), (10, 101), (20, 102), (30, 103)]
    t = _trajectory(ps, rc)
    assert t["switch_mismatch"] == 1 and t["mismatch_offsets"] == [20]
    assert t["ratio"] < 1.0


def test_trajectory_packing_invariant():
    from c2.commands.shape_recon import _trajectory
    # identical trajectory, RC just SPLITS a statement (extra mark) and uses
    # different absolute line numbers -> NOT a trajectory divergence.
    ps = [(0, 10), (10, 11), (20, 12)]
    rc = [(0, 700), (5, 700), (10, 701), (20, 702)]   # split mark at +5
    t = _trajectory(ps, rc)
    assert t["switch_mismatch"] == 0


def test_layout_aligned():
    from c2.commands.shape_recon import _layout_aligned
    # mov eax,[0x1000]; ret  vs  mov eax,[0x2000]; ret -- different address
    # bytes (a fixup) but IDENTICAL instruction layout.
    a = bytes([0xA1, 0, 0x10, 0, 0, 0xC3])
    b = bytes([0xA1, 0, 0x20, 0, 0, 0xC3])
    assert _layout_aligned(a, b)
    # nop; ret -- different layout
    assert not _layout_aligned(a, bytes([0x90, 0xC3]))
    assert not _layout_aligned(b"", a)


def test_rc_correspondence_exact_split_merge():
    from c2.commands.shape_recon import _rc_correspondence_exact

    def ps(i, a, b):
        return Statement(idx=i, ps_line=i, ps_line_rel=f"L+{i}",
                         byte_span=(a, b), multi_stmt=False, backward=False)

    def rc(off, line):
        return RcStmt("other", [], [], [], [], [], {}, line, "", off)

    stmts = [ps(0, 0, 10), ps(1, 10, 20), ps(2, 20, 30)]
    # RC marks: 0 -> ps0 (1:1); 12 & 16 -> ps1 (SPLIT); none in ps2 (MERGE)
    _rc_correspondence_exact(stmts, [rc(0, 100), rc(12, 112), rc(16, 116)])
    assert stmts[0].rc_rel == "1:1"
    assert stmts[1].rc_rel == "SPLIT" and stmts[1].rc_cues == ["L112", "L116"]
    assert stmts[2].rc_rel == "MERGE" and stmts[2].rc_cues == []


def test_rc_correspondence_clean_no_false_split():
    # well-transcribed: each PS statement maps to exactly one RC statement.
    ps = [_mk_stmt(0, calls=["fa"]), _mk_stmt(1, calls=["fb"])]
    rc = [_rc(700, calls=["fa"]), _rc(701, calls=["fb"])]
    _rc_correspondence(ps, rc)
    assert all(s.rc_rel != "SPLIT" for s in ps)
    assert ps[0].rc_cues == ["L700"] and ps[1].rc_cues == ["L701"]


# ── witness A / C against PS.EXE ────────────────────────────────────────


@_PS_ONLY
def test_spine_basic():
    spine = ps_statement_spine(_FN)
    assert spine is not None
    assert spine["file"].endswith(".c")
    ents = spine["entries"]
    assert len(ents) > 10
    # the worked example compares ebx against 4/8/0xc/0x10 -> cmp_consts present
    all_cmp = {c for e in ents for c in e.cmp_consts}
    assert 4 in all_cmp and 8 in all_cmp
    # and calls a known helper
    all_calls = {c for e in ents for c in e.calls}
    assert any("place_i" in c or "set_prov" in c for c in all_calls)


@_PS_ONLY
def test_witness_c_nontrivial():
    spine = ps_statement_spine(_FN)
    nontrivial = 0
    for e in spine["entries"]:
        ms, summ = witness_c(e)
        if ms:
            nontrivial += 1
    assert nontrivial >= 5


@_PS_ONLY
def test_build_skeleton_no_mac():
    sk = build_skeleton(_FN, use_mac=False)
    assert sk is not None
    assert sk.func == _FN
    assert len(sk.statements) > 10
    assert sk.mac_total == 0 and sk.mac_aligned == 0
    # without Mac, no statement can be "high" (needs all three witnesses)
    assert sk.n_high == 0
    assert 0.0 <= sk.agreement_score <= 1.0
    # every statement carries a confidence + byte span
    for st in sk.statements:
        assert st.confidence in ("high", "medium", "low")
        assert st.byte_span[1] >= st.byte_span[0]


@_PS_ONLY
def test_build_skeleton_unknown_fn():
    assert build_skeleton("not_a_real_function_xyz", use_mac=False) is None


# ── Mac AST accessor (no JVM: parse a synthetic Ghidra snippet) ──────────


def test_clean_decompile_ast_parses():
    from c2.mac.clean import clean_decompile_ast
    raw = """
void f(void)
{
  int iVar1;
  iVar1 = 3;
  if (iVar1 == 4) {
    return;
  }
  return;
}
"""
    fdef, err = clean_decompile_ast(raw, globals_set=frozenset())
    assert err is None
    assert fdef is not None
    assert fdef.decl.name == "f"


def test_clean_decompile_ast_parses_ghidra_bool_local():
    from c2.mac.clean import clean_decompile_ast
    raw = """
int f(void)
{
  bool bVar1;
  bVar1 = false;
  if (bVar1) {
    return 1;
  }
  return 0;
}
"""
    fdef, err = clean_decompile_ast(raw, globals_set=frozenset())
    assert err is None
    assert fdef is not None
    assert fdef.decl.name == "f"


def test_lower_mac_extracts_constructs_and_anchors():
    from c2.mac.clean import clean_decompile_ast
    raw = """
void f(void)
{
  int iVar1;
  iVar1 = g_style;
  if (iVar1 == 4) {
    helper(iVar1);
    other();
  }
  return;
}
"""
    fdef, err = clean_decompile_ast(raw, globals_set=frozenset({"g_style"}))
    assert err is None
    macs = sr._lower_mac(fdef, frozenset({"g_style"}))
    constructs = [m.construct for m in macs]
    assert "if" in constructs
    # multi-stmt body is NOT folded -> the calls appear as separate stmts
    assert any("helper" in m.calls for m in macs)
    # cmp const 4 is captured on the if condition
    if_stmt = next(m for m in macs if m.construct == "if")
    assert 4 in if_stmt.cmp_consts


def test_single_simple():
    import pycparser.c_ast as ca
    from c2.mac.clean import clean_decompile_ast
    raw = """
void f(void)
{
  if (g == 1) call_a();
  if (g == 2) { x = 3; y = 4; }
}
"""
    fdef, _ = clean_decompile_ast(raw, globals_set=frozenset({"g"}))
    body = fdef.body.block_items
    # first if: single-call body -> _single_simple returns the call
    assert sr._single_simple(body[0].iftrue) is not None
    # second if: two-statement compound -> not simple
    assert sr._single_simple(body[1].iftrue) is None


def test_lower_mac_folds_guarded_single_call():
    # `if (cond) call();` folds into ONE MacStmt carrying both the
    # condition's cmp-const AND the body call anchor (guard-line shape).
    from c2.mac.clean import clean_decompile_ast
    raw = """
void f(void)
{
  if (pointer_mode == 1) show_move();
  else if (pointer_mode == 2) show_aim();
}
"""
    fdef, err = clean_decompile_ast(raw, globals_set=frozenset({"pointer_mode"}))
    assert err is None
    macs = sr._lower_mac(fdef, frozenset({"pointer_mode"}))
    ifs = [m for m in macs if m.construct == "if"]
    assert len(ifs) == 2
    # each folded if carries its cmp const AND the body call
    first = ifs[0]
    assert 1 in first.cmp_consts and "show_move" in first.calls
    second = ifs[1]
    assert 2 in second.cmp_consts and "show_aim" in second.calls
    # no standalone call stmts emitted (bodies were folded)
    assert not any(m.construct == "call" for m in macs)

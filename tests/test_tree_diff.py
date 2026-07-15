"""Tests for the unified tree shape + diff (c2.tree_diff).

Covers:
  * shape_from_ir_forest -- forward-path adapter for c2.ir.Node trees.
  * shape_from_binir_ops -- reverse-path adapter for c2.binir.RecoveredOp.
  * tree_diff -- structural comparison, with op-mismatch / child-count /
    only-in-A / only-in-B difference kinds.
  * The end-to-end use case: identical sources should produce matching
    trees from BOTH directions.
"""
from __future__ import annotations

from c2.binir import RecoveredOp
from c2.ir import (
    Name, Node,
    TN_LEAF, TN_BINARY, TN_ASSIGN, TN_CONS,
    N_MEMORY, N_CONSTANT,
)
from c2.tree_diff import (
    TreeShape,
    shape_from_node,
    shape_from_ir_forest,
    shape_from_binir_ops,
    tree_diff,
    trees_match,
    _CG_OP_NAMES,
)


# ── shape_from_node (forward path) ────────────────────────────────────────

def _mkname(ptr: int, cls: int, line: int = 0):
    return Name(ptr=ptr, cls=cls, subcls=0, name_id=0, seq=0, ord_all=0,
                line=line)


def _mkleaf(ptr: int, name_cls: int):
    nm = _mkname(ptr + 0x1000, name_cls)
    return Node(ptr=ptr, kind="tl", cls=TN_LEAF, tipe=0, payload=nm.ptr,
                name=nm, line=1)


def _mkconst(ptr: int, value: int):
    nm = Name(ptr=ptr + 0x1000, cls=N_CONSTANT, subcls=0,
              name_id=value, seq=0, ord_all=0, line=0)
    return Node(ptr=ptr, kind="tl", cls=TN_CONS, tipe=0, payload=nm.ptr,
                name=nm, line=1)


def test_shape_from_node_leaf():
    s = shape_from_node(_mkleaf(0x100, N_MEMORY))
    assert s.op == "LEAF:MEMORY"
    assert s.children == []


def test_shape_from_node_assign_with_binary_and():
    """`X = X & MASK` -- TN_ASSIGN(LEAF, BINARY(O_AND, LEAF, CONS))."""
    lhs = _mkleaf(0x100, N_MEMORY)
    same_lhs = _mkleaf(0x110, N_MEMORY)
    mask = _mkconst(0x200, 0xfc)
    binop = Node(ptr=0x300, kind="tn", cls=TN_BINARY, tipe=0,
                 op=9,    # O_AND
                 left=same_lhs, right=mask, line=1)
    assign = Node(ptr=0x400, kind="tn", cls=TN_ASSIGN, tipe=0, op=0,
                  left=lhs, right=binop, line=1)
    s = shape_from_node(assign)
    assert s.op == "ASSIGN"
    assert len(s.children) == 2
    assert s.children[0].op == "LEAF:MEMORY"
    assert s.children[1].op == "BINARY:O_AND"
    assert s.children[1].children[0].op == "LEAF:MEMORY"
    assert s.children[1].children[1].op == "LEAF:CONSTANT"


def test_cg_op_names_include_common_ops():
    """Critical opcode names must be exposed -- consumers grep for these."""
    assert _CG_OP_NAMES[9] == "O_AND"
    assert _CG_OP_NAMES[10] == "O_OR"
    assert _CG_OP_NAMES[7] == "O_DIV"
    assert _CG_OP_NAMES[8] == "O_MOD"
    assert _CG_OP_NAMES[5] == "O_TIMES"


# ── shape_from_binir_ops (reverse path) ──────────────────────────────────

def test_shape_from_binir_g_div2():
    op = RecoveredOp(kind="g_div2", offset=0x10, length=7,
                     detail={"dst": "eax"}, op="OP_DIV(*, 2)",
                     note="By2Div")
    shapes = shape_from_binir_ops([op])
    assert len(shapes) == 1
    s = shapes[0]
    assert s.op == "BINARY:O_DIV"
    assert s.origin == "reverse"
    assert s.children[1].op == "LEAF:CONSTANT"
    assert s.children[1].detail["value"] == 2


def test_shape_from_binir_mul_pow2():
    op = RecoveredOp(kind="mul_pow2", offset=0x20, length=3,
                     detail={"reg": "esi", "shift": 3, "factor": 8},
                     op="OP_MUL(esi, 8)", note="multiply by 8")
    s = shape_from_binir_ops([op])[0]
    assert s.op == "BINARY:O_TIMES"
    assert s.children[1].detail["value"] == 8


def test_shape_from_binir_zext_byte_load():
    op = RecoveredOp(kind="zext_byte_load", offset=0x30, length=8,
                     detail={"reg": "eax", "src": "[ecx+8]"},
                     op="OP_CONVERT_U8_U32", note="zext")
    s = shape_from_binir_ops([op])[0]
    assert s.op == "UNARY:O_CONVERT"
    assert len(s.children) == 1
    assert s.children[0].op == "LEAF:MEMORY"


def test_shape_from_binir_pre_gets_mem_const():
    """Direct-memory-RMW with constant -> PRE_GETS:O_<binop>(MEM, CONST)."""
    op = RecoveredOp(kind="pre_gets_mem_const", offset=0x50, length=7,
                     detail={"binop": "and", "cg_op": "O_AND",
                             "size": "byte", "mem": "0x1234", "imm": 0xfc},
                     op="PRE_GETS:O_AND([0x1234], 0xfc)")
    s = shape_from_binir_ops([op])[0]
    assert s.op == "PRE_GETS:O_AND"
    assert len(s.children) == 2
    assert s.children[0].op == "LEAF:MEMORY"
    assert s.children[1].op == "LEAF:CONSTANT"
    assert s.children[1].detail["value"] == 0xfc


def test_shape_from_binir_mov_mem_imm():
    op = RecoveredOp(kind="mov_mem_imm", offset=0x60, length=10,
                     detail={"size": "dword", "mem": "0x1234", "imm": 0x42},
                     op="ASSIGN([0x1234], 0x42)")
    s = shape_from_binir_ops([op])[0]
    assert s.op == "ASSIGN"
    assert s.children[0].op == "LEAF:MEMORY"
    assert s.children[1].op == "LEAF:CONSTANT"
    assert s.children[1].detail["value"] == 0x42


def test_shape_from_binir_call_with_args():
    op = RecoveredOp(kind="call_with_args", offset=0x70, length=18,
                     detail={"target": "0x1000", "argc": 2,
                             "args": ["1", "2"], "cleanup": 8},
                     op="CALL(0x1000, argc=2)")
    s = shape_from_binir_ops([op])[0]
    assert s.op == "CALL"
    assert len(s.children) == 2
    for c in s.children:
        assert c.op == "PARM"
        assert len(c.children) == 1
        assert c.children[0].op == "LEAF:?"


def test_shape_from_binir_branch_jmp():
    op = RecoveredOp(kind="branch_jmp", offset=0x80, length=5,
                     detail={"mnem": "jmp", "target": "0x100"},
                     op="GOTO(0x100)")
    s = shape_from_binir_ops([op])[0]
    assert s.op == "GOTO"
    assert s.children == []


def test_shape_from_binir_branch_flag_jcc():
    op = RecoveredOp(kind="branch_flag_jcc", offset=0x90, length=2,
                     detail={"mnem": "jnz", "target": "0x80"},
                     op="COND_BRANCH(O_CMP_NOT_EQUAL, 0x80)")
    s = shape_from_binir_ops([op])[0]
    assert s.op == "COND_BRANCH"
    assert s.children == []


def test_shape_from_binir_skips_unknown_kinds():
    """A RecoveredOp with an unknown kind doesn`t emit a tree node."""
    op = RecoveredOp(kind="future_pattern_not_yet_supported",
                     offset=0x40, length=5, detail={})
    assert shape_from_binir_ops([op]) == []


# ── tree_diff ─────────────────────────────────────────────────────────────

def _t(op: str, *kids, origin: str = "forward") -> TreeShape:
    return TreeShape(op=op, children=list(kids), origin=origin)


def test_tree_diff_identical_trees():
    a = _t("ASSIGN", _t("LEAF:MEMORY"), _t("LEAF:CONSTANT"))
    b = _t("ASSIGN", _t("LEAF:MEMORY"), _t("LEAF:CONSTANT"))
    assert tree_diff(a, b) == []
    assert trees_match(a, b) is True


def test_tree_diff_op_mismatch():
    a = _t("ASSIGN", _t("LEAF:MEMORY"))
    b = _t("PRE_GETS", _t("LEAF:MEMORY"))
    diffs = tree_diff(a, b)
    assert len(diffs) == 1
    assert diffs[0].kind == "op_mismatch"
    assert diffs[0].a == "ASSIGN" and diffs[0].b == "PRE_GETS"


def test_tree_diff_children_mismatch():
    a = _t("ASSIGN", _t("X"), _t("Y"))
    b = _t("ASSIGN", _t("X"))
    diffs = tree_diff(a, b)
    # 1 children-count diff + 1 only_in_a for the extra Y
    assert any(d.kind == "children_mismatch" for d in diffs)
    assert any(d.kind == "only_in_a" and d.a == "Y" for d in diffs)


def test_tree_diff_only_in_one_side():
    """When one side is None (no counterpart), diff lists `only_in_*`."""
    assert tree_diff(None, _t("X"))[0].kind == "only_in_b"
    assert tree_diff(_t("X"), None)[0].kind == "only_in_a"


def test_tree_diff_path_propagates():
    """Path shows where the mismatch is."""
    a = _t("ASSIGN", _t("LEAF:MEMORY"), _t("BINARY:O_AND",
                                            _t("LEAF:MEMORY"),
                                            _t("LEAF:CONSTANT")))
    b = _t("ASSIGN", _t("LEAF:MEMORY"), _t("BINARY:O_AND",
                                            _t("LEAF:MEMORY"),
                                            _t("LEAF:DIFFERENT")))
    diffs = tree_diff(a, b)
    assert len(diffs) == 1
    assert "[1][1]" in diffs[0].path


# ── End-to-end use case ─────────────────────────────────────────────────

def test_pretty_dump_includes_children():
    a = _t("ASSIGN", _t("LEAF:MEMORY"), _t("LEAF:CONSTANT"))
    dump = a.pretty()
    assert "ASSIGN" in dump
    assert "  LEAF:MEMORY" in dump   # indented child
    assert "  LEAF:CONSTANT" in dump


def test_rule17b_forward_vs_reverse_market_image_minimal():
    """A minimal forward/reverse diff that captures the Rule 17b
    asymmetry: the forward IR (with intermediate temp `s`) has an extra
    `ASSIGN(s, ...)` chain absent on the reverse side (where PS emitted
    direct memory RMW with no temp visible)."""
    # Forward: TN_ASSIGN(temp, BINARY(O_AND, LEAF, CONS))
    #          TN_ASSIGN(memory, LEAF(temp))
    s_name = _mkname(0x1000, 2)   # N_TEMP
    s_leaf_lhs = Node(ptr=0x100, kind="tl", cls=TN_LEAF, tipe=0,
                      payload=s_name.ptr, name=s_name, line=10)
    s_leaf_rhs = Node(ptr=0x110, kind="tl", cls=TN_LEAF, tipe=0,
                      payload=s_name.ptr, name=s_name, line=10)
    x_lhs = _mkleaf(0x200, N_MEMORY)
    mask = _mkconst(0x300, 0xfc)
    binand = Node(ptr=0x400, kind="tn", cls=TN_BINARY, tipe=0, op=9,
                  left=_mkleaf(0x210, N_MEMORY), right=mask, line=10)
    stmt1_fwd = Node(ptr=0x500, kind="tn", cls=TN_ASSIGN, tipe=0, op=0,
                     left=s_leaf_lhs, right=binand, line=10)
    stmt2_fwd = Node(ptr=0x600, kind="tn", cls=TN_ASSIGN, tipe=0, op=0,
                     left=x_lhs, right=s_leaf_rhs, line=11)

    fwd_shape_1 = shape_from_node(stmt1_fwd)
    fwd_shape_2 = shape_from_node(stmt2_fwd)
    assert fwd_shape_1.op == "ASSIGN"
    assert fwd_shape_1.children[1].op == "BINARY:O_AND"
    # The extra ASSIGN-to-temp chain is what makes the forward have MORE
    # statement nodes than the reverse (which would be just one
    # direct-memory-RMW node).
    assert fwd_shape_2.op == "ASSIGN"
    assert fwd_shape_2.children[1].op == "LEAF:TEMP"

"""Unit tests for the shared IR forest reconstruction (c2.ir).

Covers:
  * Per-event handlers (nb / tl / tb / tn / ni) populate fields correctly.
  * Bottom-up child resolution: a tn's left/right are wired to prior nodes.
  * Statement-root detection: TN_ASSIGN / TN_LV_ASSIGN nodes go in roots[].
  * Per-class name creation order is the ConfBefore tie-break input.
  * tl payloads resolve to nb names when the payload matches an nb ptr.
  * Builder ignores tags it doesn't know (defensive against schema growth).
"""
from __future__ import annotations

import pytest

from c2.ir import (
    IR_TAGS,
    IRForest,
    Name,
    Node,
    TN_ASSIGN,
    TN_BINARY,
    TN_CONS,
    TN_LEAF,
    TN_LV_ASSIGN,
    TN_PARM,
    TN_SIDE_EFFECT,
    TN_UNARY,
    N_CONSTANT,
    N_MEMORY,
    N_REGISTER,
    N_TEMP,
    build_forest,
)


# ---- record-builder helpers ------------------------------------------------

def nb(ptr, cls, sub=0, name_id=0, line=None):
    f = [f"{ptr:x}", str(cls), str(sub), f"{name_id:x}"]
    if line is not None: f.append(str(line))
    return ("nb", f)


def tl(ptr, cls, payload, tipe=0, line=None):
    f = [f"{ptr:x}", str(cls), f"{payload:x}", f"{tipe:x}"]
    if line is not None: f.append(str(line))
    return ("tl", f)


def tb(ptr, sub=0, tipe=0, start=0, length=8, line=None):
    f = [f"{ptr:x}", f"{sub:x}", f"{tipe:x}", str(start), str(length)]
    if line is not None: f.append(str(line))
    return ("tb", f)


def tn(ptr, cls, op, left, right, tipe=0, line=None):
    f = [f"{ptr:x}", str(cls), str(op),
         f"{left:x}", f"{right:x}", f"{tipe:x}"]
    if line is not None: f.append(str(line))
    return ("tn", f)


def ni(ptr, nops=2, line=None):
    f = [f"{ptr:x}", str(nops)]
    if line is not None: f.append(str(line))
    return ("ni", f)


# ---- core invariants -------------------------------------------------------

def test_ir_tags_is_complete():
    assert IR_TAGS == frozenset({"nb", "tl", "tb", "tn", "ni"})


def test_build_forest_empty():
    f = build_forest([])
    assert isinstance(f, IRForest)
    assert f.nodes == {} and f.names == [] and f.roots == [] and f.insns == []


def test_nb_populates_name_table_and_per_class_seq():
    rec = [
        nb(0x100, N_REGISTER, name_id=0x10),
        nb(0x200, N_REGISTER, name_id=0x20),
        nb(0x300, N_TEMP, name_id=0x30),
        nb(0x400, N_REGISTER, name_id=0x40),
        nb(0x500, N_TEMP, name_id=0x50),
    ]
    f = build_forest(rec)
    assert len(f.names) == 5
    assert [n.ord_all for n in f.names] == [0, 1, 2, 3, 4]
    # Per-class seq -- the ConfBefore tie-break input.
    regs = f.names_by_class[N_REGISTER]
    temps = f.names_by_class[N_TEMP]
    assert [n.ptr for n in regs] == [0x100, 0x200, 0x400]
    assert [n.seq for n in regs] == [0, 1, 2]
    assert [n.ptr for n in temps] == [0x300, 0x500]
    assert [n.seq for n in temps] == [0, 1]
    # Lookup by ptr resolves correctly.
    assert f.names_by_ptr[0x300] is temps[0]
    # Class-name string accessor.
    assert regs[0].cls_name == "REGISTER"
    assert temps[0].cls_name == "TEMP"


def test_tl_resolves_name_when_payload_matches_nb():
    rec = [
        nb(0x100, N_MEMORY, name_id=0x55),
        tl(0xA00, TN_LEAF, 0x100),     # payload matches nb above
        tl(0xA10, TN_CONS,  0x999),    # payload is a literal constant
    ]
    f = build_forest(rec)
    leaf = f.nodes[0xA00]
    assert leaf.kind == "tl"
    assert leaf.cls == TN_LEAF
    assert leaf.payload == 0x100
    assert leaf.name is f.names_by_ptr[0x100]
    cons = f.nodes[0xA10]
    assert cons.cls == TN_CONS
    assert cons.payload == 0x999
    assert cons.name is None             # 0x999 is a literal, not an nb ptr


def test_tn_resolves_left_right_via_bottom_up_emit():
    # tl events arrive BEFORE the tn that references them (bottom-up build).
    rec = [
        nb(0x100, N_TEMP),
        nb(0x200, N_TEMP),
        tl(0xA00, TN_LEAF, 0x100),
        tl(0xA10, TN_LEAF, 0x200),
        tn(0xB00, TN_BINARY, op=2, left=0xA00, right=0xA10),
    ]
    f = build_forest(rec)
    n = f.nodes[0xB00]
    assert n.cls == TN_BINARY
    assert n.left is f.nodes[0xA00]
    assert n.right is f.nodes[0xA10]
    # walk() is pre-order.
    walked = [w.ptr for w in n.walk()]
    assert walked == [0xB00, 0xA00, 0xA10]


def test_statement_roots_capture_assign_classes():
    rec = [
        nb(0x100, N_MEMORY),
        nb(0x200, N_MEMORY),
        tl(0xA00, TN_LEAF, 0x100),
        tl(0xA10, TN_LEAF, 0x200),
        tn(0xB00, TN_BINARY, op=2, left=0xA00, right=0xA10),
        tn(0xC00, TN_ASSIGN, op=0, left=0xA00, right=0xB00),    # gA = gB + ...
        tn(0xD00, TN_LV_ASSIGN, op=0, left=0xA10, right=0xB00), # *p = ...
        tn(0xE00, TN_UNARY, op=1, left=0xB00, right=0),         # not a stmt
    ]
    f = build_forest(rec)
    assert [r.ptr for r in f.roots] == [0xC00, 0xD00]
    assert f.statements() == f.roots
    assert all(r.is_statement() for r in f.roots)


def test_tb_bitfield_fields():
    rec = [tb(0xB00, sub=0x123, tipe=0x456, start=5, length=3)]
    f = build_forest(rec)
    n = f.nodes[0xB00]
    assert n.kind == "tb"
    assert n.sub_ptr == 0x123
    assert n.tipe == 0x456
    assert n.bit_start == 5
    assert n.bit_len == 3
    assert n.cls_name == "BIT_LVALUE"


def test_ni_collects_instruction_births():
    rec = [ni(0x1000, 2), ni(0x1054, 1), ni(0x10A8, 0)]
    f = build_forest(rec)
    assert [i.ptr for i in f.insns] == [0x1000, 0x1054, 0x10A8]
    assert [i.nops for i in f.insns] == [2, 1, 0]


def test_builder_ignores_unknown_tags():
    # Defensive: future schema growth (xx records etc.) must not crash.
    rec = [
        ("xx", ["1", "2", "3"]),
        nb(0x100, N_REGISTER),
        ("yy", ["foo"]),
    ]
    f = build_forest(rec)
    assert len(f.names) == 1
    assert f.names[0].ptr == 0x100


def test_node_walk_handles_orphan_left_right():
    # When tn's left/right reference unknown ptrs (no prior tl/tn event), the
    # node's left/right stay None.  walk() must still terminate.
    rec = [tn(0xB00, TN_BINARY, op=2, left=0xDEAD, right=0xBEEF)]
    f = build_forest(rec)
    n = f.nodes[0xB00]
    assert n.left is None and n.right is None
    assert list(n.walk()) == [n]


def test_assign_tree_with_resolved_chain():
    # Full pipeline: gA = gB + 1
    rec = [
        nb(0x100, N_MEMORY, name_id=0xAA00),     # gA
        nb(0x200, N_MEMORY, name_id=0xAA10),     # gB
        nb(0x300, N_CONSTANT, name_id=1),        # const 1
        tl(0xA00, TN_LEAF, 0x100),               # gA leaf
        tl(0xA10, TN_LEAF, 0x200),               # gB leaf
        tl(0xA20, TN_CONS, 0x300),               # const-1 leaf
        tn(0xB00, TN_BINARY, op=2, left=0xA10, right=0xA20),  # gB + 1
        tn(0xC00, TN_ASSIGN, op=0, left=0xA00, right=0xB00),  # gA = ...
    ]
    f = build_forest(rec)
    assert len(f.roots) == 1
    stmt = f.roots[0]
    lhs = stmt.left
    assert lhs.name is f.names_by_ptr[0x100]    # gA name resolved
    rhs = stmt.right
    assert rhs.cls == TN_BINARY
    assert rhs.left.name is f.names_by_ptr[0x200]   # gB
    assert rhs.right.cls == TN_CONS
    # The TN_CONS leaf's name resolves to the CONSTANT entry.
    assert rhs.right.name is f.names_by_ptr[0x300]


def test_per_class_seq_is_the_birth_order_lever():
    # Rule 28/115 source-side lever: per-class BIRTH order (AllocName call
    # order) is what the source code controls via declaration order.  Verify
    # the builder exposes it.  (NOTE: birth order is NOT the ConfBefore tie-
    # break input -- conflicts come out savings-sorted; see name_birth_order
    # vs name_list docstrings for the distinction.)
    rec = [
        nb(0x100, N_TEMP),
        nb(0x200, N_TEMP),
        nb(0x300, N_REGISTER),
        nb(0x400, N_TEMP),
    ]
    f = build_forest(rec)
    order = f.name_order(N_TEMP)
    assert [n.ptr for n in order] == [0x100, 0x200, 0x400]
    assert [n.seq for n in order] == [0, 1, 2]


def test_nodes_of_filter():
    rec = [
        nb(0x100, N_MEMORY),
        tl(0xA00, TN_LEAF, 0x100),
        tl(0xA10, TN_LEAF, 0x100),
        tn(0xB00, TN_BINARY, op=2, left=0xA00, right=0xA10),
        tn(0xC00, TN_ASSIGN, op=0, left=0xA00, right=0xB00),
    ]
    f = build_forest(rec)
    assigns = f.nodes_of(TN_ASSIGN, TN_LV_ASSIGN)
    assert [n.ptr for n in assigns] == [0xC00]
    bins = f.nodes_of(TN_BINARY)
    assert [n.ptr for n in bins] == [0xB00]


# ---- source-line propagation -----------------------------------------------

def test_line_propagates_to_all_record_kinds():
    rec = [
        nb(0x100, N_MEMORY, name_id=0x55, line=5),
        tl(0xA00, TN_LEAF, 0x100, line=5),
        tb(0xB00, sub=0x200, start=2, length=4, line=5),
        tn(0xC00, TN_BINARY, op=2, left=0xA00, right=0xB00, line=5),
        tn(0xD00, TN_ASSIGN, op=0, left=0xA00, right=0xC00, line=5),
        ni(0x1000, nops=2, line=5),
    ]
    f = build_forest(rec)
    assert f.names[0].line == 5
    assert f.nodes[0xA00].line == 5     # tl
    assert f.nodes[0xB00].line == 5     # tb
    assert f.nodes[0xC00].line == 5     # tn (binary)
    assert f.nodes[0xD00].line == 5     # tn (assign root)
    assert f.insns[0].line == 5
    # Stmt root carries its line for source-level diff hints.
    assert f.roots[0].line == 5


def test_line_absent_in_legacy_traces_is_none():
    # Older trace images don't emit the trailing line field; the builder
    # must treat the field as None (not raise, not default to 0).
    rec = [
        nb(0x100, N_TEMP),                # no line
        tl(0xA00, TN_LEAF, 0x100),        # no line
        tn(0xB00, TN_ASSIGN, op=0, left=0xA00, right=0),  # no line
        ni(0x1000, nops=1),               # no line
    ]
    f = build_forest(rec)
    assert f.names[0].line is None
    assert f.nodes[0xA00].line is None
    assert f.nodes[0xB00].line is None
    assert f.insns[0].line is None


def test_line_zero_means_synthetic_compiler_emit():
    # Records emitted BEFORE any front-end source-line marker has fired
    # (compiler init, runtime support, hw-register name births) carry
    # line=0 -- not None.  Consumers should treat 0 as "no source line"
    # but distinguish it from None ("trace image lacks the field").
    rec = [
        nb(0x100, N_REGISTER, line=0),    # hw reg name -- compiler init
        nb(0x200, N_MEMORY, line=7),      # source-level global
    ]
    f = build_forest(rec)
    assert f.names[0].line == 0          # NOT None
    assert f.names[1].line == 7


def test_stmt_roots_carry_distinct_source_lines():
    # Three statements at lines 5/6/7.  Statement roots' lines are the
    # source-side handle for diff hints ("the binary diff at L6 is...").
    rec = [
        nb(0x100, N_MEMORY, line=5),
        tl(0xA00, TN_LEAF, 0x100, line=5),
        tn(0xB00, TN_ASSIGN, op=0, left=0xA00, right=0, line=5),
        nb(0x200, N_MEMORY, line=6),
        tl(0xA10, TN_LEAF, 0x200, line=6),
        tn(0xB10, TN_ASSIGN, op=0, left=0xA10, right=0, line=6),
        nb(0x300, N_MEMORY, line=7),
        tl(0xA20, TN_LEAF, 0x300, line=7),
        tn(0xB20, TN_ASSIGN, op=0, left=0xA20, right=0, line=7),
    ]
    f = build_forest(rec)
    assert [r.line for r in f.roots] == [5, 6, 7]

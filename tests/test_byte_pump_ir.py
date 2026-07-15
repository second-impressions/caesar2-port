"""Tests for the IR-level Rule 119 detector: ``tree_diff.detect_byte_pump_chains``.

The detector finds workhorse-accumulator chains in a forward TreeShape list:
ASSIGN statements where the target LEAF is ALSO referenced inside the rvalue
subtree (the IR shape of a compound assign ``r = r <op> X``).  Repeated
self-referencing assigns on the same name_seq form a chain.
"""
from __future__ import annotations

from c2.tree_diff import (
    BytePumpChain,
    TreeShape,
    detect_byte_pump_chains,
)


def _leaf(seq: int) -> TreeShape:
    return TreeShape(op="LEAF:LEAF", detail={"name_seq": seq}, origin="forward")


def _const(val: int) -> TreeShape:
    return TreeShape(op="LEAF:CONSTANT", detail={"value": val}, origin="forward")


def _byte_load() -> TreeShape:
    return TreeShape(
        op="UNARY:O_CONVERT",
        children=[TreeShape(op="LEAF:MEMORY", origin="forward")],
        origin="forward",
    )


def _assign(target_seq: int, rvalue: TreeShape) -> TreeShape:
    return TreeShape(
        op="ASSIGN",
        children=[_leaf(target_seq), rvalue],
        origin="forward",
    )


def _lshift(left: TreeShape, k: int) -> TreeShape:
    return TreeShape(op="BINARY:O_LSHIFT",
                     children=[left, _const(k)],
                     origin="forward")


def _plus(left: TreeShape, right: TreeShape) -> TreeShape:
    return TreeShape(op="BINARY:O_PLUS",
                     children=[left, right],
                     origin="forward")


# ── Positive: classic byte-pump 24-bit shape ────────────────────────────────


def test_detects_24bit_pump_with_lshift_and_byte_zext():
    """Unfixed get_buffer_ofset IR shape:

        r = (uchar)byte0;
        r = r << 16;             // r <<= 16 in source
        r = r + (uchar)byte1 << 8;
        r = r + (uchar)byte2;

    The first stmt is `r = byte` (not self-ref), then 3 self-ref stmts.
    """
    R = 100  # r's name_seq
    shapes = [
        _assign(R, _byte_load()),                          # r = byte (not self-ref)
        _assign(R, _lshift(_leaf(R), 16)),                 # r = r << 16
        _assign(R, _plus(_leaf(R), _lshift(_byte_load(), 8))),  # r = r + (byte<<8)
        _assign(R, _plus(_leaf(R), _byte_load())),         # r = r + byte
    ]
    chains = detect_byte_pump_chains(shapes)
    assert len(chains) == 1
    c = chains[0]
    assert c.name_seq == R
    assert c.self_ref_count == 3
    assert c.has_lshift is True
    assert c.has_byte_zext_input is True
    assert c.stmt_indices == [1, 2, 3]


def test_detects_or_form():
    """The OR-accumulator pattern ``r |= byte << K`` also self-refs r."""
    R = 7
    shapes = [
        _assign(R, _byte_load()),
        _assign(R, TreeShape(op="BINARY:O_OR",
                              children=[_leaf(R), _lshift(_byte_load(), 8)],
                              origin="forward")),
        _assign(R, TreeShape(op="BINARY:O_OR",
                              children=[_leaf(R), _byte_load()],
                              origin="forward")),
    ]
    chains = detect_byte_pump_chains(shapes)
    assert len(chains) == 1
    assert chains[0].self_ref_count == 2


# ── Negative: non-pump shapes ──────────────────────────────────────────────


def test_pure_assigns_do_not_chain():
    """``r = expr`` (no self-ref) doesn't count as a chain link."""
    R = 1
    shapes = [
        _assign(R, _byte_load()),
        _assign(R, _byte_load()),
        _assign(R, _const(42)),
    ]
    # No rvalue references R -- no chain.
    assert detect_byte_pump_chains(shapes) == []


def test_threshold_min_self_ref():
    """A single compound assign isn't enough -- need ``min_self_ref`` of 2."""
    R = 1
    shapes = [
        _assign(R, _byte_load()),
        _assign(R, _lshift(_leaf(R), 8)),
    ]
    # Only 1 self-ref -- below default threshold of 2.
    assert detect_byte_pump_chains(shapes) == []
    # Lowering the threshold detects it.
    chains = detect_byte_pump_chains(shapes, min_self_ref=1)
    assert len(chains) == 1
    assert chains[0].self_ref_count == 1


def test_unrelated_names_get_separate_chains():
    """Two different names with their own self-ref chains are reported
    separately, ordered by strength."""
    A, B = 10, 20
    shapes = [
        _assign(A, _byte_load()),
        _assign(A, _lshift(_leaf(A), 8)),
        _assign(A, _plus(_leaf(A), _byte_load())),
        _assign(B, _byte_load()),
        _assign(B, _plus(_leaf(B), _const(1))),
        _assign(B, _plus(_leaf(B), _const(2))),
    ]
    chains = detect_byte_pump_chains(shapes)
    assert len(chains) == 2
    # Sorted by self_ref_count desc -- both are 2, so order ties.
    seqs = {c.name_seq for c in chains}
    assert seqs == {A, B}
    a_chain = next(c for c in chains if c.name_seq == A)
    assert a_chain.has_byte_zext_input is True
    assert a_chain.has_lshift is True
    b_chain = next(c for c in chains if c.name_seq == B)
    assert b_chain.has_byte_zext_input is False
    assert b_chain.has_lshift is False


def test_handles_non_assign_roots():
    """Non-ASSIGN roots (e.g. a CALL statement) are skipped without error."""
    R = 1
    shapes = [
        TreeShape(op="CALL", origin="forward"),
        _assign(R, _lshift(_leaf(R), 8)),
        _assign(R, _plus(_leaf(R), _byte_load())),
    ]
    chains = detect_byte_pump_chains(shapes)
    assert len(chains) == 1
    assert chains[0].self_ref_count == 2


def test_empty_input():
    assert detect_byte_pump_chains([]) == []


# ── BytePumpChain dataclass surface ────────────────────────────────────────


def test_chain_record_has_documented_fields():
    """Constructible by name -- the field set is part of the public API."""
    c = BytePumpChain(
        name_seq=42, self_ref_count=3,
        has_lshift=True, has_byte_zext_input=True,
        stmt_indices=[1, 2, 3],
    )
    assert c.name_seq == 42
    assert c.self_ref_count == 3
    assert c.has_lshift is True
    assert c.has_byte_zext_input is True
    assert c.stmt_indices == [1, 2, 3]

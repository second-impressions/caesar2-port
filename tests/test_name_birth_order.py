"""Tests for ``name_list`` vs ``name_birth_order`` -- two distinct views.

``name_list`` returns conflict-CREATION order from the ``cn``
(AddConflictNode-exit) trace stream: the order in which ``AddConflictNode``
was called, measured at the creation site, with each conflict's name ptr.
Creation order is driven by the back end's name-list/instruction walks --
not by front-end birth order.

``name_birth_order`` returns front-end ``AllocName`` order from the
instrumented ``nb`` stream: the source-side declaration order, i.e. the
lever the source author controls (Rule 28 / Rule 115).

These two views can DIFFER -- this file documents the difference.
"""
from __future__ import annotations

from c2.regalloc.trace import parse
from c2.regalloc import name_list, name_birth_order


def _trace_with_three_temps_in_specific_order():
    """Forge a trace where birth order and creation order are intentionally
    different.  ``cn`` carries the creation order; ``presort`` (the ConfList
    walk = reversed creation) is consistent with it; the ``nb`` stream is
    independent."""
    return (
        "~WV1 fb\n"
        "~WV1 fn\n"
        # nb births: ptr=200 first, 100 second, 300 third (deliberately
        # different from the conf-creation order).
        "~WV1 nb 200 2 4 4\n"           # N_TEMP, born 1st
        "~WV1 nb 100 2 4 4\n"           # N_TEMP, born 2nd
        "~WV1 nb 300 2 4 4\n"           # N_TEMP, born 3rd
        # cn: creation order C=30, B=20, A=10 (conf, name, class)
        "~WV1 cn 30 300 2\n"
        "~WV1 cn 20 200 2\n"
        "~WV1 cn 10 100 2\n"
        # presort (ConfList walk order): A=10 (s=3), B=20 (s=4), C=30 (s=3)
        # == reversed creation: consistent with the cn stream above
        "~WV1 sl 10 3\n"
        "~WV1 sl 20 4\n"
        "~WV1 sl 30 3\n"
        # al records: conf 10 -> name 100, conf 20 -> name 200, conf 30 -> name 300
        "~WV1 al 10 100 3 f 0 0 2 1\n"
        "~WV1 al 20 200 4 f 0 0 2 2\n"
        "~WV1 al 30 300 3 f 0 0 2 3\n"
        "~WV1 rg 10 1000003\n"          # EAX
        "~WV1 wr 10 0\n"
        "~WV1 rg 20 200000c\n"          # EBX
        "~WV1 wr 20 0\n"
        "~WV1 rg 30 4000030\n"          # ECX
        "~WV1 wr 30 0\n"
        "~WV1 fc\n"
    )


def test_creation_order_via_name_list_reads_cn_stream():
    r = parse(_trace_with_three_temps_in_specific_order())
    ro = r["routines"][0]
    creation = [e["conf"] for e in name_list(ro)]
    # cn stream order = ['30', '20', '10']
    assert creation == ["30", "20", "10"]
    # each entry carries the name ptr from the cn record
    assert [e["name"] for e in name_list(ro)] == ["300", "200", "100"]


def test_birth_order_via_name_birth_order_uses_nb_stream():
    r = parse(_trace_with_three_temps_in_specific_order())
    ro = r["routines"][0]
    # nb births were 200, 100, 300.  Joined with al.name:
    #   200 -> conf 20 (savings=4)
    #   100 -> conf 10 (savings=3)
    #   300 -> conf 30 (savings=3)
    birth = name_birth_order(ro)
    assert [e["name"] for e in birth] == ["200", "100", "300"]
    assert [e["conf"] for e in birth] == ["20", "10", "30"]
    assert [e["savings"] for e in birth] == [4, 3, 3]
    assert [e["reg_name"] for e in birth] == ["EBX", "EAX", "ECX"]


def test_birth_and_creation_order_can_disagree():
    r = parse(_trace_with_three_temps_in_specific_order())
    ro = r["routines"][0]
    creation = [e["conf"] for e in name_list(ro)]
    birth    = [e["conf"] for e in name_birth_order(ro)]
    # creation: 30, 20, 10 ; birth: 20, 10, 30 -- DIFFERENT views.
    assert creation != birth
    # But the set of conflicts is the same.
    assert sorted(creation) == sorted(birth)


def test_birth_order_returns_empty_when_no_ir_data():
    # Trace with regalloc records but NO nb stream.
    text = (
        "~WV1 fb\n"
        "~WV1 fn\n"
        "~WV1 cn 10 100 2\n"
        "~WV1 sl 10 3\n"
        "~WV1 al 10 100 3 f 0 0 2 1\n"
        "~WV1 rg 10 1000003\n"
        "~WV1 wr 10 0\n"
        "~WV1 fc\n"
    )
    r = parse(text)
    ro = r["routines"][0]
    assert name_birth_order(ro) == []
    # name_list still works -- it needs the cn stream (+ alloc for joins).
    assert [e["conf"] for e in name_list(ro)] == ["10"]


def test_birth_order_shows_names_with_no_conflict():
    # A name that was born but never became a conflict (eliminated as dead
    # temp / aliased away) appears with conf=None so callers SEE the gap.
    text = (
        "~WV1 nb 100 2 4 4\n"
        "~WV1 nb 200 2 4 4\n"           # this one will NOT have a matching al
        "~WV1 fb\n"
        "~WV1 fn\n"
        "~WV1 sl 10 3\n"
        "~WV1 al 10 100 3 f 0 0 2 1\n"  # only name 100 becomes a conflict
        "~WV1 rg 10 1000003\n"
        "~WV1 wr 10 0\n"
        "~WV1 fc\n"
    )
    r = parse(text)
    ro = r["routines"][0]
    birth = name_birth_order(ro)
    assert [e["name"] for e in birth] == ["100", "200"]
    assert birth[0]["conf"] == "10"
    assert birth[1]["conf"] is None        # gap visible
    assert birth[1]["nameclass"] == "TEMP"


def test_birth_order_with_other_class_arg():
    # name_birth_order defaults to N_TEMP=2, but can target any class.
    text = (
        "~WV1 nb 100 1 0 11\n"          # N_MEMORY (gA)
        "~WV1 nb 200 1 0 22\n"          # N_MEMORY (gB)
        "~WV1 nb 300 2 4 4\n"           # N_TEMP (filler, ignored)
        "~WV1 fb\n"
        "~WV1 fn\n"
        "~WV1 fc\n"
    )
    r = parse(text)
    ro = r["routines"][0]
    mem = name_birth_order(ro, cls=1)        # N_MEMORY
    assert [e["name"] for e in mem] == ["100", "200"]
    assert all(e["nameclass"] == "MEMORY" for e in mem)
    # N_TEMP class still works as default.
    tmp = name_birth_order(ro, cls=2)
    assert [e["name"] for e in tmp] == ["300"]

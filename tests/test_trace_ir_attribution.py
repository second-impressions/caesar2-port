"""Multi-function IR attribution via the fc-terminal-after-fb rule.

The compiler's per-routine event sequence (cf. c2.regalloc.trace docs):

    [tn/tl/nb/ni for routine K's front-end statements]
    fb[K]   -- RegAlloc enters
    [late inserts]
    fc[K]   -- Generate returns: routine K is done
    [tn/tl/nb/ni for routine K+1]
    fb[K+1] ...
    fc[K+1] ...

Generate is ALSO called per-statement (interim ``fc`` events).  Only the
``fc`` AFTER ``fb`` closes a routine; interim ones do not.
"""
from __future__ import annotations

from c2.regalloc.trace import parse


def _mk(*lines: str) -> str:
    return "\n".join(lines) + "\n"


def test_single_function_with_interim_fc():
    # 1 function, 2 interim fc + fb + terminal fc.
    text = _mk(
        "~WV1 nb a00 2 0 11",            # routine 0 build batch 1
        "~WV1 fc",                       # interim Generate (statement 1)
        "~WV1 nb a04 2 0 22",            # routine 0 build batch 2
        "~WV1 fc",                       # interim Generate (statement 2)
        "~WV1 nb a08 2 0 33",            # routine 0 build batch 3
        "~WV1 fb",                       # RegAlloc enters for routine 0
        "~WV1 nb a0c 3 0 44",            # late insert
        "~WV1 fc",                       # TERMINAL: routine 0 closes here
    )
    r = parse(text)
    assert len(r["routines"]) == 1
    ir = r["routines"][0]["ir"]
    # All 4 names belong to routine 0.
    assert [n.name_id for n in ir.names] == [0x11, 0x22, 0x33, 0x44]


def test_two_functions_separated_by_terminal_fc():
    text = _mk(
        # Routine 0: build, fb, late insert, terminal fc.
        "~WV1 nb a00 1 0 1",
        "~WV1 nb a04 2 0 2",
        "~WV1 fb",
        "~WV1 nb a08 3 0 3",
        "~WV1 fc",                       # routine 0 closes
        # Routine 1: build batches with interim fc, then fb, late, terminal fc.
        "~WV1 nb a0c 1 0 10",
        "~WV1 fc",                       # interim
        "~WV1 nb a10 2 0 20",
        "~WV1 fb",
        "~WV1 nb a14 3 0 30",
        "~WV1 fc",                       # routine 1 closes
    )
    r = parse(text)
    assert len(r["routines"]) == 2
    r0_ids = [n.name_id for n in r["routines"][0]["ir"].names]
    r1_ids = [n.name_id for n in r["routines"][1]["ir"].names]
    assert r0_ids == [0x1, 0x2, 0x3]
    assert r1_ids == [0x10, 0x20, 0x30]


def test_pre_fb_fc_events_do_not_close_routine_0():
    # Compiler init emits fc records BEFORE the first fb (no routine open yet).
    # Those records and any pre-fb IR records belong to routine 0.
    text = _mk(
        "~WV1 fc",                       # compiler init batch 1 (no routine)
        "~WV1 nb a00 3 0 99",            # routine 0 pre-build (hw reg names)
        "~WV1 fc",                       # compiler init batch 2 (no routine)
        "~WV1 nb a04 2 0 1",
        "~WV1 fb",
        "~WV1 fc",                       # terminal
    )
    r = parse(text)
    assert len(r["routines"]) == 1
    ids = [n.name_id for n in r["routines"][0]["ir"].names]
    assert ids == [0x99, 0x1]


def test_trace_with_no_fc_falls_back_to_last_routine_finalization():
    # Defensive: if the trace is truncated before terminal fc fires, the
    # parser's tail-finalize still closes the last routine.
    text = _mk(
        "~WV1 nb a00 2 0 7",
        "~WV1 fb",
        "~WV1 nb a04 3 0 8",
        # no terminal fc -- file ends here
    )
    r = parse(text)
    assert len(r["routines"]) == 1
    assert [n.name_id for n in r["routines"][0]["ir"].names] == [0x7, 0x8]


def test_statement_roots_belong_to_correct_routine():
    # Routine 0 builds an ASSIGN.  Routine 1 builds two ASSIGNs.  The forest
    # must not leak roots across the boundary.
    text = _mk(
        "~WV1 tl 100 0 0 0",
        "~WV1 tl 200 0 0 0",
        "~WV1 tn 300 4 0 100 200 0",     # routine 0's ASSIGN
        "~WV1 fb",
        "~WV1 fc",
        "~WV1 tl 100 0 0 0",             # routine 1 reuses the same ptr (free-list)
        "~WV1 tl 200 0 0 0",
        "~WV1 tn 300 4 0 100 200 0",     # routine 1's ASSIGN
        "~WV1 tl 400 0 0 0",
        "~WV1 tn 500 4 0 400 300 0",     # routine 1's 2nd ASSIGN
        "~WV1 fb",
        "~WV1 fc",
    )
    r = parse(text)
    assert len(r["routines"]) == 2
    assert len(r["routines"][0]["ir"].roots) == 1
    assert len(r["routines"][1]["ir"].roots) == 2

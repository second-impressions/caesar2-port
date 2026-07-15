"""Tests for the Rule 124 gb/tg trace reader (c2.commands.gb_hints)."""
from c2.commands import gb_hints as GB


def _row(var, reg, sav, scores, tree=None, veto=None, given=None):
    return {"var": var, "reg_name": reg, "savings": sav,
            "cand_scores": [{"cand": c, "saves": s} for c, s in scores],
            "tree_cands": tree or [c for c, _ in scores],
            "tg_veto": veto or [], "given_before": given}


def test_credit_pick():
    e = GB._explain_row(_row("extra", "ECX", 111,
                             [("EBX", 0), ("ECX", 4), ("EBP", 0)]))
    assert e.reason == "credit" and "4" in e.detail


def test_given_tie_break():
    e = GB._explain_row(_row("y_off", "ESI", 3,
                             [("EDX", 0), ("ESI", 0), ("EBP", 0)],
                             given=0x10000100))
    assert e.reason == "given-tie-break"
    assert "EDX" in e.detail and "reorder" in e.detail


def test_list_order_and_forced():
    e = GB._explain_row(_row("off", "EAX", 37,
                             [("EAX", 0), ("EDX", 0), ("EBX", 0)]))
    assert e.reason == "list-order"
    e2 = GB._explain_row(_row("delta", "EBX", 98, [("EBX", 0)],
                              tree=["EAX", "EDX", "EBX", "ECX"],
                              veto=["EDX"]))
    assert e2.reason == "forced"
    assert ("EAX", "masked") in e2.skipped
    assert ("EDX", "TooGreedy") in e2.skipped


def test_detect_filters_by_swap_regs():
    routine = {"alloc": [
        _row("a", "EAX", 10, [("EAX", 0)]),
        _row("b", "EBX", 9, [("EBX", 0), ("ECX", 0)]),
    ]}
    out = GB.detect(routine, {"EBX", "ECX"})
    assert len(out) == 1 and out[0].var == "b"
    lines = GB.render(out)
    assert lines and "b->EBX" in lines[0]


def test_round2_flagging():
    routine = {"alloc": [
        _row("i", "EAX", 61, [("EAX", 0)]),
        _row("p", "EDX", 50, [("EDX", 0)]),
        _row("t", "EBX", 60, [("EBX", 0), ("ECX", 0)]),   # 60 > 50: round 2
    ]}
    out = GB.detect(routine, {"EBX", "ECX"})
    assert len(out) == 1 and "ROUND-2" in out[0].detail
    # monotonic walk -> no flag
    routine2 = {"alloc": [
        _row("i", "EAX", 61, [("EAX", 0)]),
        _row("t", "EBX", 60, [("EBX", 0), ("ECX", 0)]),
    ]}
    out2 = GB.detect(routine2, {"EBX"})
    assert "ROUND-2" not in out2[0].detail

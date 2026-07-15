"""Tests for the c2 worklist dispatch ladder (classify)."""
from __future__ import annotations

from c2.commands.worklist import classify, _ROUTE


def _f(**kw):
    base = {"name": "f", "diff_byte_count": 10, "rule_hints": {}}
    base.update(kw)
    return base


def _tri(*cascade):
    return {"cascade": list(cascade)}


def test_blocked_beats_everything():
    # GENUINELY tail-blocked: whole diff is in the shared-tail window
    # (size 20, only offset 16 differs >= 20-12) AND donor not exact.
    f = _f(size=20, diff_byte_count=2, diff_byte_offsets=[16],
           frame_hint={"delta": 8},
           tail_merge={"donor_name": "d", "donor_status": "diff"})
    assert classify(f, None) == "blocked"


def test_body_diff_with_diff_donor_is_not_blocked():
    # A dependent with its OWN body diff (offset 8 is far from the tail) is
    # not gated by a non-exact donor -- it routes to its real lever, not
    # BLOCKED (docs/comtail-cascade-analysis.md).
    f = _f(size=200, diff_byte_count=2, diff_byte_offsets=[8, 100],
           frame_hint={"delta": 8},
           tail_merge={"donor_name": "d", "donor_status": "diff"})
    assert classify(f, None) == "frame"


def test_donor_exact_is_not_blocked():
    f = _f(tail_merge={"donor_name": "d", "donor_status": "exact"})
    # no other signal -> needs diagnosis (body residue), not blocked
    assert classify(f, None) == "needs-diagnosis"


def test_shape_over_frame():
    # The dominant verdict is the most-upstream fix-order lever: a Rule 152
    # shape fix (layer 1) cascades into the frame (layer 2), so it is fixed
    # -- and surfaced -- FIRST (decomp/AGENTS.md: shape -> structural ->
    # regalloc).  classify_all still carries BOTH (frame is in other_levers).
    from c2.commands.worklist import classify_all
    f = _f(frame_hint={"delta": -8}, rule_hints={"Rule 152": 2})
    assert classify(f, None) == "shape-152"
    assert "frame" in classify_all(f, None)


def test_shape_152_and_151():
    assert classify(_f(rule_hints={"Rule 152": 1}), None) == "shape-152"
    assert classify(_f(rule_hints={"Rule 151": 1}), None) == "shape-151"


def test_byte_seat_cached_cases():
    for case, bucket in [("A", "byte-reorder"), ("B", "byte-widen"),
                         ("C", "byte-dename"), ("D", "park-byte")]:
        f = _f(byte_seat={"case": case}, rule_hints={"Byte-reg swap": 1})
        assert classify(f, None) == bucket


def test_byte_seat_uncached_routes_to_v():
    f = _f(rule_hints={"Byte-reg swap": 1})   # no byte_seat field
    assert classify(f, None) == "byte-seat"


def test_reorder_reachable():
    f = _f(rule_hints={"Reg swap": 1})
    assert classify(f, _tri("Cascade: EAX<->EDX REACHABLE by TIE-REORDER ...")) == "reorder"


def test_savings_and_park():
    f = _f(rule_hints={"Reg swap": 1})
    assert classify(f, _tri("Cascade: needs a SAVINGS change ...")) == "savings"
    assert classify(f, _tri("Cascade: UNREACHABLE by any move ...")) == "park-reg"


def test_pragma_is_prologue_bucket():
    # pragma_hint (Rule 89 extra-callee-save) is no longer mislabeled diagnose.
    assert classify(_f(pragma_hint={"category": "ps_extra_callee_save"}), None) \
        == "prologue"


def test_frame_beats_pragma():
    f = _f(frame_hint={"delta": 8}, pragma_hint={"category": "x"})
    assert classify(f, None) == "frame"


def test_slot_swap_bucket():
    assert classify(_f(slot_swap={"slots": [4, 8]}), None) == "slot-swap"


def test_cache_and_decl_order():
    assert classify(_f(global_cache_hint={"x": 1}), None) == "cache"
    assert classify(_f(decl_order_hint={"x": 1}), None) == "decl-order"


def test_opaque_is_diagnose():
    assert classify(_f(), _tri()) == "needs-diagnosis"


def test_every_bucket_has_a_route():
    buckets = {"frame", "shape-152", "shape-151", "byte-widen", "byte-dename",
               "byte-reorder", "reorder", "cache", "decl-order", "savings",
               "prologue", "slot-swap", "byte-seat", "blocked", "park-byte",
               "park-reg", "needs-diagnosis"}
    assert buckets <= set(_ROUTE)


def test_loop_rotation_bucket_and_multi_lever():
    from c2.commands.worklist import classify_all
    # a function with BOTH a slot-swap AND a loop rotation -> both surface.
    f = _f(slot_swap={"slots": [4, 8]}, loop_rotation={"rule": "134"})
    buckets = classify_all(f, None)
    assert "loop-rotation" in buckets and "slot-swap" in buckets
    # loop-rotation (clean shape fix) is the dominant of the two.
    assert classify(f, None) == "loop-rotation"


def test_shape_signal_ir_identical_is_regalloc():
    from c2.commands.worklist import _shape_signal
    f = _f(binir_shape_hint={"verdict": "encoding_noise",
                             "lines_compared": 5, "lines_divergent": 0})
    assert _shape_signal(f)["kind"] == "regalloc"


def test_shape_signal_divergent_is_shape():
    from c2.commands.worklist import _shape_signal
    f = _f(binir_shape_hint={"verdict": "shape_divergence",
                             "lines_compared": 27, "lines_divergent": 21})
    sig = _shape_signal(f)
    assert sig["kind"] == "shape" and sig["divergent"] == 21


def test_shape_signal_none_and_no_lines():
    from c2.commands.worklist import _shape_signal
    assert _shape_signal(_f()) is None
    f = _f(binir_shape_hint={"verdict": "no_lines_with_ir",
                             "lines_compared": 0, "lines_divergent": 0})
    assert _shape_signal(f)["kind"] == "unknown"


def test_new_rule_frontier_ranks_by_cluster_leverage(capsys):
    # The new-rule picker ranks NOVEL residue families by cluster size then
    # rep tractability -- a 7-member family with a 5b rep outranks a
    # 1-member 446b one, the inverse of byte ranking.
    from c2.commands.worklist import _new_rule_frontier
    full_diff = [
        # cluster A: 2 byte-reg-swap funcs (novel: only generic reg-swap hints)
        {"name": "a_rep", "diff_byte_count": 5, "size": 100,
         "file": "x.c", "rule_hints": {"Byte-reg swap": 1}, "rows": []},
        {"name": "a_two", "diff_byte_count": 9, "size": 100,
         "file": "x.c", "rule_hints": {"Byte-reg swap": 1}, "rows": []},
    ]
    rows = [{"name": "a_rep", "status": "workable", "shape": "regalloc"},
            {"name": "a_two", "status": "workable", "shape": "regalloc"}]
    _new_rule_frontier(full_diff, rows, as_json=True)
    import json as _j
    out = _j.loads(capsys.readouterr().out)
    assert "novel_families" in out and "diagnose_no_lever" in out


def test_diff_shape_summary_gates_and_flags_cascade():
    from c2.commands.decomp_verify import _diff_shape_summary
    def _row(kind, o_asm=None, r_asm=None):
        o = (0, 1, b"", o_asm) if o_asm is not None else None
        r = (0, 1, b"", r_asm) if r_asm is not None else None
        return {"kind": kind, "o": o, "r": r}
    # small clean replace-only diff -> gated out (None)
    assert _diff_shape_summary([_row("replace", "mov eax, 1", "mov edx, 1")]) is None
    # insert/delete-heavy -> cascade verdict
    rows = ([_row("replace", "mov eax,1", "mov edx,1")]
            + [_row("insert", None, "nop") for _ in range(5)]
            + [_row("delete", "nop", None) for _ in range(5)])
    out = _diff_shape_summary(rows)
    assert out and "ALIGNMENT CASCADE" in out and "insert" in out

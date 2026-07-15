"""Tests for the regtrace spill-chain predictor (memory-exile lever hint).

Makes the WCC spill decision predictable: for a memory-exiled value it names
which value holds each candidate register and the correct lever, distinguishing
three real cases:
  * below-all-holders  -> reduce cross-call register pressure (shorten the
    cheapest holder's call-spanning range so it becomes a memory temp);
  * a free callee-saved reg that is scratch-clobbered across calls -> cut the
    cross-call scratch;
  * out-ranks a holder yet still spilled -> interference, not rank: shorten the
    value's OWN live range.
"""
from c2.commands.regtrace import build_holder_map, spill_chain_hint

GP = ["EAX", "EDX", "EBX", "ECX", "ESI", "EDI", "EBP", "ESP"]


def test_below_all_holders_reduce_pressure():
    # rows(param,12) spills; all 4 callee-saved held (EBX,ESI,EDI,EBP),
    # caller-saved free => cross-call. Lever = shorten cheapest holder's range.
    holder = build_holder_map([
        ("EAX", "(temp)", 1500),            # caller-saved (clobbered)
        ("EBX", "tA", 300), ("ESI", "col", 710),
        ("EDI", "enemy_idx", 400), ("EBP", "row", 231),
        # EDX/ECX left free (caller-saved) -> cross=True
    ])
    out = spill_chain_hint(GP, 12, holder)
    assert "lowest cross-call competitor" in out
    assert "row(231)" in out and "call-spanning range" in out
    # must NOT claim to raise the spilled value's own savings (it can't)
    assert "raise this value" not in out


def test_free_callee_saved_is_scratch_blocked():
    # ECX/EAX free (cross) AND EBX (callee-saved) unheld yet still spilled
    # => EBX scratch-clobbered across the call(s).
    holder = build_holder_map([
        ("EAX", "t", 1500), ("ESI", "col", 710), ("EDI", "y", 400),
        ("EBP", "row", 131),
        # EBX unheld -> free callee-saved
    ])
    out = spill_chain_hint(GP, 12, holder)
    assert "EBX is unheld but scratch-clobbered" in out
    assert "cut cross-call scratch" in out


def test_out_ranks_holder_is_interference_not_rank():
    # value sav=100 out-ranks weak(50) yet spilled -> interference lever,
    # shorten THIS value's own range; never advise "raise savings".
    holder = build_holder_map([
        ("ESI", "col", 710), ("EDI", "weak", 50),
        ("EBP", "row", 600), ("EBX", "t", 300),
    ])
    out = spill_chain_hint(GP, 100, holder)
    assert "interference, NOT rank" in out
    assert "weak(50)" in out
    assert "THIS value's live range" in out
    assert "raise this value" not in out


def test_no_holders_no_hint():
    assert spill_chain_hint(GP, 12, {}) == ""

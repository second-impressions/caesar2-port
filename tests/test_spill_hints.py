"""Tests for the register-pressure spill / rematerialization detector
(Rule 111) wired into `decomp-verify -v`."""
from c2.commands.spill_hints import (
    redundant_reads,
    detect_spill_class,
    render,
)


def _i(asm):
    return (0, 1, b"", asm)


def test_redundant_reads_counts_cse_able_rereads():
    # Same addr read 3x with nothing between -> 2 redundant reads.
    insns = [_i("mov eax, [0x72ba0]"),
             _i("mov edx, [0x72ba0]"),
             _i("mov ecx, [0x72ba0]")]
    total, per = redundant_reads(insns)
    assert total == 2
    assert per["0x72ba0"] == 2


def test_call_kills_availability():
    # A call between reads means the second read is NOT redundant.
    insns = [_i("mov eax, [0x72ba0]"),
             _i("call 0x1234"),
             _i("mov edx, [0x72ba0]")]
    total, _ = redundant_reads(insns)
    assert total == 0


def test_write_kills_availability():
    # A write to the addr between reads kills the CSE.
    insns = [_i("mov eax, [0x72ba0]"),
             _i("mov [0x72ba0], edx"),
             _i("mov ecx, [0x72ba0]")]
    total, _ = redundant_reads(insns)
    assert total == 0


def test_rmw_counts_as_write():
    # sub [m], eax is a read-modify-write -> destination -> kills.
    insns = [_i("mov eax, [0x72ba0]"),
             _i("sub [0x72ba0], edx"),
             _i("mov ecx, [0x72ba0]")]
    total, _ = redundant_reads(insns)
    assert total == 0


def test_detect_fires_when_ps_rereads_rc_holds():
    # PS re-reads the global 5x (4 redundant); RC holds it (1 read).
    ps = [_i(f"mov eax, [0x72ba0]") for _ in range(5)]
    rc = [_i("mov eax, [0x40000]"), _i("add ebx, eax")]
    h = detect_spill_class(ps, rc, has_body_diff=True)
    assert h is not None
    assert h.addr == "0x72ba0"
    assert h.ps_reads == 4 and h.rc_total == 0 and h.margin == 4
    assert "spill" in render(h).lower()


def test_no_fire_when_both_reread():
    # raider_in_region case: PS AND RC both re-read -> no divergence.
    ps = [_i("mov eax, [0x858b4]"), _i("mov edx, [0x858b4]"), _i("mov ecx, [0x858b4]")]
    rc = [_i("mov eax, [0x40000]"), _i("mov edx, [0x40000]"), _i("mov ecx, [0x40000]")]
    assert detect_spill_class(ps, rc, has_body_diff=True) is None


def test_no_fire_on_non_diffing():
    ps = [_i("mov eax, [0x72ba0]") for _ in range(5)]
    rc = [_i("nop")]
    assert detect_spill_class(ps, rc, has_body_diff=False) is None


def test_no_fire_below_threshold():
    # Only one redundant read on PS -> below _MIN_PS_REDUNDANT.
    ps = [_i("mov eax, [0x72ba0]"), _i("mov edx, [0x72ba0]")]
    rc = [_i("mov eax, [0x40000]")]
    assert detect_spill_class(ps, rc, has_body_diff=True) is None

"""Unit tests for the same-size spill-slot SWAP detector (Rule 107 gap)."""
from c2.commands import slot_swap_hints as ss


def _insn(off, size, asm):
    # InsnT tuple shape: (off, size, raw_bytes, asm_text)
    return (off, size, b"\x90" * size, asm)


def _prologue(frame):
    """A minimal callee-save prologue + `sub esp, frame` on both sides."""
    return [
        _insn(0, 1, "push ebx"),
        _insn(1, 1, "push esi"),
        _insn(2, 3, f"sub esp, {frame:#x}"),
    ]


def _row(o, r, kind="diff"):
    return {"o": o, "r": r, "kind": kind, "off": o[0] if o else r[0]}


def test_detects_refresh_style_slot_swap():
    """PS spills to [esp+4]/[esp]; recomp swaps them -> Slot-swap fires."""
    orig = _prologue(0xC)
    recomp = _prologue(0xC)
    rows = [
        # pass-1 spill: PS [esp+4]  vs  RC [esp]
        _row(_insn(0x20, 4, "mov [esp + 4], edx"), _insn(0x20, 3, "mov [esp], edx")),
        _row(_insn(0x30, 4, "mov eax, [esp + 4]"), _insn(0x30, 3, "mov eax, [esp]")),
        # pass-2 spill: PS [esp]    vs  RC [esp+4]
        _row(_insn(0x60, 3, "mov [esp], edx"), _insn(0x60, 4, "mov [esp + 4], edx")),
        _row(_insn(0x70, 3, "add eax, [esp]"), _insn(0x70, 4, "add eax, [esp + 4]")),
    ]
    h = ss.detect(orig, recomp, rows)
    assert h is not None
    assert h.frame == 0xC
    assert h.slots == [0, 4]
    assert h.n_rows == 4
    line = ss.render(h)
    assert "FUNCTION scope" in line and "Rule 107" in line


def test_no_fire_on_frame_size_delta():
    """Different frame sizes are frame_hints' job, not ours."""
    orig = _prologue(0xC)
    recomp = _prologue(0x8)
    rows = [_row(_insn(0x20, 4, "mov [esp + 4], edx"),
                 _insn(0x20, 3, "mov [esp], edx"))]
    assert ss.detect(orig, recomp, rows) is None


def test_no_fire_on_single_slot_shift():
    """One row moving into a NEW slot (not a permutation of the same set)
    is a layout change, not a swap -> no fire."""
    orig = _prologue(0xC)
    recomp = _prologue(0xC)
    rows = [_row(_insn(0x20, 4, "mov [esp + 4], edx"),
                 _insn(0x20, 4, "mov [esp + 8], edx"))]
    assert ss.detect(orig, recomp, rows) is None


def test_no_fire_when_register_also_changes():
    """If the instruction differs beyond the esp displacement (a real
    register diff), it is not a pure slot swap."""
    orig = _prologue(0xC)
    recomp = _prologue(0xC)
    rows = [
        _row(_insn(0x20, 4, "mov [esp + 4], edx"), _insn(0x20, 3, "mov [esp], ebx")),
        _row(_insn(0x60, 3, "mov [esp], edx"), _insn(0x60, 4, "mov [esp + 4], ebx")),
    ]
    assert ss.detect(orig, recomp, rows) is None


def test_ignores_outgoing_stack_args_above_frame():
    """[esp+N] with N >= frame size is outgoing-arg space, not a local slot."""
    orig = _prologue(0x8)
    recomp = _prologue(0x8)
    rows = [
        _row(_insn(0x20, 4, "mov [esp + 8], edx"), _insn(0x20, 4, "mov [esp + 0xc], edx")),
        _row(_insn(0x60, 4, "mov [esp + 0xc], edx"), _insn(0x60, 4, "mov [esp + 8], edx")),
    ]
    assert ss.detect(orig, recomp, rows) is None


def test_caller_push_pad_counts_push_eax_frame_slot():
    # push esi/edi/ebp (callee), sub esp,8 (frame), push eax (extra slot).
    insns = [
        _insn(0, 1, "push esi"), _insn(1, 1, "push edi"),
        _insn(2, 1, "push ebp"), _insn(3, 3, "sub esp, 0x8"),
        _insn(6, 1, "push eax"), _insn(7, 4, "mov [esp + 4], ebx"),
    ]
    assert ss._caller_push_pad(insns) == 4


def test_push_eax_shifted_spill_is_detected():
    """build_units_figures shape: frame 0x8 + `push eax` -> a real spill at
    [esp+8] that the old `>= ps_frame` filter wrongly excluded."""
    pro = [
        _insn(0, 1, "push esi"), _insn(1, 1, "push edi"),
        _insn(2, 1, "push ebp"), _insn(3, 3, "sub esp, 0x8"),
        _insn(6, 1, "push eax"),
    ]
    rows = [
        _row(_insn(0x9, 4, "mov [esp + 4], ebx"), _insn(0x9, 4, "mov [esp + 8], ebx")),
        _row(_insn(0xd, 4, "mov [esp + 8], ecx"), _insn(0xd, 4, "mov [esp + 4], ecx")),
    ]
    h = ss.detect(pro, pro, rows)
    assert h is not None and h.slots == [4, 8]


def test_outgoing_args_still_excluded_without_push_pad():
    """No caller-save push -> [esp+8]/[esp+0xc] above an 8-byte frame stay
    excluded (the outgoing-stack-arg guard is intact)."""
    pro = [_insn(0, 1, "push ebx"), _insn(1, 1, "push esi"),
           _insn(2, 3, "sub esp, 0x8")]
    rows = [
        _row(_insn(0x20, 4, "mov [esp + 8], edx"), _insn(0x20, 4, "mov [esp + 0xc], edx")),
        _row(_insn(0x60, 4, "mov [esp + 0xc], edx"), _insn(0x60, 4, "mov [esp + 8], edx")),
    ]
    assert ss.detect(pro, pro, rows) is None

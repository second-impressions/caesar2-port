"""Tests for the frame-size root-cause diagnostic (c2.commands.frame_hints)."""

from c2.commands.frame_hints import detect, detect_frame_alloc, render_line, to_json


def _insns(asms):
    """Build minimal InsnT tuples (off, size, raw, asm) from asm strings."""
    out = []
    off = 0
    for a in asms:
        out.append((off, 1, b"\x00", a))
        off += 1
    return out


def test_detect_frame_alloc_simple():
    insns = _insns(["push ebx", "push esi", "sub esp, 0x10", "mov eax, 1"])
    assert detect_frame_alloc(insns) == 0x10


def test_detect_frame_alloc_skips_caller_saved_pushes():
    # PS routinely pushes ecx/edx as preserves before the sub (Rule 24a).
    insns = _insns(["push ebx", "push ecx", "push edx", "push esi",
                    "sub esp, 0x14", "mov eax, 1"])
    assert detect_frame_alloc(insns) == 0x14


def test_detect_frame_alloc_chk_prologue():
    insns = _insns(["push 0x40", "call 0x1234", "push ebx",
                    "sub esp, 0x20"])
    assert detect_frame_alloc(insns) == 0x20


def test_detect_frame_alloc_no_frame():
    insns = _insns(["push ebx", "mov eax, 1", "ret"])
    assert detect_frame_alloc(insns) == 0


def test_no_hint_when_frames_match():
    ps = _insns(["push ebx", "sub esp, 0x10"])
    rc = _insns(["push ebx", "sub esp, 0x10"])
    assert detect(ps, rc) is None


def test_rc_bigger_equal_pushes_points_to_rule116():
    # equal push count -> the removable-local / pressure-spill case (Rule 116)
    ps = _insns(["push ebx", "sub esp, 0x14"])
    rc = _insns(["push ebx", "sub esp, 0x30"])
    rows = [{"kind": "replace", "off": 2}]
    h = detect(ps, rc, rows)
    assert h is not None
    assert h.direction == "rc_bigger"
    assert h.delta == 0x30 - 0x14
    assert h.slot_delta == (0x30 - 0x14) // 4
    assert h.is_root is True
    assert h.worthprolog_swap is False
    assert "Rule 116" in h.fix
    line = render_line(h)
    assert "ROOT of cascade" in line
    assert "+7 slots" in line
    assert "pushes PS 1/RC 1" in line


def test_rc_bigger_fewer_pushes_is_worthprolog_swap():
    # RC dropped a callee-save (edi) and spilled to a stack slot instead.
    ps = _insns(["push esi", "push edi", "mov esi, eax"])
    rc = _insns(["push esi", "sub esp, 4", "mov esi, eax"])
    rows = [{"kind": "replace", "off": 1}]
    h = detect(ps, rc, rows)
    assert h.direction == "rc_bigger"
    assert h.ps_pushes == 2 and h.rc_pushes == 1
    assert h.worthprolog_swap is True
    assert h.over_enregister is False
    assert "WorthProlog" in h.fix
    assert "WorthProlog spill-vs-callee-save" in render_line(h)


def test_rc_bigger_more_pushes_is_structural_over_enregister():
    # RC pushes MORE callee-saves AND has a bigger frame (figure_update shape).
    ps = _insns(["push ebx", "push ecx", "push edx", "push esi", "mov eax, 1"])
    rc = _insns(["push ebx", "push ecx", "push edx", "push esi",
                 "push edi", "push ebp", "sub esp, 4", "mov eax, 1"])
    rows = [{"kind": "replace", "off": 4}]
    h = detect(ps, rc, rows)
    assert h.direction == "rc_bigger"
    assert h.ps_pushes == 4 and h.rc_pushes == 6
    assert h.worthprolog_swap is False
    assert h.over_enregister is True
    assert "MORE prologue pushes" in h.fix
    assert "structural (RC over-enregisters)" in render_line(h)


def test_ps_bigger_direction():
    ps = _insns(["push ebx", "sub esp, 0x20"])
    rc = _insns(["push ebx", "sub esp, 0x08"])
    h = detect(ps, rc, rows=[{"kind": "equal", "off": 0},
                             {"kind": "replace", "off": 2}])
    assert h.direction == "ps_bigger"
    assert h.slot_delta == -6
    assert "Rule 111" in h.fix
    assert h.is_root is True


def test_is_root_false_when_first_diff_is_late():
    ps = _insns(["push ebx", "sub esp, 0x14"])
    rc = _insns(["push ebx", "sub esp, 0x30"])
    # first divergence is far past the prologue window
    rows = [{"kind": "equal", "off": 0}, {"kind": "replace", "off": 200}]
    h = detect(ps, rc, rows)
    assert h.is_root is False
    assert "downstream" in render_line(h)


def test_to_json_roundtrip():
    ps = _insns(["push ebx", "sub esp, 0x14"])
    rc = _insns(["push ebx", "sub esp, 0x18"])
    h = detect(ps, rc, rows=[{"kind": "replace", "off": 2}])
    j = to_json(h)
    assert j["direction"] == "rc_bigger"
    assert j["slot_delta"] == 1
    assert to_json(None) is None


# ── c2.c burn-down detectors (Rules 136/137/138), 2026-06-13 ──────────────

def _ins(off, asm, size=2):
    return (off, size, b"\x90" * size, asm)


class TestMemoryRetvalFunnel:
    """Rule 136: PS exiles the return temp to [esp]; RC keeps a register."""

    PS = [
        _ins(0x000, "push ebx", 1),
        _ins(0x001, "sub esp, 4", 3),
        _ins(0x115, "mov dword ptr [esp], 1", 7),
        _ins(0x11c, "jmp 0x15d"),
        _ins(0x13e, "call 0x100", 5),
        _ins(0x15d, "mov eax, dword ptr [esp]", 3),
        _ins(0x160, "add esp, 4", 3),
        _ins(0x163, "pop ebx", 1),
        _ins(0x164, "ret", 1),
    ]
    RC = [
        _ins(0x000, "push ebx", 1),
        _ins(0x115, "mov eax, 1", 5),
        _ins(0x11a, "pop ebx", 1),
        _ins(0x11b, "ret", 1),
    ]

    def test_fires_on_load_map_graphics_shape(self):
        from c2.commands.frame_hints import detect_memory_retval_funnel
        h = detect_memory_retval_funnel("t", self.PS, self.RC)
        assert h is not None
        assert h.imm == "1"
        assert h.store_off == 0x115 and h.load_off == 0x15d

    def test_suppressed_when_rc_funnels_too(self):
        from c2.commands.frame_hints import detect_memory_retval_funnel
        rc = self.RC + [_ins(0x200, "mov eax, dword ptr [esp]", 3)]
        assert detect_memory_retval_funnel("t", self.PS, rc) is None

    def test_register_store_is_not_a_funnel(self):
        from c2.commands.frame_hints import detect_memory_retval_funnel
        ps = [_ins(0x115, "mov dword ptr [esp], eax", 3),
              _ins(0x15d, "mov eax, dword ptr [esp]", 3),
              _ins(0x160, "ret", 1)]
        assert detect_memory_retval_funnel("t", ps, self.RC) is None

    def test_mid_function_load_is_not_a_funnel(self):
        # the [esp] reload must be at the epilogue (only add/pop/ret after)
        from c2.commands.frame_hints import detect_memory_retval_funnel
        ps = [_ins(0x115, "mov dword ptr [esp], 1", 7),
              _ins(0x120, "mov eax, dword ptr [esp]", 3),
              _ins(0x123, "call 0x50", 5),
              _ins(0x128, "ret", 1)]
        assert detect_memory_retval_funnel("t", ps, self.RC) is None


class TestMergeDirection:
    """Rule 137: PS merges suffixes keep-first (backward), RC keep-last."""

    def test_fires_on_per_arm_shape(self):
        from c2.commands.frame_hints import detect_merge_direction
        ps = [_ins(0x68, "test eax, eax"), _ins(0x86, "jmp 0x68"),
              _ins(0x99, "jmp 0x68"), _ins(0xac, "jmp 0x68")]
        rc = [_ins(0x86, "jmp 0xf8"), _ins(0x99, "jmp 0xf8"),
              _ins(0xf8, "test eax, eax")]
        h = detect_merge_direction("t", ps, rc)
        assert h is not None
        assert h.ps_target == 0x68 and h.ps_jumpers == 3
        assert h.rc_target == 0xf8 and h.rc_jumpers == 2

    def test_symmetric_loop_continues_cancel(self):
        from c2.commands.frame_hints import detect_merge_direction
        loop = [_ins(0x50, "jmp 0x10"), _ins(0x60, "jmp 0x10")]
        assert detect_merge_direction("t", loop, loop) is None

    def test_single_jumpers_do_not_fire(self):
        from c2.commands.frame_hints import detect_merge_direction
        ps = [_ins(0x50, "jmp 0x10")]
        rc = [_ins(0x50, "jmp 0x90")]
        assert detect_merge_direction("t", ps, rc) is None


class TestParamRegScratch:
    """Rule 138: PS writes an unsaved arg reg -> params exist."""

    def test_fires_on_main_shape(self):
        from c2.commands.frame_hints import detect_param_reg_scratch
        ps = [_ins(0, "push ebx", 1), _ins(1, "push ecx", 1),
              _ins(2, "push ebp", 1), _ins(3, "xor edx, edx"),
              _ins(5, "call 0x100", 5)]
        rc = [_ins(0, "push ebx", 1), _ins(1, "push ecx", 1),
              _ins(2, "push edx", 1), _ins(3, "push ebp", 1),
              _ins(4, "xor edx, edx")]
        h = detect_param_reg_scratch("t", ps, rc)
        assert h is not None
        assert h.writes == [("edx", 3)]

    def test_render_names_arity(self):
        from c2.commands.frame_hints import (
            detect_param_reg_scratch, render_param_scratch)
        ps = [_ins(0, "push ebx", 1), _ins(3, "xor ecx, ecx")]
        rc = [_ins(0, "push ebx", 1), _ins(1, "push ecx", 1),
              _ins(3, "xor ecx, ecx")]
        h = detect_param_reg_scratch("t", ps, rc)
        assert h is not None
        assert ">= 4 parameters" in render_param_scratch(h)[1]

    def test_no_fire_when_ps_never_writes(self):
        from c2.commands.frame_hints import detect_param_reg_scratch
        ps = [_ins(0, "push ebx", 1), _ins(1, "mov eax, edx")]  # read only
        rc = [_ins(0, "push ebx", 1), _ins(1, "push edx", 1)]
        assert detect_param_reg_scratch("t", ps, rc) is None


# ── Session 2026-06-13 (initreg_game_loop close-out): Rules 148/149 ──────

def _i(off, asm, size=2):
    return (off, size, b"\x90" * size, asm)


class TestEpilogueFunnel:
    """Rule 141: PS funnels early exits via jmp; RC inlines epilogues."""

    # initreg_game_loop pre-fix shape (frameless, 5 callee-save pushes,
    # 4 early exits inlined as `pop ebx; pop ecx; pop edx; pop edi; ret`
    # in RC vs `jmp <end>` in PS).
    PS = [
        _i(0x000, "push ebx", 1), _i(0x001, "push ecx", 1),
        _i(0x002, "push edx", 1), _i(0x003, "push edi", 1),
        _i(0x004, "push ebp", 1),
        # early-exit jmps
        _i(0x102, "jmp 0x16b"),
        _i(0x10b, "je 0x16b"),
        _i(0x115, "je 0x16b"),
        _i(0x125, "jne 0x16b"),
        # body
        _i(0x140, "call 0x500", 5),
        # final epilogue (6b: 5 pops + ret)
        _i(0x16b, "pop ebp", 1), _i(0x16c, "pop edi", 1),
        _i(0x16d, "pop edx", 1), _i(0x16e, "pop ecx", 1),
        _i(0x16f, "pop ebx", 1), _i(0x170, "ret", 1),
    ]
    # RC has 4 inlined epilogue blocks at the early-exit sites + the final.
    # callee-saves are only 4 (ebx,ecx,edx,edi); the inlined epilogue is 5b.
    RC = [
        _i(0x000, "push ebx", 1), _i(0x001, "push ecx", 1),
        _i(0x002, "push edx", 1), _i(0x003, "push edi", 1),
        # early-exit inlined epilogues (4 sites)
        _i(0x102, "pop edi", 1), _i(0x103, "pop edx", 1),
        _i(0x104, "pop ecx", 1), _i(0x105, "pop ebx", 1),
        _i(0x106, "ret", 1),
        _i(0x110, "pop edi", 1), _i(0x111, "pop edx", 1),
        _i(0x112, "pop ecx", 1), _i(0x113, "pop ebx", 1),
        _i(0x114, "ret", 1),
        _i(0x120, "pop edi", 1), _i(0x121, "pop edx", 1),
        _i(0x122, "pop ecx", 1), _i(0x123, "pop ebx", 1),
        _i(0x124, "ret", 1),
        _i(0x130, "pop edi", 1), _i(0x131, "pop edx", 1),
        _i(0x132, "pop ecx", 1), _i(0x133, "pop ebx", 1),
        _i(0x134, "ret", 1),
        # final epilogue
        _i(0x140, "call 0x500", 5),
        _i(0x16f, "pop edi", 1), _i(0x170, "pop edx", 1),
        _i(0x171, "pop ecx", 1), _i(0x172, "pop ebx", 1),
        _i(0x173, "ret", 1),
    ]

    def test_fires_on_initreg_shape(self):
        from c2.commands.frame_hints import detect_epilogue_funnel
        h = detect_epilogue_funnel("t", self.PS, self.RC)
        assert h is not None
        assert len(h.ps_jmps) == 4
        assert h.epilogue_size == 6

    def test_no_fire_when_epilogue_is_inlinable(self):
        # 4 callee-saves -> epilogue=5b, CloneCode inlines both sides
        from c2.commands.frame_hints import detect_epilogue_funnel
        ps = [_i(0, "push ebx", 1), _i(1, "push ecx", 1),
              _i(2, "push edx", 1), _i(3, "push edi", 1),
              _i(0x50, "pop edi", 1), _i(0x51, "pop edx", 1),
              _i(0x52, "pop ecx", 1), _i(0x53, "pop ebx", 1),
              _i(0x54, "ret", 1)]
        rc = list(ps)
        assert detect_epilogue_funnel("t", ps, rc) is None

    def test_no_fire_when_framed(self):
        # framed function -> Rule 135 territory, not this one
        from c2.commands.frame_hints import detect_epilogue_funnel
        ps = [_i(0, "push ebx", 1), _i(1, "push ecx", 1),
              _i(2, "push edx", 1), _i(3, "push edi", 1),
              _i(4, "push ebp", 1), _i(5, "sub esp, 0x10", 3)]
        ps.extend(self.PS[5:])
        assert detect_epilogue_funnel("t", ps, self.RC) is None

    def test_no_fire_when_rc_has_no_inline_epilogues(self):
        from c2.commands.frame_hints import detect_epilogue_funnel
        rc = list(self.PS)   # RC same as PS
        assert detect_epilogue_funnel("t", self.PS, rc) is None


class TestGlobalInExtraCalleeSave:
    """Rule 142: PS keeps a global in the extra callee-save across calls."""

    PS = [
        _i(0x000, "push ebx", 1), _i(0x001, "push ecx", 1),
        _i(0x002, "push edx", 1), _i(0x003, "push edi", 1),
        _i(0x004, "push ebp", 1),
        # body: load region_over into the extra callee-save EBP
        _i(0x10d, "mov ebp, dword ptr [0x72f98]", 6),
        _i(0x113, "test ebp, ebp", 2),
        _i(0x115, "je 0x16b"),
        # body call (this_region() in the worked example)
        _i(0x140, "call 0x500", 5),
        # USE EBP after the call (would die without callee-save)
        _i(0x145, "mov [eax + 0x836e5], ebp", 6),
        _i(0x16b, "pop ebp", 1), _i(0x16c, "pop edi", 1),
        _i(0x16d, "pop edx", 1), _i(0x16e, "pop ecx", 1),
        _i(0x16f, "pop ebx", 1), _i(0x170, "ret", 1),
    ]
    RC = [
        _i(0x000, "push ebx", 1), _i(0x001, "push ecx", 1),
        _i(0x002, "push edx", 1), _i(0x003, "push edi", 1),
        # body: load + use, but EAX (caller-save) dies on the call
        _i(0x10d, "mov eax, dword ptr [0x72f98]", 5),
        _i(0x112, "test eax, eax", 2),
        _i(0x114, "je 0x140"),
        _i(0x120, "call 0x500", 5),
        # have to RELOAD after the call
        _i(0x125, "mov eax, dword ptr [0x72f98]", 5),
        _i(0x140, "pop edi", 1), _i(0x141, "pop edx", 1),
        _i(0x142, "pop ecx", 1), _i(0x143, "pop ebx", 1),
        _i(0x144, "ret", 1),
    ]

    def test_fires_on_initreg_region_shape(self):
        from c2.commands.frame_hints import detect_global_in_extra_callee_save
        h = detect_global_in_extra_callee_save("t", self.PS, self.RC)
        assert h is not None
        assert h.extra_save == "ebp"
        assert h.global_addr == 0x72f98
        assert h.spans_calls >= 1

    def test_no_fire_when_no_extra_save(self):
        from c2.commands.frame_hints import detect_global_in_extra_callee_save
        # both sides save same set
        rc = list(self.PS)
        assert detect_global_in_extra_callee_save("t", self.PS, rc) is None

    def test_no_fire_when_extra_save_used_only_pre_call(self):
        # PS extra save EBP is used, but no call between load and last use
        from c2.commands.frame_hints import detect_global_in_extra_callee_save
        ps = [
            _i(0x000, "push ebx", 1), _i(0x001, "push edi", 1),
            _i(0x002, "push ebp", 1),
            _i(0x010, "mov ebp, dword ptr [0x72f98]", 6),
            _i(0x016, "mov [0x100], ebp", 6),
            _i(0x01c, "pop ebp", 1), _i(0x01d, "pop edi", 1),
            _i(0x01e, "pop ebx", 1), _i(0x01f, "ret", 1),
        ]
        rc = ps[:2] + ps[3:]   # no ebp save
        assert detect_global_in_extra_callee_save("t", ps, rc) is None

    def test_no_fire_when_load_source_is_register(self):
        # PS loads ebp from a register, not a global -- not the de-invent
        # pattern.
        from c2.commands.frame_hints import detect_global_in_extra_callee_save
        ps = [
            _i(0x000, "push ebx", 1), _i(0x001, "push ebp", 1),
            _i(0x010, "mov ebp, eax", 2),     # NOT [imm32]
            _i(0x020, "call 0x500", 5),
            _i(0x025, "mov [0x100], ebp", 6),
            _i(0x030, "pop ebp", 1), _i(0x031, "pop ebx", 1),
            _i(0x032, "ret", 1),
        ]
        rc = ps[:1] + ps[2:]
        assert detect_global_in_extra_callee_save("t", ps, rc) is None

"""Tests for the frame-level levers (2026-06-10):

* binir ``farptr_ret_const`` (Rule 85 MK_FP decoder)
* frame_hints ``detect_foreign_frame`` (Rule 125 hosted-block signal)
* frame_hints ``detect_retval_funnel`` (W107 join-read exile)
* tail_merge ``EpilogueChain`` rendering (required save-suffix delta)

All fixtures are synthetic InsnT lists shaped after the real cases that
motivated each lever (pcsound start_sequences / start_samples, battle.c
sf14_opertunist_fire, action.c battle_action).
"""

from c2 import binir
from c2.commands import frame_hints as fh
from c2.commands.tail_merge import EpilogueChain, render_epilogue_chain


def _ins(off, text, size=2):
    return (off, size, b"\x90" * size, text)


# ── farptr_ret_const ───────────────────────────────────────────────────────

def test_farptr_ret_const_certain_with_ret():
    # Local pops ending in ret = certainly a far-ptr return.
    insns = [
        _ins(0x36, "xor edx, edx"),
        _ins(0x38, "mov eax, 1", 5),
        _ins(0x3D, "pop ebp", 1),
        _ins(0x3E, "ret", 1),
    ]
    ops = binir.recover(insns)
    fp = [o for o in ops if o.kind == "farptr_ret_const"]
    assert len(fp) == 1
    assert fp[0].detail == {"seg": 0, "off": 1}
    assert "return (char __far *)0x1;" in fp[0].note


def test_regpair_const_exit_ambiguous_jmp():
    # start_sequences return-1 shape: pop + jmp to an epilogue stub --
    # ambiguous within the function (could be merged-call-site args),
    # so the neutral kind fires with the jmp target recorded for
    # symbol-side resolution (tail_merge.classify_regpair_exit).
    insns = [
        _ins(0x36, "xor edx, edx"),
        _ins(0x38, "mov eax, 1", 5),
        _ins(0x3D, "pop ebp", 1),
        _ins(0x3E, "jmp 0x18df", 5),
    ]
    ops = binir.recover(insns)
    rp = [o for o in ops if o.kind == "regpair_const_exit"]
    assert len(rp) == 1
    assert rp[0].detail == {"seg": 0, "off": 1, "jmp_target": 0x18DF}
    assert "SHARED CALL TAIL" in rp[0].note


def test_regpair_const_exit_mkfp():
    # start_sequences return-2: mov edx,1; mov eax,2; jmp -> MK_FP(1,2).
    insns = [
        _ins(0x89, "mov edx, 1", 5),
        _ins(0x8E, "mov eax, 2", 5),
        _ins(0x93, "jmp 0x3d", 2),
    ]
    ops = binir.recover(insns)
    rp = [o for o in ops if o.kind == "regpair_const_exit"]
    assert len(rp) == 1
    assert rp[0].detail["seg"] == 1 and rp[0].detail["off"] == 2
    assert "MK_FP(0x1, 0x2)" in rp[0].note


def test_farptr_ret_const_not_arg_setup():
    # xor edx,edx; mov eax,N before a CALL is watcall arg setup, not a
    # far-ptr return.
    insns = [
        _ins(0x10, "xor edx, edx"),
        _ins(0x12, "mov eax, 15", 5),
        _ins(0x17, "call 0x4354", 5),
    ]
    assert not [o for o in binir.recover(insns)
                if o.kind in ("farptr_ret_const", "regpair_const_exit")]


def test_farptr_ret_const_not_tailcall_args():
    # Large (address-like) immediates: watcall tail-call args, skip.
    insns = [
        _ins(0x10, "mov edx, 0xd398", 5),
        _ins(0x15, "mov eax, 0x14150", 5),
        _ins(0x1A, "jmp 0x9000", 5),
    ]
    assert not [o for o in binir.recover(insns)
                if o.kind in ("farptr_ret_const", "regpair_const_exit")]


# ── foreign-frame blocks ───────────────────────────────────────────────────

def test_foreign_frame_sf14_shape():
    # PS sf14: saves ebx/ecx/edx only, but the range writes esi and edi.
    insns = [
        _ins(0x0, "push ebx", 1),
        _ins(0x1, "push ecx", 1),
        _ins(0x2, "push edx", 1),
        _ins(0x3, "mov eax, dword ptr [0x858a8]", 5),
        _ins(0x301, "xor esi, esi"),
        _ins(0x303, "mov dword ptr [0x72ed4], esi", 6),
        _ins(0x6E3, "mov edi, dword ptr [0x72d98]", 6),
    ]
    h = fh.detect_foreign_frame("sf14", insns)
    assert h is not None
    assert {r for _o, r, _t in h.writes} == {"esi", "edi"}
    assert [o for o, _r, _t in h.writes] == [0x301, 0x6E3]
    txt = "\n".join(fh.render_foreign_frame(h))
    assert "Rule 125" in txt and "ANOTHER function's frame" in txt


def test_foreign_frame_clean_when_saved():
    insns = [
        _ins(0x0, "push ebx", 1),
        _ins(0x1, "push esi", 1),
        _ins(0x2, "push edi", 1),
        _ins(0x3, "xor esi, esi"),
        _ins(0x5, "mov edi, 5", 5),
        _ins(0xA, "pop edi", 1),
        _ins(0xB, "pop esi", 1),
        _ins(0xC, "pop ebx", 1),
        _ins(0xD, "ret", 1),
    ]
    assert fh.detect_foreign_frame("f", insns) is None


def test_foreign_frame_param_regs_not_flagged():
    # edx/ebx/ecx may carry watcall params -> never evidence.
    insns = [
        _ins(0x0, "push ebx", 1),
        _ins(0x1, "mov edx, 7", 5),
        _ins(0x6, "mov ecx, 8", 5),
        _ins(0xB, "pop ebx", 1),
        _ins(0xC, "ret", 1),
    ]
    assert fh.detect_foreign_frame("f", insns) is None


# ── retval funnel ──────────────────────────────────────────────────────────

def test_retval_funnel_fires_on_homing_pair():
    # RC start_sequences (far* form): mov edx,edi; mov eax,esi; pops; ret.
    insns = [
        _ins(0x0, "push ebx", 1),
        _ins(0x1, "push ecx", 1),
        _ins(0xD0, "mov dword ptr [0x435c0], edx", 6),
        _ins(0xD5, "mov edx, edi"),
        _ins(0xD7, "mov eax, esi"),
        _ins(0xD9, "pop ecx", 1),
        _ins(0xDA, "pop ebx", 1),
        _ins(0xDB, "ret", 1),
    ]
    h = fh.detect_retval_funnel("start_sequences", insns)
    assert h is not None
    assert (h.seg_src, h.off_src) == ("edi", "esi")
    txt = "\n".join(fh.render_retval_funnel(h))
    assert "join read" in txt and "Rule 85" in txt


def test_retval_funnel_ignores_mid_body_movs():
    # The same MOV pair mid-body (followed by real code) must not fire.
    insns = [
        _ins(0x10, "mov edx, edi"),
        _ins(0x12, "mov eax, esi"),
        _ins(0x14, "call 0x100", 5),
        _ins(0x19, "ret", 1),
    ]
    assert fh.detect_retval_funnel("f", insns) is None


# ── epilogue chain render ──────────────────────────────────────────────────

def test_epilogue_chain_missing_save_delta():
    chain = EpilogueChain(
        hops=[("scroll", 0x2FDEF)],
        restores=["edi", "esi", "edx", "ecx", "ebx"],
        ends_in_ret=True,
    )
    assert chain.required_saves == ["ebx", "ecx", "edx", "esi", "edi"]
    lines = render_epilogue_chain(chain, ["ebx", "edx", "esi", "edi"])
    txt = "\n".join(lines)
    assert "MISSING save(s) ['ecx']" in txt
    assert "Rule 110" in txt and "Rule 126" in txt


def test_epilogue_chain_extra_save_delta():
    chain = EpilogueChain(
        hops=[("f", 0x1000), ("g", 0x2000)],
        restores=["edx", "ebx"],
        ends_in_ret=True,
    )
    lines = render_epilogue_chain(chain, ["ebx", "edx", "esi", "edi"])
    txt = "\n".join(lines)
    assert "RC saves ['esi', 'edi']" in txt
    assert "exiled" in txt


def test_foreign_frame_custom_convention():
    # Blitter shape: no pushes, unsaved esi/edi written immediately.
    insns = [
        _ins(0x0, "mov eax, dword ptr [0x100]", 5),
        _ins(0x5, "mov edi, edx"),
        _ins(0x7, "mov esi, ebx"),
        _ins(0x9, "ret", 1),
    ]
    h = fh.detect_foreign_frame("write_large_diamond_hat", insns)
    assert h is not None and h.custom
    txt = "\n".join(fh.render_foreign_frame(h))
    assert "Custom-convention" in txt and "Rule 125" not in txt


def test_foreign_frame_hosted_not_custom():
    insns = [
        _ins(0x0, "push ebx", 1),
        _ins(0x1, "push edx", 1),
        _ins(0x100, "xor esi, esi"),
    ]
    h = fh.detect_foreign_frame("f", insns)
    assert h is not None and not h.custom


def test_rover_caused_push_guard():
    """The rover detect must NOT bail on a push-set delta when the delta
    register is the PARENT of byte rover picks (battle_action: PS rover
    lands on cl -> PS pushes ecx)."""
    from c2.commands import rover_hints as rh

    def f(off, text, size=2):
        return (off, size, b"\x90" * size, text)

    ps = [f(0, "push ebx", 1), f(1, "push ecx", 1), f(2, "push edx", 1),
          f(3, "mov cl, 1"), f(5, "mov byte ptr [0x100], cl", 6),
          f(11, "mov ah, 2"), f(13, "mov byte ptr [0x104], ah", 6),
          f(19, "ret", 1)]
    rc = [f(0, "push ebx", 1), f(1, "push edx", 1),
          f(2, "mov bh, 1"), f(4, "mov byte ptr [0x100], bh", 6),
          f(10, "mov ah, 2"), f(12, "mov byte ptr [0x104], ah", 6),
          f(18, "ret", 1)]
    h = rh.detect(ps, rc, {"Byte-reg swap": 2})
    assert h is not None
    assert "ROVER-CAUSED PUSH" in h.summary

    # An UNEXPLAINED delta (esi never appears as a subreg parent) still bails.
    ps2 = [f(0, "push ebx", 1), f(1, "push esi", 1), f(2, "mov eax, 1", 5),
           f(7, "ret", 1)]
    rc2 = [f(0, "push ebx", 1), f(1, "mov eax, 1", 5), f(6, "ret", 1)]
    assert rh.detect(ps2, rc2, {"Reg swap": 1}) is None


def test_al_squat_rule127_override_signature():
    from c2.commands.al_squat_hints import _ps_copy_and_srcs
    ps = [
        (0, 2, b"\x90\x90", "mov al, ch"),
        (2, 5, b"\x90" * 5, "and eax, 0xff"),
        (7, 2, b"\x90\x90", "mov al, bl"),
        (9, 2, b"\x90\x90", "test al, al"),       # not followed by and -> no
    ]
    assert _ps_copy_and_srcs(ps) == ["ch"]
    assert _ps_copy_and_srcs([]) == []


# NOTE: the former test_reread_hint_* tests were removed -- the
# `reread_hints` module they covered was intentionally deleted in
# a375b060 (its de-invent / Rule-129 logic was fused into
# `deinvent_hints.py`).  The tests referenced the deleted module and only
# ImportError'd.


def test_ast_pickle_cache_roundtrip(tmp_path, monkeypatch):
    from c2.commands import c_source
    monkeypatch.setattr(c_source, "_AST_CACHE_DIR", tmp_path)
    c_source._parse_c_cached.cache_clear()
    src = "int g; void f(void){ g = 1; }"
    a1 = c_source.parse_c(src, "t.c")
    c_source._parse_c_cached.cache_clear()   # force disk path
    a2 = c_source.parse_c(src, "t.c")
    assert a2.ext[1].decl.name == "f"
    assert len(list(tmp_path.glob("*.ast.pkl"))) == 1

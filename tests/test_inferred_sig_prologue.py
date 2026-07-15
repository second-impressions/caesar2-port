"""Tests for callee-side prologue / calling-convention inference in
``infer_sig`` against real PS.EXE functions.

These lock in the asm-derived classification logic added while draining
signature drift:

* the __watcall callee-side prefix property (a high-index live-in reg
  implies every lower-index reg is a parameter slot),
* cdecl call-argument forwarding (`push eax; call open`),
* callee-save detection across tail-merge (the matching `pop` lives in
  the donor) and shared-epilogue exits (written-before-read),
* the `ret <imm>` watcall stack-arg signal, gated on register-calling
  evidence so non-default ABIs (Smacker's RADMALLOC) are not misread.
"""
from c2.commands.inferred_sig import infer_sig


def _argc(name: str) -> int:
    sig = infer_sig(name)
    return len(sig.arg_regs) + len(sig.stack_args)


def test_prefix_property_dummy_param():
    # test_for_ns_polar_walls takes (unused EAX, EDX y, EBX sptr): the
    # body reads EDX+EBX only, but EBX at index 2 implies a 3-arg list.
    sig = infer_sig("test_for_ns_polar_walls")
    assert sig.arg_regs == ["eax", "edx", "ebx"]


def test_cdecl_forward_param():
    # loadmodel forwards its fname arg straight to cdecl `open`
    # (`push eax; call open`); EAX must be detected as a parameter.
    sig = infer_sig("loadmodel")
    assert sig.arg_regs == ["eax"]


def test_chk_prologue_not_broken_by_forward_rule():
    # totalXpercent: `push N; call __CHK` stack-check precedes the real
    # callee-saves; the prologue must still find EAX+EDX.
    sig = infer_sig("totalXpercent")
    assert sig.arg_regs == ["eax", "edx"]


def test_tail_merge_callee_save_not_a_param():
    # act_baths pushes EBX as a callee-save, but the matching `pop ebx;
    # ret` lives in the tail-merge donor (act_plaza).  EBX must NOT be
    # mistaken for a forwarded/spilled parameter.
    assert infer_sig("act_baths").arg_regs == []


def test_shared_epilogue_callee_save():
    # no_high_beeps saves EDX then clobbers it (`mov edx, eax`); the
    # incoming EDX value is dead, so it is a callee-save, not an arg.
    assert infer_sig("no_high_beeps").arg_regs == ["eax"]


def test_ret_imm_implies_watcall_stack_args():
    # create_figure: register args sit behind a loop back-edge the
    # forward walk can't reach, but `ret 0xc` + prologue arg spills prove
    # 4 register args + 3 stack args == 7 total.
    sig = infer_sig("create_figure")
    assert len(sig.arg_regs) == 4
    assert _argc("create_figure") == 7


def test_ret_imm_not_misread_for_stack_convention():
    # RADMALLOC (Smacker, `#pragma aux ... parm routine []`) cleans its
    # stack with `ret 4` but reads its parameter from [esp+4] with no
    # register-calling evidence; we must NOT fabricate register args.
    sig = infer_sig("RADMALLOC")
    assert sig.arg_regs == []


def test_cfg_liveness_loop_read_arg():
    # change_sized's 4th arg (ECX, a city_map cell pointer) is read only
    # inside the scan loop, behind a backward branch the forward-only walk
    # never reaches.  CFG liveness must recover it -> 4 args.
    assert infer_sig("change_sized").arg_regs == ["eax", "edx", "ebx", "ecx"]


def test_byte_granular_al_param():
    # test_type_citymap_neighbours_posedge takes one `unsigned char` read
    # via AL while `xor ah, ah` clears the high byte.  Byte-granular
    # liveness must see AL as a parameter (1 arg), not be fooled into
    # treating the AH clear as a full-EAX define.
    assert infer_sig("test_type_citymap_neighbours_posedge").arg_regs == ["eax"]


def test_and_imm_zero_extend_not_a_param():
    # go_16m_palette's `mov al, [m]; and eax, 0xff` zero-extend idiom must
    # not make the masked-off upper bytes of EAX look live-in.  It takes
    # exactly one parameter (the palette pointer in EAX).
    assert infer_sig("go_16m_palette").arg_regs == ["eax"]


def test_pushed_not_spilled_is_callee_save():
    # dock_the_ship_in_good_port pushes EBX as a callee-save (its slot is
    # never read) but a may-liveness infeasible path reads EBX before a
    # write.  "pushed but slot-not-read" must classify EBX as a callee-
    # save, leaving just the EAX parameter.
    assert infer_sig("dock_the_ship_in_good_port").arg_regs == ["eax"]


def test_restored_spill_slot_read_is_not_a_param():
    # evolve_security_activity reads the saved EDX slot ([esp+0x18]) but
    # EDX is restored (popped) -> it's a callee-save read for its incoming
    # value (Rule-77 style), not a parameter spill.  Only EAX is an arg.
    assert infer_sig("evolve_security_activity").arg_regs == ["eax"]

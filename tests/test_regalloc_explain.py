"""Tests for the regalloc model explainer wired into `decomp-verify -v`."""
from c2.commands.regalloc_explain import explain


def _i(asm, addr=0):
    return (addr, 1, b"", asm)


def test_layer6_spill_divergence():
    ps = [_i("push ebx"), _i("ret")]
    rc = [_i("push ebx"), _i("sub esp, 4"), _i("ret")]
    h = explain(ps, rc, {}, True)
    assert h.layer == 6 and "spill" in h.summary


def test_layer5_loop_reload():
    # RC reloads a global ([disp32]) inside the loop; PS hoisted it.
    ps = [_i("mov ebx, dword ptr [0x70000]", 0), _i("mov dword ptr [eax*4], ebx", 6),
          _i("inc eax", 9), _i("cmp eax, 0x64", 10), _i("jl 6", 13)]
    rc = [_i("mov ebx, dword ptr [0x70000]", 6), _i("mov dword ptr [eax*4], ebx", 12),
          _i("inc eax", 15), _i("cmp eax, 0x64", 16), _i("jl 6", 19)]
    h = explain(ps, rc, {}, True)
    assert h.layer == 5 and "reload" in h.summary


def test_layer3_callee_save_swap():
    ps = [_i("push esi"), _i("ret")]
    rc = [_i("push edi"), _i("ret")]
    h = explain(ps, rc, {}, True)
    assert h.layer == 3 and "swap" in h.summary


def test_layer3_caller_saved_reg_swap_via_hist():
    ps = [_i("mov eax, 1")]
    rc = [_i("mov edx, 1")]
    h = explain(ps, rc, {"Reg swap": 2}, True)
    assert h.layer == 3 and "identity swap" in h.summary


def test_layer1_extra_callee_save_with_call():
    ps = [_i("push ebx"), _i("call 0x10"), _i("ret")]
    rc = [_i("push ebx"), _i("push ecx"), _i("call 0x10"), _i("ret")]
    h = explain(ps, rc, {}, True)
    assert h.layer == 1


def test_layer2_extra_callee_save_no_call():
    ps = [_i("push ebx"), _i("ret")]
    rc = [_i("push ebx"), _i("push ecx"), _i("ret")]
    h = explain(ps, rc, {}, True)
    assert h.layer == 2


def test_outside_model_names_rule():
    ps = [_i("imul eax, eax, 10")]
    rc = [_i("lea eax, [eax*4+eax]")]
    h = explain(ps, rc, {"Rule 62": 1}, True)
    assert h.layer == -1 and "Rule 62" in h.lever


def test_none_when_no_diff():
    ps = [_i("mov eax, 1")]
    rc = [_i("mov eax, 1")]
    assert explain(ps, rc, {}, False) is None


def test_render_lines_drift_warning():
    from c2.commands.regalloc_hints import RegallocHint, render_lines
    h = RegallocHint(func="f", cost_model={}, loop_base=10,
                     allocs=[{"savings": 3, "regclass_name": "dword",
                              "reg_name": "EAX", "nameclass_name": "N_TEMP"}],
                     spilled=0,
                     drift=["  given_regs DRIFT at alloc #7 ...", "  ^ ..."])
    txt = "\n".join(render_lines(h))
    assert "given_regs DRIFT (1 alloc(s))" in txt
    assert "UNRELIABLE" in txt


def test_render_lines_no_drift_silent():
    from c2.commands.regalloc_hints import RegallocHint, render_lines
    h = RegallocHint(func="f", cost_model={}, loop_base=10,
                     allocs=[{"savings": 3, "regclass_name": "dword",
                              "reg_name": "EAX", "nameclass_name": "N_TEMP"}],
                     spilled=0)
    assert "DRIFT" not in "\n".join(render_lines(h))

"""Tests for the Rule 123 split-temp merge detector."""
from c2.commands import merge_hints as MH


def _a(reg, sav, cls="dword", nc="N_TEMP", line=0):
    return {"reg_name": reg, "savings": sav, "regclass_name": cls,
            "nameclass_name": nc, "defline": line}


def test_merge_detects_byte_pair_over_dword_owner():
    # ferret shape: i=EAX 61, addr=EDX 50, j=EBX 41, byte 30+20 (split temp)
    routine = {"alloc": [
        _a("EAX", 61, line=10), _a("EDX", 50), _a("EBX", 41, line=12),
        _a("CH", 30, cls="byte", line=18), _a("CH", 20, cls="byte"),
    ]}
    h = MH.detect(routine, {"EBX", "ECX"})
    assert h is not None
    assert h.owner_name == "EBX" and h.owner_sav == 41
    assert {h.t1_sav, h.t2_sav} == {30, 20} and h.cls == "byte"
    assert "in-place compound" in MH.render(h)


def test_merge_prefers_locatable_byte_pair():
    routine = {"alloc": [
        _a("EBX", 41, line=12),
        _a("EDX", 30), _a("EDX", 25),                      # dword pair, no lines
        _a("CH", 30, cls="byte", line=18), _a("CH", 20, cls="byte", line=19),
    ]}
    h = MH.detect(routine, {"EBX", "ECX"})
    assert h.cls == "byte" and h.t1_line == 18 and h.t2_line == 19


def test_merge_requires_sum_above_owner():
    routine = {"alloc": [
        _a("EBX", 60, line=12),
        _a("CH", 30, cls="byte", line=18), _a("CH", 20, cls="byte", line=19),
    ]}
    assert MH.detect(routine, {"EBX", "ECX"}) is None


def test_merge_ignores_named_locals_and_far_lines():
    routine = {"alloc": [
        _a("EBX", 41, line=12),
        _a("CH", 30, cls="byte", nc="N_USER", line=18),    # named: no merge
        _a("CH", 20, cls="byte", line=19),
        _a("DL", 25, cls="byte", line=80),                 # too far from 19
    ]}
    assert MH.detect(routine, {"EBX", "ECX"}) is None


def test_merge_no_owner_in_swap_set():
    routine = {"alloc": [_a("EAX", 61), _a("CH", 30, cls="byte"),
                         _a("CH", 20, cls="byte")]}
    assert MH.detect(routine, {"EBX", "ECX"}) is None


# ── Rule 132: copy-then-op vs op-in-place ───────────────────────────────

def _r132_rows(ps_copy=True):
    # copy side: mov ecx,eax / sub ecx,ebx / mov [g],ecx
    # in-place side: sub eax,ebx / mov [g],eax
    copy = [
        (0, 2, b"\x90" * 2, "mov ecx, eax"),
        (2, 2, b"\x90" * 2, "sub ecx, ebx"),
        (4, 6, b"\x90" * 6, "mov dword ptr [0x43054], ecx"),
    ]
    inpl = [
        (0, 2, b"\x90" * 2, "sub eax, ebx"),
        (2, 5, b"\x90" * 5, "mov dword ptr [0x465d4], eax"),
        None,
    ]
    a, b = (copy, inpl) if ps_copy else (inpl, copy)
    return [(a[i], b[i], True) for i in range(3)]


def test_rule_132_ps_side_copy():
    from c2.commands.rule_hints import _find_rule_132_rows
    hints = _find_rule_132_rows(_r132_rows(ps_copy=True))
    assert hints, "PS-side copy must be detected"
    h = list(hints.values())[0]
    assert h.rule == "Rule 132" and "PS preserves EAX" in h.summary


def test_rule_132_recomp_side_copy():
    from c2.commands.rule_hints import _find_rule_132_rows
    hints = _find_rule_132_rows(_r132_rows(ps_copy=False))
    assert hints
    h = list(hints.values())[0]
    assert "recomp preserves EAX" in h.summary


def test_rule_132_both_sides_copy_suppressed():
    from c2.commands.rule_hints import _find_rule_132_rows
    copy = [
        (0, 2, b"\x90" * 2, "mov ecx, eax"),
        (2, 2, b"\x90" * 2, "sub ecx, ebx"),
    ]
    rows = [(copy[i], copy[i], True) for i in range(2)]
    assert not _find_rule_132_rows(rows)


# ── Rule 133: cwde vs movsx word-seat flip ──────────────────────────────

def test_rule_133_cwde_vs_movsx():
    from c2.commands.rule_hints import detect_rule_133
    ps = (0, 3, b"\x0f\xbf\xc2", "movsx eax, dx")
    rc = (0, 1, b"\x98", "cwde")
    h = detect_rule_133(ps, rc)
    assert h and h.rule == "Rule 133" and "recomp has the short in AX" in h.summary
    h2 = detect_rule_133(rc, ps)
    assert h2 and "PS has the short in AX" in h2.summary
    # movsx from a byte reg is NOT the word-seat marker
    assert detect_rule_133((0, 3, b"\x0f\xbe\xc2", "movsx eax, dl"), rc) is None

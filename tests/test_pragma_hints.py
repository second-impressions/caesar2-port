"""Tests for the prologue-divergence pragma detector.

Synthetic-only — the detector takes pre-decoded instruction tuples,
so we build them by hand without needing PS.EXE.  An end-to-end PS
smoke test would be redundant with the project-wide `decomp-verify
--json` sweep that already exercises the detector across all 1521
functions.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, ".")

from c2.commands.pragma_hints import (
    PragmaHint,
    detect_prologue_pushes,
    detect_pragma_hint,
    hint_to_json,
    render_hint_lines,
)


# ── InsnT-shaped tuple helpers ────────────────────────────────────────────


def _ins(asm: str, size: int = 1) -> tuple:
    """Build a capstone-shaped instruction tuple ``(addr, size, raw, asm)``.

    Address is always 0 (the detector doesn't read it); raw bytes are
    a placeholder of ``size`` zero-bytes.
    """
    return (0, size, b"\x00" * size, asm)


def _push(reg: str) -> tuple:
    """Build a ``push <reg>`` instruction tuple."""
    return _ins(f"push {reg}", 1)


def _push_imm(imm: str) -> tuple:
    """Build a ``push <imm>`` instruction tuple (stack-probe prefix)."""
    return _ins(f"push {imm}", 2)


def _call(target: str) -> tuple:
    """Build a ``call <target>`` instruction tuple."""
    return _ins(f"call {target}", 5)


def _body(asm: str = "mov eax, ebx") -> tuple:
    """Build a generic body instruction (terminates the prologue scan)."""
    return _ins(asm, 2)


# ── detect_prologue_pushes ────────────────────────────────────────────────


class TestDetectProloguePushes:
    def test_empty(self):
        assert detect_prologue_pushes([]) == ()

    def test_single_push(self):
        insns = [_push("ebx"), _body()]
        assert detect_prologue_pushes(insns) == ("ebx",)

    def test_four_pushes(self):
        insns = [_push("ebx"), _push("ecx"), _push("edx"), _push("esi"), _body()]
        assert detect_prologue_pushes(insns) == ("ebx", "ecx", "edx", "esi")

    def test_stack_probe_skipped(self):
        """`push <imm>; call __CHK` prefix is skipped by the scanner."""
        insns = [
            _push_imm("8"), _call("0x12345"),
            _push("ebx"), _push("esi"), _body(),
        ]
        assert detect_prologue_pushes(insns) == ("ebx", "esi")

    def test_stack_probe_hex_imm(self):
        insns = [
            _push_imm("0x10"), _call("0x12345"),
            _push("ebp"), _body(),
        ]
        assert detect_prologue_pushes(insns) == ("ebp",)

    def test_no_prologue(self):
        """Function with no callee-saves (e.g. a leaf-ish helper)."""
        assert detect_prologue_pushes([_body()]) == ()

    def test_segment_register_push(self):
        """Segment-reg pushes (rare; e.g. __loadds) are picked up."""
        insns = [_push("ds"), _body()]
        assert detect_prologue_pushes(insns) == ("ds",)

    def test_push_eax_unusual(self):
        """EAX pushes are picked up — the detector flags them via _classify."""
        insns = [_push("ebx"), _push("eax"), _body()]
        assert detect_prologue_pushes(insns) == ("ebx", "eax")

    def test_stops_at_non_push(self):
        insns = [_push("ebx"), _push("esi"), _body(), _push("edi")]
        # The trailing push is *after* the body and shouldn't count.
        assert detect_prologue_pushes(insns) == ("ebx", "esi")

    def test_stops_at_push_imm_in_body(self):
        """A `push <imm>` inside the body (e.g. arg-spill) ends the prologue."""
        insns = [_push("ebx"), _push_imm("0x42"), _body()]
        assert detect_prologue_pushes(insns) == ("ebx",)

    def test_stops_at_push_memory(self):
        """`push [...]` (memory operand) isn't a callee-save."""
        insns = [_push("ebx"), _ins("push dword ptr [eax]", 2), _body()]
        assert detect_prologue_pushes(insns) == ("ebx",)


# ── detect_pragma_hint: matching prologues → no hint ──────────────────────


class TestNoHintWhenMatching:
    def test_identical_prologues(self):
        """Both sides push the same regs in the same order → no hint."""
        ps = [_push("ebx"), _push("esi"), _body()]
        rc = [_push("ebx"), _push("esi"), _body()]
        assert detect_pragma_hint(ps, rc) is None

    def test_both_empty(self):
        """Both prologues empty → no hint."""
        assert detect_pragma_hint([_body()], [_body()]) is None

    def test_both_with_chk_prefix(self):
        ps = [_push_imm("8"), _call("X"), _push("ebx"), _body()]
        rc = [_push_imm("8"), _call("X"), _push("ebx"), _body()]
        assert detect_pragma_hint(ps, rc) is None


# ── ps_eax_preserved: high-severity pragma hint ───────────────────────────


class TestPsEaxPreserved:
    def test_eax_only_difference(self):
        """PS pushes EAX, no `[esp]` body access → ps_eax_preserved."""
        ps = [_push("ebx"), _push("eax"), _body()]
        rc = [_push("ebx"), _body()]
        hint = detect_pragma_hint(ps, rc)
        assert hint is not None
        assert hint.category == "ps_eax_preserved"
        assert hint.severity == "high"
        assert "EAX" in hint.summary
        assert "modify exact [edx ebx ecx]" in hint.suggestion
        assert "eax" in hint.ps_only

    def test_eax_plus_other_extras(self):
        """PS pushes EAX + something else → still classified as ps_eax."""
        ps = [_push("ebx"), _push("esi"), _push("eax"), _body()]
        rc = [_push("ebx"), _body()]
        hint = detect_pragma_hint(ps, rc)
        assert hint is not None
        assert hint.category == "ps_eax_preserved"
        assert "eax" in hint.ps_only

    def test_eax_with_stack_slot_access_is_stack_spill(self):
        """PS pushes EAX **and** reads `[esp]` in the body → Rule 24a
        stack-spill, not true EAX preservation."""
        ps = [
            _push("esi"), _push("edi"), _push("eax"),
            _ins("mov edi, dword ptr [esp]", 3),   # spill signature
            _body(),
        ]
        rc = [_push("esi"), _push("edi"), _body()]
        hint = detect_pragma_hint(ps, rc)
        assert hint is not None
        assert hint.category == "ps_stack_spill"
        assert hint.severity == "medium"
        assert "24a" in hint.suggestion or "spill" in hint.suggestion.lower()

    def test_eax_with_esp_plus_offset_is_stack_spill(self):
        """`[esp + 4]` (offset access) also counts as spill signature."""
        ps = [
            _push("eax"), _push("edx"),
            _ins("mov eax, dword ptr [esp + 0x4]", 4),
            _body(),
        ]
        rc = [_push("edx"), _body()]
        hint = detect_pragma_hint(ps, rc)
        assert hint is not None
        assert hint.category == "ps_stack_spill"


# ── ps_loadds / ps_seg_preserved: segment-reg hints ───────────────────────


class TestPsSegregs:
    def test_ds_only(self):
        """PS pushes only DS → `__loadds` suggestion."""
        ps = [_push("ds"), _body()]
        rc = [_body()]
        hint = detect_pragma_hint(ps, rc)
        assert hint is not None
        assert hint.category == "ps_loadds"
        assert hint.severity == "high"
        assert "__loadds" in hint.suggestion

    def test_multiple_segregs(self):
        """PS pushes DS + ES → generic ps_seg_preserved hint."""
        ps = [_push("ds"), _push("es"), _body()]
        rc = [_body()]
        hint = detect_pragma_hint(ps, rc)
        assert hint is not None
        assert hint.category == "ps_seg_preserved"
        assert hint.severity == "high"


# ── Extra/missing single callee-save: medium severity ─────────────────────


class TestExtraCalleeSave:
    def test_ps_extra_edi(self):
        """PS has EDI, recomp doesn't → suggest widening a local."""
        ps = [_push("ebx"), _push("esi"), _push("edi"), _body()]
        rc = [_push("ebx"), _push("esi"), _body()]
        hint = detect_pragma_hint(ps, rc)
        assert hint is not None
        assert hint.category == "ps_extra_callee_save"
        assert hint.severity == "medium"
        assert "edi" in hint.summary
        assert hint.ps_only == ("edi",)

    def test_rc_extra_ebp(self):
        """Recomp enregisters one extra → suggest simplifying."""
        ps = [_push("ebx"), _body()]
        rc = [_push("ebx"), _push("ebp"), _body()]
        hint = detect_pragma_hint(ps, rc)
        assert hint is not None
        assert hint.category == "rc_extra_callee_save"
        assert hint.severity == "medium"
        assert hint.rc_only == ("ebp",)

    def test_swap(self):
        """PS uses ESI where recomp uses EDI → Rule 28a swap."""
        ps = [_push("ebx"), _push("esi"), _body()]
        rc = [_push("ebx"), _push("edi"), _body()]
        hint = detect_pragma_hint(ps, rc)
        assert hint is not None
        assert hint.category == "callee_save_swap"
        assert "esi" in hint.summary and "edi" in hint.summary
        # Generic swaps point at Rule 28a.
        assert "Rule 28" in hint.suggestion
        assert "Rule 87" not in hint.suggestion

    def test_edi_ebp_swap_points_at_rule_87(self):
        """PS uses EDI where recomp uses EBP → Rule 87 lever (dead else-return)."""
        ps = [_push("ebx"), _push("edi"), _body()]
        rc = [_push("ebx"), _push("ebp"), _body()]
        hint = detect_pragma_hint(ps, rc)
        assert hint is not None
        assert hint.category == "callee_save_swap"
        assert {"edi", "ebp"} <= {*hint.ps_only, *hint.rc_only}
        assert "Rule 87" in hint.suggestion
        assert "else return" in hint.suggestion


# ── Structural divergence (many regs differ) ─────────────────────────────


class TestStructuralDivergence:
    def test_ps_two_extras(self):
        ps = [_push(r) for r in ("ebx", "ecx", "edx", "esi", "edi", "ebp")] + [_body()]
        rc = [_push(r) for r in ("ebx", "ecx", "edx", "esi")] + [_body()]
        hint = detect_pragma_hint(ps, rc)
        assert hint is not None
        assert hint.category == "structural_divergence"
        assert hint.severity == "low"
        assert set(hint.ps_only) == {"edi", "ebp"}

    def test_two_for_two_swap(self):
        """ESI/EDI on PS, EDI/EBP on recomp — same length, different set."""
        ps = [_push("ebx"), _push("esi"), _push("edi"), _body()]
        rc = [_push("ebx"), _push("edi"), _push("ebp"), _body()]
        hint = detect_pragma_hint(ps, rc)
        assert hint is not None
        # one-for-one swap (esi/ebp differ) — both ps_only and rc_only are size 1
        # but the symmetric branch in _classify covers this.
        assert hint.category in ("callee_save_swap", "structural_divergence")


# ── prologue_order divergence ─────────────────────────────────────────────


class TestPrologueOrder:
    def test_same_set_different_order(self):
        """Same regs, different push order → low-severity prologue_order hint.

        Note: Watcom's prologue emitter is deterministic for a given
        `state.used` set, so this case is rare in practice but real.
        """
        ps = [_push("ebx"), _push("ecx"), _body()]
        rc = [_push("ecx"), _push("ebx"), _body()]
        hint = detect_pragma_hint(ps, rc)
        assert hint is not None
        assert hint.category == "prologue_order"
        assert hint.severity == "low"


# ── Serialisation ─────────────────────────────────────────────────────────


class TestSerialisation:
    def test_hint_to_json_roundtrip(self):
        ps = [_push("ebx"), _push("esi"), _push("edi"), _body()]
        rc = [_push("ebx"), _push("esi"), _body()]
        hint = detect_pragma_hint(ps, rc)
        d = hint_to_json(hint)
        assert d["category"] == "ps_extra_callee_save"
        assert d["severity"] == "medium"
        assert d["ps_pushes"] == ["ebx", "esi", "edi"]
        assert d["rc_pushes"] == ["ebx", "esi"]
        assert d["ps_only"] == ["edi"]
        assert d["rc_only"] == []
        assert "suggestion" in d
        assert "summary" in d

    def test_render_hint_lines(self):
        ps = [_push("ebx"), _push("eax"), _body()]
        rc = [_push("ebx"), _body()]
        hint = detect_pragma_hint(ps, rc)
        lines = render_hint_lines(hint)
        assert len(lines) == 2     # summary + suggestion
        assert "EAX" in lines[0]
        assert lines[1].startswith("    →")


# ── Sanity guard against regression on the web.c discovery ────────────────


class TestWebCRegression:
    """The `push_node_value` discovery that motivated this detector.

    Confirms the detector would have flagged the prologue divergence
    we hit before fixing it (PS pushes ebx/ecx/edx/esi, recomp without
    `int building` pushes only ebx/ecx/edx).
    """

    def test_push_node_value_prefix(self):
        ps = [_push(r) for r in ("ebx", "ecx", "edx", "esi")] + [_body()]
        rc = [_push(r) for r in ("ebx", "ecx", "edx")] + [_body()]
        hint = detect_pragma_hint(ps, rc)
        assert hint is not None
        assert hint.category == "ps_extra_callee_save"
        assert hint.ps_only == ("esi",)
        # The hint should point the agent at widening a local — which
        # is exactly the `unsigned char building` → `int building` fix.
        assert "int" in hint.suggestion.lower()

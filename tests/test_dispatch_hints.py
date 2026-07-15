"""Tests for the switch<->jump-table dispatch mismatch hint."""
import sys
sys.path.insert(0, '.')

from c2.commands.dispatch_hints import (
    ps_has_jump_table, detect_dispatch_mismatch, _switch_index, SwitchInfo,
)

# ── ps_has_jump_table: jmp through an indexed table ──────────────────────────
def insn(text):
    return (0, len(text), b"", text)

jt = [insn("push edx"), insn("cmp edx, 7"), insn("ja 0x5185a"),
      insn("jmp cs:[edx*4 + 0x416ab]")]
assert ps_has_jump_table(jt) is True
print("✓ jmp [reg*4+table] detected as jump table")

# A call-table (function pointer array) is NOT a switch jump table.
ct = [insn("movsx eax, byte ptr [eax + 0x437f0]"),
      insn("call dword ptr [eax*4 + 0xa0a0]")]
assert ps_has_jump_table(ct) is False
print("✓ call [reg*4+table] (fn-ptr) is NOT a jump table")

# A compare chain (if/else-if lowering) has no jump table.
cc = [insn("cmp edx, 7"), insn("jne 0x4d2c8"),
      insn("cmp edx, 1"), insn("jne 0x4d2d5")]
assert ps_has_jump_table(cc) is False
print("✓ cmp/jne chain is NOT a jump table")

# jmp [reg*8 + ...] (8-byte stride) also counts.
assert ps_has_jump_table([insn("jmp dword ptr [eax*8 + 0x1234]")]) is True
# A plain indirect jmp [reg] (no scale, no disp) is not a table.
assert ps_has_jump_table([insn("jmp dword ptr [eax]")]) is False
print("✓ stride *8 counts; plain jmp [reg] does not")

# PRE-SCALED table: `shl ebp,2; jmp cs:[ebp + 0x1d1cf]` -- the scale is
# applied earlier so the jmp operand has only a displacement, not *4.
# (This was a detector false-negative: move_to_tb_value etc.)
pre = [insn("shl ebp, 2"), insn("jmp cs:[ebp + 0x1d1cf]")]
assert ps_has_jump_table(pre) is True
assert ps_has_jump_table([insn("jmp dword ptr [ebp + 0x1d1cf]")]) is True
print("✓ pre-scaled jmp [reg+disp] table detected (no *4 in operand)")

# ── detect_dispatch_mismatch: monkeypatch the source index ──────────────────
import c2.commands.dispatch_hints as dh

_orig = dh._switch_index
dh._switch_index = lambda *a, **k: {
    "switchy": SwitchInfo(cases=6, fall=0),
    "fally":   SwitchInfo(cases=4, fall=3),
}
try:
    # source switch + NO jump table -> hint to convert to if/else-if
    h = detect_dispatch_mismatch("switchy", cc)
    assert h and "switch (6 cases)" in h and "if/else-if" in h, h
    print("✓ source switch + no jump table -> convert-to-if/else-if hint")

    # fall-through count surfaced
    h = detect_dispatch_mismatch("fally", cc)
    assert "4 cases, 3 fall-through" in h, h
    print("✓ fall-through count reported")

    # source switch + jump table present -> NO hint (correct switch)
    assert detect_dispatch_mismatch("switchy", jt) is None
    print("✓ source switch + jump table -> no hint")

    # PS jump table + source has NO switch -> hint to add a switch
    h = detect_dispatch_mismatch("nosrc", jt)
    assert h and "use a `switch`" in h, h
    print("✓ jump table + no source switch -> use-switch hint")

    # no switch, no jump table -> nothing
    assert detect_dispatch_mismatch("nosrc", cc) is None
    assert detect_dispatch_mismatch(None, jt) is None
    print("✓ no mismatch / no name -> None")
finally:
    dh._switch_index = _orig

print("\nALL dispatch_hints TESTS PASS")

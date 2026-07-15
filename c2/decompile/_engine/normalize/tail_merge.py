"""Cross-function elision normalization (the umbrella of three patterns).

Watcom 10.0a fuses functions in three distinct ways; all three need the
TARGET bytes to be rewritten so a standalone-TU compile can reach
byte-exact equivalence:

1. **Tail-merge (Rule 42)** — dependent ends in ``jmp donor+N``; the
   donor's shared tail is the real epilogue.  We splice it in.
2. **Forward fall-through** — dependent ends with a non-terminating
   instruction (e.g. ``jne``) and the next byte in the binary is the
   start of another function it was "calling" via physical adjacency.
   We append ``call <next_fn>; ret`` to recreate what an isolated
   compile would emit.
3. **Backward shared-ret jcc** — dependent uses ``jcc city_trouble``
   (etc.) where ``city_trouble`` is a one-byte (``c3``) shared-ret
   function reused by many callers.  An isolated compile would emit
   ``jcc <local_ret>`` instead.  We don't rewrite the bytes (the
   instruction size stays the same) but we mark the displacement as
   relocation-equivalent so the diff classifier treats both forms
   as equal.

Returns :class:`Normalized` carrying every piece downstream needs.
"""

from __future__ import annotations

import capstone

from c2.commands.tail_merge import TailMergeHint, scan_tail_merge_donor
from c2.decompile._engine.toolchains.base import NormalizedTarget

# Back-compat alias — older imports can still say ``from
# c2_ext.normalize.tail_merge import Normalized``.
Normalized = NormalizedTarget


def normalize(
    target_bytes: bytes,
    target_address: int,
    target_fixups: frozenset[int],
    target_lines: tuple[tuple[int, int], ...],
    toolchain,
) -> NormalizedTarget:
    """Return a :class:`Normalized` representation of the target.

    If no tail-merge is detected, returns the bytes unchanged with
    donor fields set to None.  If a tail-merge is detected:

    * The dependent's last (jmp) instruction is removed.
    * The donor's shared tail is appended.
    * Donor-side fixup bytes are remapped to the new offsets.
    * Donor-side line marks are appended (still using donor source lines).
    """
    raw_dep_size = len(target_bytes)

    #  (1) Tail-merge (Rule 42)
    hint = scan_tail_merge_donor(
        target_bytes, target_address, is_vaddr=True,
        symbols_json=toolchain.project.symbols_json,
    )
    # Standalone compile has no other functions in the TU, so any
    # tail-merge donor (same-TU or cross-TU) is unavailable to wcc386
    # \u2014 we always splice the donor's tail in.
    extra_reloc = _backward_shared_ret_relocs(
        target_bytes, target_address, target_fixups, toolchain,
    )

    if hint is None:
        # No tail-merge — try forward fall-through normalization next.
        spliced = target_bytes
        spliced_fixups = set(target_fixups)
        spliced_marks = list(target_lines)
        ft_callee, ft_added, spliced, spliced_fixups = _maybe_append_fallthrough(
            spliced, target_address, spliced_fixups, toolchain,
        )
        return NormalizedTarget(
            bytes_=bytes(spliced),
            fixup_offsets=frozenset(spliced_fixups),
            line_marks=tuple(spliced_marks),
            extra_reloc_offsets=frozenset(extra_reloc),
            donor_name=None,
            donor_boundary=None,
            donor_first_line=None,
            donor_tail_size=0,
            fallthrough_callee=ft_callee,
            fallthrough_added_bytes=ft_added,
            raw_dependent_size=raw_dep_size,
        )

    boundary = hint.jmp_offset_in_self
    spliced = target_bytes[:boundary] + hint.tail_bytes
    # Donor tail fixups: pull from the toolchain's PS code-fixup map
    # for the donor's vaddr range, remap onto the spliced offsets.
    donor_start = hint.donor_start
    donor_tail_size = len(hint.tail_bytes)
    donor_tail_vaddr_start = hint.merge_target
    donor_tail_vaddr_end = donor_tail_vaddr_start + donor_tail_size
    code_base = toolchain._le_bases[0]
    donor_tail_off_in_code = donor_tail_vaddr_start - code_base

    donor_fixups: set[int] = set()
    fixmap = toolchain._ps_le_fixup_map
    for o in range(donor_tail_off_in_code,
                   donor_tail_off_in_code + donor_tail_size):
        if o in fixmap:
            donor_fixups.add(o - donor_tail_off_in_code + boundary)

    # Keep dependent's pre-jmp fixups; jmp's own 4 disp bytes (boundary+1..+4)
    # are dropped along with the jmp itself.
    dep_fixups = {f for f in target_fixups if f < boundary}
    spliced_fixups = dep_fixups | donor_fixups

    # Line marks: dependent's marks unchanged (still in pre-boundary region);
    # donor's marks remapped onto the appended tail.  The donor's first
    # line mark at or after the merge boundary serves as the `D+0`
    # baseline (so D+N is offset from the start of the SHARED tail, not
    # from the donor's overall first line).
    donor_marks_raw = toolchain._line_numbers_by_addr.get(donor_start, [])
    merge_off = hint.merge_offset_in_donor
    donor_tail_marks_raw = [
        (off_in_donor, line)
        for (off_in_donor, line, _file) in donor_marks_raw
        if off_in_donor >= merge_off
    ]
    donor_first_line = donor_tail_marks_raw[0][1] if donor_tail_marks_raw else None
    donor_marks: list[tuple[int, int]] = []
    for off_in_donor, line in donor_tail_marks_raw:
        new_off = boundary + (off_in_donor - merge_off)
        if new_off >= len(spliced):
            continue
        donor_marks.append((new_off, line))

    # Keep dependent marks only up to the boundary (we replaced everything
    # past it).
    dep_marks = tuple(m for m in target_lines if m[0] < boundary)
    spliced_marks = tuple(sorted(dep_marks + tuple(donor_marks)))

    return NormalizedTarget(
        bytes_=bytes(spliced),
        fixup_offsets=frozenset(spliced_fixups),
        line_marks=spliced_marks,
        extra_reloc_offsets=frozenset(extra_reloc),
        donor_name=hint.donor_name,
        donor_boundary=boundary,
        donor_first_line=donor_first_line,
        donor_tail_size=donor_tail_size,
        fallthrough_callee=None,
        fallthrough_added_bytes=0,
        raw_dependent_size=raw_dep_size,
    )


#  helpers


_CS = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
_CS.detail = True


def _same_tu(toolchain, addr_a: int, addr_b: int) -> bool:
    """Are two function addresses in the same source TU?"""
    fa = toolchain._function_at(addr_a)
    fb = toolchain._function_at(addr_b)
    if fa is None or fb is None:
        return False
    tu_a = _tu_for_function(toolchain, fa[0])
    tu_b = _tu_for_function(toolchain, fb[0])
    return tu_a is not None and tu_a == tu_b


def _tu_for_function(toolchain, name: str) -> str | None:
    """Return the basename of the TU file containing ``name``, if known."""
    addr = toolchain._sym_ctx.name_to_addr.get(name)
    if addr is None:
        return None
    marks = toolchain._line_numbers_by_addr.get(addr, [])
    return marks[0][2] if marks else None


def _backward_shared_ret_relocs(
    target_bytes: bytes, target_address: int,
    target_fixups: frozenset[int], toolchain,
) -> set[int]:
    """Find jcc/jmp displacement bytes that target a one-byte shared-ret
    function (`c3`); mark them as relocation-equivalent.

    A standalone-TU compile would have generated an equivalent
    intra-function branch with the SAME mnemonic + same encoded size
    but a different displacement.  Marking the disp bytes as fixups
    lets the diff classifier ignore the displacement difference.
    """
    code_base = toolchain._le_bases[0]
    ps_code, _ = toolchain._ps_code_and_fixups
    extra: set[int] = set()
    for ins in _CS.disasm(target_bytes, target_address):
        off = ins.address - target_address
        if ins.mnemonic == "jmp":
            continue
        if not ins.mnemonic.startswith("j"):
            continue
        # Short jcc (`7x XX`) or long jcc (`0F 8x XX XX XX XX`)
        try:
            ops = list(ins.operands)
        except (AttributeError, capstone.CsError):
            continue
        if not ops or ops[0].type != capstone.x86.X86_OP_IMM:
            continue
        target = ops[0].value.imm
        # Only cross-function targets (outside our function bytes)
        if 0 <= (target - target_address) < len(target_bytes):
            continue
        # Is the target's first byte 0xc3 (ret) AND the byte before isn't
        # part of a larger instruction (i.e. truly a shared-ret fn)?
        tgt_off_in_code = target - code_base
        if tgt_off_in_code < 0 or tgt_off_in_code >= len(ps_code):
            continue
        if ps_code[tgt_off_in_code] != 0xC3:
            continue
        # Mark this insn's displacement bytes as relocations.
        # For short jcc the disp is 1 byte at offset+1; for long
        # jcc (0F 8x) the disp is 4 bytes at offset+2.
        if ins.bytes and ins.bytes[0] == 0x0F:
            for k in range(2, ins.size):
                extra.add(off + k)
        else:
            for k in range(1, ins.size):
                extra.add(off + k)
    return extra


def detect_fallthrough(
    target_bytes: bytes, target_address: int, toolchain,
) -> str | None:
    """Detect forward fall-through into a neighbor function.

    Returns the callee name if the function ends with a non-terminating
    instruction and the next byte in the binary is the start of another
    code symbol; otherwise None.
    """
    insns = list(_CS.disasm(target_bytes, target_address))
    if not insns:
        return None
    last = insns[-1]
    if last.mnemonic in ("ret", "retn", "retf", "iret", "iretd", "jmp"):
        return None
    next_addr = target_address + len(target_bytes)
    ref = toolchain.resolve_code_ref(next_addr)
    if ref is None or ref[1] != 0:
        return None
    return ref[0]


def _maybe_append_fallthrough(
    target_bytes: bytes, target_address: int,
    fixups: set[int], toolchain,
) -> tuple[str | None, int, bytes, set[int]]:
    """Detect forward fall-through but DO NOT append bytes.

    Rationale: appending ``call+ret`` (6 bytes) to the target *over-
    specifies* what the standalone compile produces — Watcom may emit
    a 7-byte ``inverted-jcc + call + ret`` or other equivalents,
    differing in size and encoding from our synthetic appendage.

    Instead, the *consumer* of :class:`Normalized` is expected to mask
    everything past the dependent's original ``raw_dependent_size``
    when forward fall-through is detected.  This makes the comparison
    'first N bytes only', which is what byte equivalence actually means
    here.
    """
    callee = detect_fallthrough(target_bytes, target_address, toolchain)
    return callee, 0, target_bytes, fixups

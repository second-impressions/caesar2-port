"""Detect file-scope-static references the standalone TU cannot satisfy.

A function with a private (PS-internal) static label reference cannot be
extracted into a standalone scratch TU because the static lives only
inside the original TU's source and has no PUBDEF.

Per the v1 design (P), we bail out cleanly with a message rather than
attempting fragile inlining.  Real corpus measurement (Caesar II)
suggests these are vanishingly rare; this module makes the failure
mode explicit.
"""

from __future__ import annotations

from dataclasses import dataclass

from c2_ext.toolchains.base import Toolchain


@dataclass(frozen=True)
class StaticsCheck:
    ok: bool
    message: str
    unresolved_addresses: tuple[int, ...] = ()


def check(toolchain: Toolchain, function_name: str, bytes_: bytes,
          fixup_offsets: frozenset[int]) -> StaticsCheck:
    """Inspect every fixup in the function and verify each resolves to a
    named global / function in the project's symbol table.

    A fixup that resolves to a code or data address with NO symbol
    within a small offset window (16 KiB) is treated as a private
    static reference; we bail out and tell the caller which addresses
    failed.
    """
    # Use the WatcomToolchain's LE fixup map directly — fixup_offsets
    # alone doesn't carry target info.
    fixmap = getattr(toolchain, "_ps_le_fixup_map", None)
    if fixmap is None:
        # Other toolchains may not expose this; skip the check.
        return StaticsCheck(ok=True, message="(statics check skipped: toolchain has no LE fixup map)")

    info = toolchain.function_info(function_name)
    code_base, _data_base = toolchain._le_bases
    fn_off_in_code = info.address - code_base

    unresolved: list[int] = []
    for off in sorted(fixup_offsets):
        # Map function-relative offset to code-section offset
        code_off = fn_off_in_code + off
        rec = fixmap.get(code_off)
        if rec is None:
            # Fixup not in LE map (could be intra-function — that's fine)
            continue
        tgt_obj, tgt_off = rec
        if tgt_obj == 1:
            vaddr = code_base + tgt_off
            resolved = toolchain.resolve_code_ref(vaddr)
        else:
            vaddr = toolchain._le_bases[1] + tgt_off
            resolved = toolchain.resolve_data_ref(vaddr)
        if resolved is None:
            unresolved.append(vaddr)

    if not unresolved:
        return StaticsCheck(ok=True, message="all fixups resolve to named symbols")
    return StaticsCheck(
        ok=False,
        message=(
            f"function {function_name!r} references {len(unresolved)} unresolved "
            f"address(es) (likely file-scope statics in the original TU); "
            f"the standalone-TU model cannot reproduce this. Addresses: "
            + ", ".join(f"0x{a:x}" for a in unresolved[:5])
            + ("..." if len(unresolved) > 5 else "")
        ),
        unresolved_addresses=tuple(unresolved),
    )

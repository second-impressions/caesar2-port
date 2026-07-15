"""Generate per-module .asm files for hand-written C2 assembly modules.

Each function is emitted as a labeled block of WASM-syntax instructions
(byte-identical to PS.EXE after assembly + link).  Local branch targets
are renamed per-function-relatively (``<funcname>L<N>``) so the output
no longer encodes post-link absolute addresses.

This module only powers the single ``c2 decomp`` call site, which always
uses ``relabel_local=True`` mode.  Earlier db-byte / data.asm / per-module
.c stub generators have been retired; they lived in this file until the
cleanup that accompanied switching the build to ``clib3r.lib`` for the
CRT and to the 7-file allowlist for hand-written asm.
"""

from __future__ import annotations

import bisect
import io
import re as _re

from capstone import (
    CS_ARCH_X86,
    CS_GRP_BRANCH_RELATIVE,
    CS_GRP_CALL,
    CS_GRP_JUMP,
    CS_GRP_RET,
    CS_MODE_32,
    CS_OP_IMM,
    CS_OP_MEM,
    Cs,
    CsInsn,
)


# ── Shared helpers ───────────────────────────────────────────────────────────


def build_symbol_name_map(symbols: list[dict]) -> dict[int, str]:
    """Build an offset → unique name map from a list of symbol dicts.

    Disambiguates duplicate names by appending the hex offset.
    """
    name_map: dict[int, str] = {}
    seen_names: set[str] = set()
    for s in sorted(symbols, key=lambda s: s["offset"]):
        raw = s["raw_name"]
        if s["offset"] not in name_map:
            if raw not in seen_names:
                name_map[s["offset"]] = raw
                seen_names.add(raw)
            else:
                unique = f"{raw}_{s['offset']:06X}"
                name_map[s["offset"]] = unique
                seen_names.add(unique)
    return name_map


def _pad_or_trim(data: bytes, target_size: int) -> bytes:
    """Pad with zeros or trim to exact target size."""
    if len(data) < target_size:
        return data + b"\x00" * (target_size - len(data))
    if len(data) > target_size:
        return data[:target_size]
    return data


def _build_fixup_occupied_set(
    fixup_map: dict[int, tuple[int, int]],
) -> set[int]:
    """Build a set of all byte offsets occupied by fixup dd values."""
    occupied: set[int] = set()
    for off in fixup_map:
        for i in range(4):
            occupied.add(off + i)
    return occupied


# ── Capstone disassembly helpers ─────────────────────────────────────────────


def _resolve_data_ref(
    tgt: int,
    data_sym_names: dict[int, str],
    sorted_data_offsets: list[int],
) -> tuple[str, str]:
    """Resolve a data fixup target to ``(extern_base_name, use_expr)``.

    If the target has a direct named data symbol, both fields are
    that name.  Otherwise the target is a sub-field of an unnamed
    structure: walk back to the nearest preceding named data symbol
    and return ``(base_name, "base_name + delta")`` — matching how
    the original hand-written .asm source would have written
    e.g. ``[_lib_para4 + 4]``.  Falls back to a synthesised
    ``_data_XXXXXX`` only when no preceding named symbol exists
    (which doesn't happen for the 7 C2 asm modules).
    """
    direct = data_sym_names.get(tgt)
    if direct is not None:
        return direct, direct
    i = bisect.bisect_right(sorted_data_offsets, tgt) - 1
    if i < 0:
        synth = f"_data_{tgt:06X}"
        return synth, synth
    base_off = sorted_data_offsets[i]
    base_name = data_sym_names[base_off]
    delta = tgt - base_off
    return base_name, f"{base_name} + {delta}"


def _value_in_brackets(op_str: str, raw_val: str) -> bool:
    """Check if raw_val appears inside [...] in the operand string.

    WASM doesn't accept 'offset' inside memory operand brackets.
    E.g., [eax + offset _sym] is invalid, [eax + _sym] is correct.
    But 'mov dword ptr [esp + 14h], offset _sym' needs offset because
    the symbol is the immediate source, not the memory displacement.
    """
    idx = op_str.find(raw_val)
    if idx < 0:
        # Try alternate format
        for fmt in [f"0x{int(raw_val, 16):X}" if raw_val.startswith("0x") else raw_val]:
            idx = op_str.find(fmt)
            if idx >= 0:
                break
    if idx < 0:
        return False
    # Check if there's an open bracket before this position without a close bracket
    before = op_str[:idx]
    return before.rfind("[") > before.rfind("]")


# ── Capstone → WASM mnemonic conversion helpers ─────────────────────────────


# Opcodes where the original binary uses the "r, r/m" direction for a
# reg-reg operation but WASM 10.0a emits the "r/m, r" direction.  Keyed
# by the original (non-WASM) opcode; value is what WASM would emit
# instead.  Direction PROVEN empirically (2026-07): WASM 10.0a assembles
# `mov ebp, esp` → 89 E5, `xor ebx, ebx` → 31 DB, `mov al, bl` → 88 D8
# (the r/m,r store direction) — while MASM/TASM-assembled originals like
# palet.ASM carry 8B EC / 33 DB / 8A C3 (the r,r/m load direction).
# (The table was inverted before 2026-07; it was dead code then — every
# caller passed skip_regreg_check=True.)
_REGREG_NONCANONICAL: dict[int, int] = {
    0x02: 0x00, 0x03: 0x01,  # add r,r/m → add r/m,r
    0x0A: 0x08, 0x0B: 0x09,  # or
    0x12: 0x10, 0x13: 0x11,  # adc
    0x1A: 0x18, 0x1B: 0x19,  # sbb
    0x22: 0x20, 0x23: 0x21,  # and
    0x2A: 0x28, 0x2B: 0x29,  # sub
    0x32: 0x30, 0x33: 0x31,  # xor
    0x3A: 0x38, 0x3B: 0x39,  # cmp
    0x8A: 0x88, 0x8B: 0x89,  # mov
}


def _is_regreg_mismatch(
    code_bin: bytes, addr: int, size: int,
    skip_check: bool = False,
) -> bool:
    """Check if instruction at addr uses a reg-reg encoding that WASM
    would emit differently (opposite opcode direction).

    When skip_check is True, always returns False — used when assembling
    with the original Watcom 10.0a wasm which uses the same encoding
    direction as the original binary.
    """
    if skip_check:
        return False
    if size < 2:
        return False
    opcode = code_bin[addr]
    if opcode not in _REGREG_NONCANONICAL:
        return False
    modrm = code_bin[addr + 1]
    # mod=11 means register-register (no memory operand)
    return (modrm >> 6) == 3


# Capstone → WASM mnemonic translations
_MNEMONIC_MAP = {
    "pushal": "pushad",
    "popal": "popad",
}

# Capstone string instructions that include implicit operands we must strip
_STRING_INSNS = {
    "rep stosd", "rep stosb", "rep stosw",
    "rep movsd", "rep movsb", "rep movsw",
    "stosd", "stosb", "stosw",
    "movsd", "movsb", "movsw",
    "lodsd", "lodsb", "lodsw",
    "scasd", "scasb", "scasw",
    "cmpsd", "cmpsb", "cmpsw",
    "insb", "insw", "insd",
    "outsb", "outsw", "outsd",
    # With repne/repe prefixes
    "repne scasd", "repne scasb", "repne scasw",
    "repe scasd", "repe scasb", "repe scasw",
    "repne cmpsd", "repne cmpsb", "repne cmpsw",
    "repe cmpsd", "repe cmpsb", "repe cmpsw",
    "rep scasd", "rep scasb", "rep scasw",
    "rep cmpsd", "rep cmpsb", "rep cmpsw",
}


def _is_branch(insn: CsInsn) -> bool:
    """True for any control-transfer with an encoded target: call, jmp,
    jcc — AND the rel8-only loop family (``loop``/``loope``/``loopne``),
    which capstone puts ONLY in CS_GRP_BRANCH_RELATIVE, not CS_GRP_JUMP
    (the miss produced a raw-address ``loop 6b0a9h`` in palet.asm)."""
    return (insn.group(CS_GRP_CALL) or insn.group(CS_GRP_JUMP)
            or insn.group(CS_GRP_BRANCH_RELATIVE))


def _hex_to_wasm(m: _re.Match) -> str:
    """Convert 0x1234 → 01234h for WASM syntax."""
    digits = m.group(0)[2:]  # strip '0x'
    if digits[0].isalpha():
        digits = '0' + digits
    return digits + 'h'


def _capstone_to_wasm(
    insn: CsInsn,
    code_bin: bytes,
    fixup_map: dict[int, tuple[int, int]],
    all_code: dict[int, str],
    data_sym_names: dict[int, str],
    sorted_data_offsets: list[int],
    data_fixup_occupied: set[int],
    data_fixup_map: dict[int, tuple[int, int]] | None,
    label_map: dict[int, str],
    skip_regreg_check: bool = False,
) -> str | None:
    """Convert a Capstone instruction to WASM syntax.

    Returns the WASM instruction string, or None if the instruction
    cannot be faithfully represented (reg-reg encoding mismatch,
    unresolvable fixup, or branch into garbage).

    ``label_map`` is the only source of truth for local branch labels:
    if a target lacks a precomputed label and isn't a named global,
    the instruction was decoded from data — force db fallback.
    """
    if _is_regreg_mismatch(code_bin, insn.address, insn.size, skip_regreg_check):
        return None

    mnemonic = insn.mnemonic
    op_str = insn.op_str

    # Instructions that can't be represented in WASM flat model → db fallback
    if mnemonic in ("ljmp", "lcall", "lds", "les", "lfs", "lgs", "lss"):
        return None

    # Map mnemonic
    mnemonic = _MNEMONIC_MAP.get(mnemonic, mnemonic)

    # String instructions: strip implicit operands
    if mnemonic in _STRING_INSNS:
        return f"    {mnemonic}"

    # Segment register moves with 32-bit GP register:
    # The original compiler emits 8C DA ("mov edx, ds") as 2 bytes, but
    # WASM rejects "mov edx, ds" ("operands must be the same size") and
    # "mov dx, ds" adds a 66 prefix (3 bytes).  Force db fallback.
    _SEG_REGS = {"cs", "ds", "es", "fs", "gs", "ss"}
    _REG32_TO_16 = {
        "eax": "ax", "ebx": "bx", "ecx": "cx", "edx": "dx",
        "esi": "si", "edi": "di", "ebp": "bp", "esp": "sp",
    }
    if mnemonic == "mov" and ", " in op_str:
        parts = [p.strip() for p in op_str.split(", ", 1)]
        if len(parts) == 2:
            dst, src = parts
            if src in _SEG_REGS and dst in _REG32_TO_16:
                return None  # 8C modrm — can't express in WASM
            elif dst in _SEG_REGS and src in _REG32_TO_16:
                return None  # 8E modrm — can't express in WASM

    # No operands
    if not op_str:
        return f"    {mnemonic}"

    # Handle fixup (dd offset) inside the instruction
    fixup_off = None
    for byte_off in range(insn.address, insn.address + insn.size):
        if byte_off in fixup_map:
            fixup_off = byte_off
            break

    if fixup_off is not None:
        tgt_obj, tgt_offset = fixup_map[fixup_off]
        if tgt_obj == 1:
            sym = all_code.get(tgt_offset, f"_code_{tgt_offset:06X}")
        elif tgt_obj == 2:
            if tgt_offset in data_fixup_occupied and tgt_offset not in (data_fixup_map or {}):
                return None
            _, sym = _resolve_data_ref(
                tgt_offset, data_sym_names, sorted_data_offsets,
            )
        else:
            return None

        is_mem = any(
            op.type == CS_OP_MEM and op.mem.base == 0 and op.mem.index == 0
            for op in insn.operands
        )

        # Try text replacement: if the hex value appears in the operand string,
        # replace it. Use _value_in_brackets to decide whether to add "offset".
        # Must match the COMPLETE hex token (not a substring like 0x1c767 in 0x1c76700).
        raw_val = f"0x{tgt_offset:x}"
        found_fmt = None
        for fmt in [raw_val, f"0x{tgt_offset:X}"]:
            idx = op_str.find(fmt)
            if idx >= 0:
                end_idx = idx + len(fmt)
                # Ensure not a substring: next char must not be hex digit
                if end_idx >= len(op_str) or op_str[end_idx] not in '0123456789abcdefABCDEF':
                    found_fmt = fmt
                    break

        if found_fmt is not None:
            in_brackets = _value_in_brackets(op_str, found_fmt)
            repl = sym if in_brackets else f"offset {sym}"
            op_str = op_str.replace(found_fmt, repl)
        elif is_mem:
            # Direct memory [0x...] where hex format didn't match
            return None
        elif _is_branch(insn):
            # Direct call/jump — the fixup IS the target address
            op_str = sym
        else:
            raw_val = f"0x{tgt_offset:x}"
            # Check for complete hex token match (not substring)
            idx = op_str.find(raw_val)
            if idx >= 0:
                end_idx = idx + len(raw_val)
                if end_idx < len(op_str) and op_str[end_idx] in '0123456789abcdefABCDEF':
                    return None  # Substring match — misaligned fixup
                in_brackets = _value_in_brackets(op_str, raw_val)
                repl = sym if in_brackets else f"offset {sym}"
                op_str = op_str.replace(raw_val, repl)
            else:
                return None
    else:
        # No fixup — handle jumps/calls.  In relabel mode, label_map is
        # the *only* source of truth for local-branch names: if a target
        # lacks a precomputed label and isn't a named global, the trial
        # decode hit garbage → force db.
        if len(insn.operands) == 1 and insn.operands[0].type == CS_OP_IMM:
            target = insn.operands[0].imm
            if _is_branch(insn):
                if target in label_map:
                    op_str = label_map[target]
                elif target in all_code:
                    op_str = all_code[target]
                else:
                    return None

    # Force near encoding for jumps that the original compiler emitted as near.
    # Without this, WASM may optimise near jumps to short (2-byte) form when the
    # target is within ±128 bytes, producing fewer bytes than the original.
    if insn.group(CS_GRP_JUMP) and len(insn.operands) == 1 and insn.operands[0].type == CS_OP_IMM:
        is_near_jmp = (insn.size == 5 and insn.bytes[0] == 0xE9)      # E9 rel32
        is_near_jcc = (insn.size == 6 and insn.bytes[0] == 0x0F)      # 0F 8x rel32
        if is_near_jmp or is_near_jcc:
            # Only add "near ptr" if not already present and target is a label
            if "near ptr" not in op_str:
                op_str = f"near ptr {op_str}"

    # Force db fallback for push imm32 (opcode 0x68) when the value fits in a
    # signed byte.  WASM always optimises these to push imm8 (opcode 0x6A,
    # 2 bytes), saving 3 bytes — but the original compiler used the 5-byte form.
    if (mnemonic == "push" and insn.size == 5 and insn.bytes[0] == 0x68):
        imm = int.from_bytes(insn.bytes[1:5], "little", signed=True)
        if -128 <= imm <= 127:
            return None  # db fallback

    # Force db fallback for accumulator-specific ALU ops (ADD/SUB/AND/OR/XOR/CMP)
    # with EAX and imm32 fitting in imm8.  WASM optimises e.g. 05 02 00 00 00
    # (add eax, imm32, 5 bytes) to 83 C0 02 (add eax, imm8, 3 bytes).
    _ACCUM_IMM32_OPCODES = {0x05, 0x0D, 0x25, 0x2D, 0x35, 0x3D}  # add/or/and/sub/xor/cmp
    if insn.size == 5 and insn.bytes[0] in _ACCUM_IMM32_OPCODES:
        imm = int.from_bytes(insn.bytes[1:5], "little", signed=True)
        if -128 <= imm <= 127:
            return None  # db fallback

    # Force db fallback for mov [mem], imm32 (C7) when the immediate is a
    # fixup (offset).  WASM 10.0a incorrectly adds a 66 prefix, producing a
    # 16-bit move (7 bytes) instead of 32-bit (8+ bytes).
    if insn.bytes[0] == 0xC7 and insn.size >= 7:
        imm_off = insn.address + insn.size - 4
        if imm_off in fixup_map:
            return None  # db fallback

    # Force db fallback for short jumps at the boundary where WASM switches
    # to near encoding.  WASM uses near for forward dist ≥ 125, even though
    # short (rel8) supports up to 127.  The "short" keyword doesn't force it
    # when the assembled distance exceeds 127 (e.g. after other size changes
    # in the function push the target further away).  Safest: db fallback.
    if insn.group(CS_GRP_JUMP) and len(insn.operands) == 1 and insn.operands[0].type == CS_OP_IMM:
        is_short_jmp = (insn.size == 2 and insn.bytes[0] == 0xEB)
        is_short_jcc = (insn.size == 2 and 0x70 <= insn.bytes[0] <= 0x7F)
        if is_short_jmp or is_short_jcc:
            dist = insn.operands[0].imm - (insn.address + 2)
            if dist >= 125 or dist <= -127:
                return None  # db fallback

    # Convert hex: 0x1234 → 01234h
    op_str = _re.sub(r'0x[0-9a-fA-F]+', _hex_to_wasm, op_str)

    return f"    {mnemonic} {op_str}"


# ── Per-module code ASM generation ───────────────────────────────────────────


def generate_module_asm(
    code_bin: bytes,
    functions: list[dict],
    fixup_map: dict[int, tuple[int, int]],
    code_sym_names: dict[int, str],
    data_sym_names: dict[int, str],
    data_fixup_map: dict[int, tuple[int, int]] | None = None,
    extra_labels: dict[int, str] | None = None,
    force_public: set[int] | None = None,
    skip_regreg_check: bool = False,
) -> str:
    """Generate a single module's .asm file.

    Emits real WASM mnemonics (falling back to db only for reg-reg
    encoding mismatches and a handful of WASM 10.0a quirks).  Local
    branch labels are renamed per-function-relatively as
    ``<funcname>L<N>`` so the output doesn't encode post-link
    absolute addresses.

    Each function is emitted as:
      - Capstone disassembly converted to WASM syntax
      - db bytes only for instructions that can't be faithfully expressed
    """
    sorted_funcs = sorted(functions, key=lambda s: s["offset"])

    # Collect all fixup targets to determine EXTRN declarations
    data_fixup_occupied = _build_fixup_occupied_set(data_fixup_map or {})
    extern_data: set[str] = set()
    extern_code: set[str] = set()

    # Sorted list of named data offsets for nearest-base lookups.
    sorted_data_offsets = sorted(data_sym_names.keys())

    # Synthetic labels for fixup targets to code symbols without debug names.
    synthetic_code: dict[int, str] = {}

    # Scan all fixups in this module's range
    mod_start = sorted_funcs[0]["offset"]
    mod_end = sorted_funcs[-1]["_end"]

    for off in range(mod_start, mod_end):
        if off not in fixup_map:
            continue
        tgt_obj, tgt_offset = fixup_map[off]
        if tgt_obj == 1:
            if tgt_offset not in code_sym_names and tgt_offset not in synthetic_code:
                synthetic_code[tgt_offset] = f"_code_{tgt_offset:06X}"

    all_code = {**code_sym_names, **synthetic_code}

    out = io.StringIO()

    # Canonical name for each function (may be disambiguated)
    def _func_name(f: dict) -> str:
        return code_sym_names.get(f["offset"], f["raw_name"])

    # Names defined in this module (functions + extra labels)
    own_names = {_func_name(f) for f in sorted_funcs}
    if extra_labels:
        own_names.update(extra_labels.values())

    out.write(".386p\n.MODEL FLAT\n\n")

    # PUBLIC declarations
    for f in sorted_funcs:
        name = _func_name(f)
        if not f["is_static"] or (force_public and f["offset"] in force_public):
            out.write(f"PUBLIC {name}\n")
    if extra_labels:
        for name in extra_labels.values():
            out.write(f"PUBLIC {name}\n")
    out.write("\n")

    # Collect EXTRNs needed by this module's fixups.  For data refs we
    # extract the *base* symbol name (e.g. ``_lib_para4``) even when the
    # fixup target is mid-symbol (``_lib_para4 + 4``); the displacement
    # rides as a constant inside the instruction.
    for off in range(mod_start, mod_end):
        if off not in fixup_map:
            continue
        tgt_obj, tgt_offset = fixup_map[off]
        if tgt_obj == 2:
            if tgt_offset in data_fixup_occupied and tgt_offset not in (data_fixup_map or {}):
                continue
            base_name, _ = _resolve_data_ref(
                tgt_offset, data_sym_names, sorted_data_offsets,
            )
            extern_data.add(base_name)
        elif tgt_obj == 1:
            sym = all_code.get(tgt_offset, f"_code_{tgt_offset:06X}")
            if sym not in own_names:
                extern_code.add(sym)

    # Also collect EXTRNs from non-fixup calls/jumps.  Relative calls
    # (E8 rel32) within the same segment don't have fixups but become
    # symbolic `call name` in the .asm output.
    code_seg_size = len(code_bin)
    _md = Cs(CS_ARCH_X86, CS_MODE_32)
    _md.detail = True
    for f in sorted_funcs:
        foff, fend = f["offset"], f["_end"]
        # Build instruction address set for this function
        func_insn_addrs: set[int] = set()
        for insn in _md.disasm(code_bin[foff:fend], foff):
            func_insn_addrs.add(insn.address)
        for insn in _md.disasm(code_bin[foff:fend], foff):
            if not _is_branch(insn):
                continue
            if len(insn.operands) != 1 or insn.operands[0].type != CS_OP_IMM:
                continue
            target = insn.operands[0].imm
            # Skip targets outside code segment (garbage decode)
            if target < 0 or target >= code_seg_size:
                continue
            # Skip intra-module targets
            if mod_start <= target < mod_end:
                continue
            # Skip if the branch instruction itself targets a
            # non-instruction address within this function (garbage data)
            if foff <= target < fend and target not in func_insn_addrs:
                continue
            sym = all_code.get(target)
            if sym is None:
                continue  # No named symbol → skip (garbage decode)
            if sym not in own_names:
                extern_code.add(sym)

    for name in sorted(extern_code):
        out.write(f"EXTRN {name}: PROC\n")
    for name in sorted(extern_data):
        out.write(f"EXTRN {name}: BYTE\n")
    if extern_code or extern_data:
        out.write("\n")

    out.write("_TEXT SEGMENT BYTE PUBLIC USE32 'CODE'\n\n")

    # Pre-compute module-wide branch targets to catch cross-function
    # intra-module calls to unnamed helpers.  Two-pass approach: first
    # compute per-function reachability (to avoid collecting garbage
    # targets from data decoded as code), then collect branch targets
    # only from reachable instructions.
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True

    # Pass 1: compute reachable addresses per function
    all_reachable: set[int] = set()
    for f in sorted_funcs:
        foff, fend = f["offset"], f["_end"]
        f_insns = {i.address: i for i in md.disasm(code_bin[foff:fend], foff)}
        reachable: set[int] = set()
        wl = [foff]
        while wl:
            a = wl.pop()
            if a in reachable or a not in f_insns:
                continue
            reachable.add(a)
            insn = f_insns[a]
            if not insn.group(CS_GRP_RET) and insn.mnemonic != "jmp":
                na = a + insn.size
                if na in f_insns:
                    wl.append(na)
            if insn.group(CS_GRP_JUMP) or insn.group(CS_GRP_BRANCH_RELATIVE):
                if len(insn.operands) == 1 and insn.operands[0].type == CS_OP_IMM:
                    t = insn.operands[0].imm
                    if foff <= t < fend:
                        wl.append(t)
        all_reachable |= reachable

    # Pass 2: collect branch targets only from reachable instructions
    module_branch_targets: set[int] = set()
    for f in sorted_funcs:
        foff, fend = f["offset"], f["_end"]
        for insn in md.disasm(code_bin[foff:fend], foff):
            if insn.address not in all_reachable:
                continue
            if _is_branch(insn):
                if len(insn.operands) == 1 and insn.operands[0].type == CS_OP_IMM:
                    target = insn.operands[0].imm
                    if mod_start <= target < mod_end:
                        module_branch_targets.add(target)
    # Remove targets that already have symbol names
    module_branch_targets -= set(all_code.keys())
    if extra_labels:
        module_branch_targets -= set(extra_labels.keys())

    # Build a module-wide label map keyed by branch-target address.
    # For each function, label names are numbered sequentially (1…N) by
    # ascending address inside the function body.  Cross-function
    # intra-module branches resolve to the owning function's label.
    # Targets that already have a named code symbol fall through to that
    # symbol; they're never added to the map.
    label_map: dict[int, str] = {}
    md_lbl = Cs(CS_ARCH_X86, CS_MODE_32)
    md_lbl.detail = True
    for f in sorted_funcs:
        foff, fend = f["offset"], f["_end"]
        f_insns = {i.address: i for i in md_lbl.disasm(
            code_bin[foff:fend], foff)}
        # Intra-function branch targets (reachable disassembly)
        inner_targets: set[int] = set()
        for ia, insn in f_insns.items():
            if _is_branch(insn) \
                    and len(insn.operands) == 1 \
                    and insn.operands[0].type == CS_OP_IMM:
                t = insn.operands[0].imm
                if foff <= t < fend and t in f_insns:
                    inner_targets.add(t)
        # Cross-function intra-module targets that fall in this
        # function's range (jumped INTO from elsewhere)
        for t in module_branch_targets:
            if foff < t < fend and t in f_insns:
                inner_targets.add(t)
        # Drop the function entry (it's the PUBLIC symbol itself)
        inner_targets.discard(foff)
        # Drop any address that already has a known code symbol
        inner_targets -= set(all_code.keys())
        # Drop any address already named via extra_labels
        if extra_labels:
            inner_targets -= set(extra_labels.keys())
        fname = _func_name(f)
        for i, addr in enumerate(sorted(inner_targets), 1):
            # fname already ends with `_` from Watcom mangling;
            # `<fname>L<N>` reads as e.g. `cls_256x_L1`
            label_map[addr] = f"{fname}L{i}"

    for f in sorted_funcs:
        func_off = f["offset"]
        func_size = f["_end"] - func_off

        fname = _func_name(f)
        out.write(f"; {'═' * 60}\n")
        out.write(f"; {f['name']}\n")
        out.write(f"; {'═' * 60}\n")

        func_extra = {}
        if extra_labels:
            func_extra = {o: n for o, n in extra_labels.items()
                          if func_off <= o < func_off + func_size}

        _emit_asm_mnemonics(
            out, code_bin, func_off, func_size, fname,
            fixup_map, all_code, data_sym_names, sorted_data_offsets,
            func_extra, data_fixup_occupied, data_fixup_map,
            module_branch_targets=module_branch_targets,
            skip_regreg_check=skip_regreg_check,
            label_map=label_map,
        )

        out.write("\n")

    out.write("_TEXT ENDS\nEND\n")
    return out.getvalue()


def _emit_trailing_data(
    out: io.StringIO,
    code_bin: bytes,
    start: int,
    end: int,
    func_extra: dict[int, str],
    fixup_map: dict[int, tuple[int, int]],
    all_code: dict[int, str],
    data_sym_names: dict[int, str],
    sorted_data_offsets: list[int],
    data_fixup_occupied: set[int],
    data_fixup_map: dict[int, tuple[int, int]] | None,
) -> None:
    """Emit trailing data bytes (e.g., jump tables) after last instruction."""
    pos = start
    while pos < end:
        # Emit any labels at this position
        if pos in func_extra:
            out.write(f"{func_extra[pos]}:\n")

        # Check for fixup (dd offset)
        if pos in fixup_map:
            tgt_obj, tgt_off = fixup_map[pos]
            if tgt_obj == 1:
                sym = all_code.get(tgt_off, f"_code_{tgt_off:06X}")
            elif tgt_obj == 2:
                if tgt_off in data_fixup_occupied and tgt_off not in (data_fixup_map or {}):
                    sym = f"_data_{tgt_off:06X}"
                else:
                    _, sym = _resolve_data_ref(
                        tgt_off, data_sym_names, sorted_data_offsets,
                    )
            else:
                sym = f"_obj{tgt_obj}_{tgt_off:06X}"
            out.write(f"    dd offset {sym}\n")
            pos += 4
        else:
            out.write(f"    db 0{code_bin[pos]:02X}h\n")
            pos += 1


def _emit_asm_mnemonics(
    out: io.StringIO,
    code_bin: bytes,
    func_off: int,
    func_size: int,
    fname: str,
    fixup_map: dict[int, tuple[int, int]],
    all_code: dict[int, str],
    data_sym_names: dict[int, str],
    sorted_data_offsets: list[int],
    func_extra: dict[int, str],
    data_fixup_occupied: set[int],
    data_fixup_map: dict[int, tuple[int, int]] | None,
    module_branch_targets: set[int],
    label_map: dict[int, str],
    skip_regreg_check: bool = False,
) -> None:
    """Emit function body as real WASM instructions.

    Falls back to db bytes only for reg-reg encoding mismatches
    (where WASM would emit a different opcode direction) and a few
    WASM 10.0a optimisation quirks (see _capstone_to_wasm).
    """
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True

    end = func_off + func_size

    # First pass: build instruction map and addresses
    insn_list = list(md.disasm(code_bin[func_off:end], func_off))
    insn_addrs: set[int] = {i.address for i in insn_list}
    insn_by_addr: dict[int, CsInsn] = {i.address: i for i in insn_list}

    # Reachability analysis — find instructions reachable from the function
    # entry point.  Unreachable instructions are embedded data (jump tables,
    # lookup tables, etc.) that Capstone decoded as garbage.  They must be
    # emitted as raw db bytes to preserve the original encoding.
    reachable: set[int] = set()
    worklist = [func_off]
    # Also seed from module_branch_targets (cross-function jumps into this
    # function from other reachable code in the same module).
    # Do NOT seed from func_extra — those are label placements that may
    # point into embedded data regions; they become reachable only if
    # reached via the normal control flow seeded here.
    for t in module_branch_targets:
        if func_off < t < end and t in insn_addrs:
            worklist.append(t)

    while worklist:
        addr = worklist.pop()
        if addr in reachable or addr not in insn_by_addr:
            continue
        reachable.add(addr)
        insn = insn_by_addr[addr]
        is_ret = insn.group(CS_GRP_RET)
        is_uncond_jmp = insn.mnemonic == "jmp"
        # Follow fall-through unless ret or unconditional jmp
        if not is_ret and not is_uncond_jmp:
            next_addr = addr + insn.size
            if next_addr in insn_by_addr:
                worklist.append(next_addr)
        # Follow intra-function branch targets
        if insn.group(CS_GRP_JUMP) or insn.group(CS_GRP_BRANCH_RELATIVE):
            if len(insn.operands) == 1 and insn.operands[0].type == CS_OP_IMM:
                target = insn.operands[0].imm
                if func_off <= target < end:
                    worklist.append(target)

    # Collect local branch targets only from REACHABLE instructions.
    local_targets: set[int] = set()
    for addr in reachable:
        insn = insn_by_addr[addr]
        if _is_branch(insn):
            if len(insn.operands) == 1 and insn.operands[0].type == CS_OP_IMM:
                target = insn.operands[0].imm
                if func_off <= target < end and target in insn_addrs:
                    local_targets.add(target)
    for t in module_branch_targets:
        if func_off < t < end and t not in func_extra and t in insn_addrs:
            local_targets.add(t)

    out.write(f"{fname}:\n")

    last_addr = func_off
    for insn in insn_list:
        addr = insn.address

        # Extra labels (mid-function entry points)
        if addr in func_extra:
            out.write(f"{func_extra[addr]}:\n")

        # Local branch target labels.  Every entry in local_targets is also
        # in label_map (label_map is built from the same set, plus
        # module-wide jumps INTO this function).
        if addr in local_targets and addr in label_map:
            out.write(f"{label_map[addr]}:\n")

        # Unreachable instructions (embedded data decoded as code):
        # emit as raw db bytes to preserve original encoding.
        if addr not in reachable:
            # Check for func_extra labels falling mid-instruction
            has_mid = any(addr < off < addr + insn.size for off in func_extra)
            if has_mid:
                for byte_off in range(addr, addr + insn.size):
                    if byte_off in func_extra:
                        out.write(f"{func_extra[byte_off]}:\n")
                    out.write(f"    db 0{code_bin[byte_off]:02X}h\n")
            else:
                raw = code_bin[addr : addr + insn.size]
                hex_bytes = ", ".join(f"0{b:02X}h" for b in raw)
                out.write(f"    db {hex_bytes}\n")
            last_addr = addr + insn.size
            continue

        # Try converting to WASM mnemonic
        wasm_line = _capstone_to_wasm(
            insn, code_bin, fixup_map, all_code,
            data_sym_names, sorted_data_offsets,
            data_fixup_occupied, data_fixup_map,
            label_map=label_map,
            skip_regreg_check=skip_regreg_check,
        )

        # Check if any func_extra labels fall mid-instruction
        mid_labels = {off: name for off, name in func_extra.items()
                      if addr < off < addr + insn.size}

        if mid_labels:
            # Must emit as individual db bytes to insert labels
            for byte_off in range(addr, addr + insn.size):
                if byte_off in func_extra:
                    out.write(f"{func_extra[byte_off]}:\n")
                out.write(f"    db 0{code_bin[byte_off]:02X}h\n")
        elif wasm_line is not None:
            # Emit real instruction
            out.write(wasm_line + "\n")
        else:
            # Encoding mismatch or unresolvable — emit db with comment
            raw = code_bin[addr : addr + insn.size]
            hex_bytes = ", ".join(f"0{b:02X}h" for b in raw)
            out.write(f"    db {hex_bytes}")
            out.write(f"    ; {insn.mnemonic} {insn.op_str}\n")
        last_addr = addr + insn.size

    # Emit trailing bytes after last disassembled instruction (e.g., jump tables)
    if last_addr < end:
        _emit_trailing_data(
            out, code_bin, last_addr, end, func_extra, fixup_map,
            all_code, data_sym_names, sorted_data_offsets,
            data_fixup_occupied, data_fixup_map,
        )

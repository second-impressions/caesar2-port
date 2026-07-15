"""Tests for the Rule 42 tail-merge donor scanner.

Two flavours:

  1. **Synthetic**: hand-crafted byte sequences plus a fake symbol
     table.  Asserts the scanner's logic in isolation — no PS.EXE
     needed.  These run fast and don't depend on the project state.
  2. **PS.EXE smoke**: confirms the scanner finds the known Rule 42
     donor relationships in the live binary (`clear_all_rm` →
     `build_wall_from_elastic`).  Skipped if `data/PS.EXE` or
     `data/out/symbols.json` are missing.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, ".")

from c2.commands.tail_merge import (
    _SymCtx,
    _function_at,
    _sym_cache,
    expand_merged_tail,
    ranges_from_offset_map,
    render_tail_merge_hint,
    scan_tail_merge_donor,
)


# ── Synthetic helpers ─────────────────────────────────────────────────────


def _patch_sym_cache(symbols_json: Path, ctx: _SymCtx) -> None:
    """Inject a fake _SymCtx so the scanner doesn't load real symbols."""
    _sym_cache[symbols_json.resolve()] = ctx


def _make_ctx(
    code_base: int,
    funcs: list[tuple[int, int, str]],   # (start, size, name)
) -> _SymCtx:
    """Build a fake symbol context with `funcs` as the only code symbols."""
    addr_to_name = {start: name for start, _sz, name in funcs}
    name_to_addr = {name: start for start, _sz, name in funcs}
    funcs_sorted = sorted(funcs, key=lambda t: t[0])
    ranges = []
    for i, (start, size, name) in enumerate(funcs_sorted):
        if i + 1 < len(funcs_sorted):
            end = funcs_sorted[i + 1][0]
        else:
            end = start + size
        ranges.append((start, end, name))
    return _SymCtx(
        addr_to_name=addr_to_name,
        name_to_addr=name_to_addr,
        func_ranges=ranges,
        code_base=code_base,
    )


def _e9_jmp(jmp_at_vaddr: int, target_vaddr: int) -> bytes:
    """Encode a near 32-bit jmp from `jmp_at_vaddr` to `target_vaddr`."""
    rel = target_vaddr - (jmp_at_vaddr + 5)
    return b"\xe9" + rel.to_bytes(4, "little", signed=True)


# ── Synthetic tests ───────────────────────────────────────────────────────


def test_no_jmp_returns_none(tmp_path: Path) -> None:
    """Function ending in plain ret has no donor."""
    sym_json = tmp_path / "symbols.json"
    _patch_sym_cache(
        sym_json,
        _make_ctx(0x10000, [(0x10000, 0x40, "f"), (0x10040, 0x40, "g")]),
    )
    # `mov eax, ebx ; ret`
    body = b"\x89\xd8\xc3"
    hint = scan_tail_merge_donor(body, 0x10000, symbols_json=sym_json)
    assert hint is None


def test_self_jmp_returns_none(tmp_path: Path) -> None:
    """A back-jmp inside the function is a loop, not a tail-merge."""
    sym_json = tmp_path / "symbols.json"
    _patch_sym_cache(
        sym_json,
        _make_ctx(0x10000, [(0x10000, 0x40, "f"), (0x10040, 0x40, "g")]),
    )
    body = bytearray(b"\x90" * 0x20)        # 32 bytes of nop
    body += _e9_jmp(0x10020, 0x10000)        # jmp back to start of f
    hint = scan_tail_merge_donor(bytes(body), 0x10000, symbols_json=sym_json)
    assert hint is None


def test_tail_call_returns_none(tmp_path: Path) -> None:
    """Jmp to the *start* of another function is a tail-call, not a merge."""
    sym_json = tmp_path / "symbols.json"
    _patch_sym_cache(
        sym_json,
        _make_ctx(0x10000, [(0x10000, 0x10, "caller"), (0x10010, 0x40, "callee")]),
    )
    body = bytearray(b"\x90" * 0x0b)
    body += _e9_jmp(0x1000b, 0x10010)        # jmp to callee's entry
    hint = scan_tail_merge_donor(bytes(body), 0x10000, symbols_json=sym_json)
    assert hint is None


def test_jmp_into_donor_middle_fires(tmp_path: Path) -> None:
    """The textbook Rule 42 case: jmp into the middle of another fn."""
    sym_json = tmp_path / "symbols.json"
    _patch_sym_cache(
        sym_json,
        _make_ctx(0x10000, [(0x10000, 0x10, "caller"), (0x10100, 0x40, "donor")]),
    )
    body = bytearray(b"\x90" * 0x0b)
    body += _e9_jmp(0x1000b, 0x10120)        # jmp into donor at +0x20

    # Need the donor's tail bytes from a fake "code section".
    code = bytearray(0x200)
    # Donor occupies code[0x100:0x140]; tail starting at +0x20 is
    # 0x140 - 0x120 = 32 bytes ending in ret.
    code[0x120:0x140] = b"\x5d\x5f\x5e\x5b\xc3" + b"\x90" * 27

    hint = scan_tail_merge_donor(
        bytes(body), 0x10000,
        symbols_json=sym_json,
        code_bytes=bytes(code),
        code_base=0x10000,
    )
    assert hint is not None
    assert hint.donor_name == "donor"
    assert hint.donor_start == 0x10100
    assert hint.merge_target == 0x10120
    assert hint.merge_offset_in_donor == 0x20
    assert hint.jmp_offset_in_self == 0x0b
    assert hint.tail_bytes.startswith(b"\x5d\x5f\x5e\x5b\xc3")
    # Disasm decodes pop/ret sequence.
    assert "pop ebp" in hint.tail_disasm[0]
    assert hint.tail_disasm[4].rstrip() == "ret"


def test_section_offset_mode(tmp_path: Path) -> None:
    """`is_vaddr=False` adds code_base when interpreting orig_off."""
    sym_json = tmp_path / "symbols.json"
    _patch_sym_cache(
        sym_json,
        _make_ctx(0x10000, [(0x10000, 0x10, "caller"), (0x10100, 0x40, "donor")]),
    )
    body = bytearray(b"\x90" * 0x0b)
    body += _e9_jmp(0x1000b, 0x10120)
    code = bytearray(0x200)
    code[0x120:0x140] = b"\xc3" + b"\x90" * 31

    # orig_off=0 (= section offset 0 = vaddr 0x10000) with is_vaddr=False
    hint = scan_tail_merge_donor(
        bytes(body), 0,
        is_vaddr=False,
        symbols_json=sym_json,
        code_bytes=bytes(code),
        code_base=0x10000,
    )
    assert hint is not None
    assert hint.donor_name == "donor"


def test_jmp_into_unknown_address_returns_none(tmp_path: Path) -> None:
    """Jmp to an address not covered by any code symbol is rejected."""
    sym_json = tmp_path / "symbols.json"
    _patch_sym_cache(
        sym_json,
        _make_ctx(0x10000, [(0x10000, 0x10, "caller")]),
    )
    body = bytearray(b"\x90" * 0x0b)
    # Pick a target that's a 32-bit signed jmp away but doesn't land
    # inside any known function.
    body += _e9_jmp(0x1000b, 0x70000)
    hint = scan_tail_merge_donor(bytes(body), 0x10000, symbols_json=sym_json)
    assert hint is None


def test_render_hint_format() -> None:
    """`render_tail_merge_hint` produces the expected one-line format."""
    from c2.commands.tail_merge import TailMergeHint
    h = TailMergeHint(
        donor_name="build_wall_from_elastic",
        donor_start=0x67653,
        merge_target=0x678B4,
        merge_offset_in_donor=0x261,
        jmp_offset_in_self=0x94,
        tail_bytes=b"\x5d\x5f\x5e\x5a\x59\x5b\xc3",
        tail_disasm=("pop ebp", "pop edi", "pop esi", "pop edx",
                     "pop ecx", "pop ebx", "ret"),
    )
    out = render_tail_merge_hint(h)
    assert "build_wall_from_elastic+0x261" in out
    assert "7 b" in out
    assert "pop ebp" in out
    assert "ret" in out


def test_render_hint_truncates_long_tails() -> None:
    """Very long tails get an ellipsis after `max_disasm` instructions."""
    from c2.commands.tail_merge import TailMergeHint
    h = TailMergeHint(
        donor_name="big",
        donor_start=0,
        merge_target=0x10,
        merge_offset_in_donor=0x10,
        jmp_offset_in_self=0,
        tail_bytes=b"\x90" * 50,
        tail_disasm=tuple(f"nop{i}" for i in range(20)),
    )
    out = render_tail_merge_hint(h, max_disasm=3)
    assert out.endswith("…")
    assert "nop2" in out
    assert "nop15" not in out


# ── Merged-tail expansion (side-by-side splice) ────────────────────────────


def test_expand_no_trailing_jmp_returns_none() -> None:
    """A body that ends in `ret` has no merged tail to splice."""
    resolve = ranges_from_offset_map({"f": 0, "g": 0x40}, 0x10000)
    body = b"\x89\xd8\xc3"                    # mov eax, ebx ; ret
    assert expand_merged_tail(
        body, 0, code_bytes=b"\x00" * 0x200, code_base=0x10000,
        resolve=resolve,
    ) is None


def test_expand_single_hop_to_ret() -> None:
    """jmp into a donor whose tail is `pop…; ret` returns those bytes."""
    resolve = ranges_from_offset_map({"caller": 0, "donor": 0x100}, 0x10000)
    body = bytearray(b"\x90" * 0x0b)
    body += _e9_jmp(0x1000b, 0x10120)        # jmp into donor at +0x20
    code = bytearray(0x200)
    code[0x120:0x125] = b"\x5d\x5f\x5e\xc3"  # pop ebp; pop edi; pop esi; ret
    exp = expand_merged_tail(
        bytes(body), 0, code_bytes=bytes(code), code_base=0x10000,
        resolve=resolve,
    )
    assert exp is not None
    assert exp.ends_in_ret is True
    assert exp.tail_bytes == b"\x5d\x5f\x5e\xc3"
    assert exp.jmp_rel == 0x0b
    assert len(exp.segments) == 1
    seg = exp.segments[0]
    assert seg.name == "donor"
    assert seg.merge_off == 0x20
    assert seg.length == 4
    assert exp.label == "donor+0x20"


def test_expand_chained_epilogue_follows_hops() -> None:
    """A partial-stub chain `pop ebp; jmp …` → `pop…; ret` concatenates the
    executed epilogue and drops the intermediate jmp."""
    resolve = ranges_from_offset_map(
        {"caller": 0, "stubA": 0x100, "stubB": 0x200}, 0x10000,
    )
    body = bytearray(b"\x90" * 0x0b)
    body += _e9_jmp(0x1000b, 0x10120)        # jmp into stubA at +0x20
    code = bytearray(0x300)
    # stubA: pop ebp ; jmp stubB+0x10
    code[0x120] = 0x5d
    code[0x121:0x126] = _e9_jmp(0x10121, 0x10210)
    # stubB tail: pop edi ; pop esi ; ret
    code[0x210:0x213] = b"\x5f\x5e\xc3"
    exp = expand_merged_tail(
        bytes(body), 0, code_bytes=bytes(code), code_base=0x10000,
        resolve=resolve,
    )
    assert exp is not None
    assert exp.ends_in_ret is True
    # The inter-hop jmp is replaced by stubB's bytes -> straight epilogue.
    assert exp.tail_bytes == b"\x5d\x5f\x5e\xc3"
    assert [s.name for s in exp.segments] == ["stubA", "stubB"]
    assert exp.segments[0].length == 1     # just `pop ebp` before the jmp
    assert exp.segments[1].length == 3     # pop edi; pop esi; ret
    assert "stubA+0x20" in exp.label and "stubB" in exp.label


def test_expand_tail_call_to_function_start_returns_none() -> None:
    """jmp to the *start* of another fn is a tail-call, not an epilogue
    merge — nothing to splice."""
    resolve = ranges_from_offset_map({"caller": 0, "callee": 0x100}, 0x10000)
    body = bytearray(b"\x90" * 0x0b)
    body += _e9_jmp(0x1000b, 0x10100)        # jmp to callee's entry
    exp = expand_merged_tail(
        bytes(body), 0, code_bytes=b"\x00" * 0x200, code_base=0x10000,
        resolve=resolve,
    )
    assert exp is None


def test_ranges_from_offset_map_resolves() -> None:
    """The offset-map resolver reports the owning function + its extent."""
    resolve = ranges_from_offset_map({"a": 0, "b": 0x40, "c": 0x80}, 0x10000)
    assert resolve(0x10000) == ("a", 0x10000, 0x10040)
    assert resolve(0x1003f) == ("a", 0x10000, 0x10040)
    assert resolve(0x10040) == ("b", 0x10040, 0x10080)
    assert resolve(0x10090)[0] == "c"        # last fn gets a synthetic tail
    assert resolve(0x9999) is None           # below the first function


# ── PS.EXE smoke test ─────────────────────────────────────────────────────

_PS_EXE = Path("data/PS.EXE")
_SYMBOLS = Path("data/out/symbols.json")


@pytest.mark.skipif(
    not _PS_EXE.exists() or not _SYMBOLS.exists(),
    reason="data/PS.EXE or data/out/symbols.json not present",
)
def test_clear_all_rm_donor_is_build_wall_from_elastic() -> None:
    """The known Rule 42 donor relationship in PS.EXE.

    `clear_all_rm` ends with `jmp 0x678b4` which lands inside
    `build_wall_from_elastic` at offset 0x261 — the canonical merge
    point.  This is the exact relationship the production verifier
    surfaces today.
    """
    from c2.commands.disasm import disasm_function
    from c2.commands.decomp_verify import _load_le_code_and_fixups

    addr, size, _lines = disasm_function("clear_all_rm")
    code, _ = _load_le_code_and_fixups(_PS_EXE)
    section_off = addr - 0x10000
    body = code[section_off:section_off + size]

    hint = scan_tail_merge_donor(
        body, addr, symbols_json=_SYMBOLS, code_bytes=code, code_base=0x10000,
    )
    assert hint is not None
    assert hint.donor_name == "build_wall_from_elastic"
    assert hint.merge_offset_in_donor == 0x261
    # The shared tail is the 7-byte epilogue.
    assert hint.tail_bytes == b"\x5d\x5f\x5e\x5a\x59\x5b\xc3"
    assert hint.tail_disasm[0] == "pop ebp"
    assert hint.tail_disasm[-1].rstrip() == "ret"


@pytest.mark.skipif(
    not _PS_EXE.exists() or not _SYMBOLS.exists(),
    reason="data/PS.EXE or data/out/symbols.json not present",
)
def test_expand_merged_tail_on_live_function() -> None:
    """`expand_merged_tail` splices `clear_all_rm`'s borrowed 7-byte
    `pop…; ret` epilogue out of its `build_wall_from_elastic` donor."""
    from c2.commands.disasm import disasm_function
    from c2.commands.decomp_verify import _load_le_code_and_fixups
    from c2.commands.tail_merge import _function_at, _load_symbols

    addr, size, _lines = disasm_function("clear_all_rm")
    code, _ = _load_le_code_and_fixups(_PS_EXE)
    sym = _load_symbols(_SYMBOLS)
    section_off = addr - 0x10000
    body = code[section_off:section_off + size]

    exp = expand_merged_tail(
        body, section_off, code_bytes=code, code_base=0x10000,
        resolve=lambda va: _function_at(sym, va),
    )
    assert exp is not None
    assert exp.ends_in_ret is True
    assert exp.tail_bytes == b"\x5d\x5f\x5e\x5a\x59\x5b\xc3"
    assert exp.segments[0].name == "build_wall_from_elastic"
    assert exp.segments[0].merge_off == 0x261
    assert exp.label.startswith("build_wall_from_elastic+0x261")


@pytest.mark.skipif(
    not _PS_EXE.exists() or not _SYMBOLS.exists(),
    reason="data/PS.EXE or data/out/symbols.json not present",
)
def test_build_wall_from_elastic_does_not_donate_to_anyone() -> None:
    """The donor itself ends in `ret`, not in a jmp — no hint."""
    from c2.commands.disasm import disasm_function
    from c2.commands.decomp_verify import _load_le_code_and_fixups

    addr, size, _lines = disasm_function("build_wall_from_elastic")
    code, _ = _load_le_code_and_fixups(_PS_EXE)
    section_off = addr - 0x10000
    body = code[section_off:section_off + size]
    hint = scan_tail_merge_donor(
        body, addr, symbols_json=_SYMBOLS, code_bytes=code, code_base=0x10000,
    )
    assert hint is None


# ── _is_tail_blocked classifier (tail_merge_rank) ───────────────────────────

def test_is_tail_blocked_classifier() -> None:
    """A dependent is tail-blocked iff every diff byte is in the last 12 b."""
    from c2.commands.tail_merge_rank import _is_tail_blocked, _TAIL_WINDOW

    # Exact function — never blocked.
    assert _is_tail_blocked({"size": 100, "diff_byte_offsets": []}) is False

    # Diff entirely in the shared-tail window → tail-blocked.
    assert _is_tail_blocked(
        {"size": 100, "diff_byte_offsets": [95, 98, 99]}
    ) is True

    # Diff at the very last byte (e.g. put_danger_flag jmp opcode).
    assert _is_tail_blocked(
        {"size": 19, "diff_byte_offsets": [14]}
    ) is True

    # A single body diff anywhere earlier → NOT tail-blocked.
    assert _is_tail_blocked(
        {"size": 100, "diff_byte_offsets": [40, 95, 99]}
    ) is False

    # Boundary: exactly size - _TAIL_WINDOW is inside the window.
    assert _is_tail_blocked(
        {"size": 100, "diff_byte_offsets": [100 - _TAIL_WINDOW]}
    ) is True
    assert _is_tail_blocked(
        {"size": 100, "diff_byte_offsets": [100 - _TAIL_WINDOW - 1]}
    ) is False

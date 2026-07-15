"""Watcom Debug Info 3.0 parser.

Parses the debug section appended to the end of a DOS/4GW executable:
  - Master debug header (14 bytes at EOF)
  - Source language table
  - Segment address table
  - Section header + module info + global symbols + address info
  - Line number info (demand data)

The debug info describes a 32-bit LE (Linear Executable) with two objects:
  - Object 1 (code): 508KB at base 0x10000
  - Object 2 (data): 562KB at base 0x90000

Symbol offsets are direct flat offsets into the LE objects.
Line number offsets are relative to their module's addr_info base.

Reference: open-watcom-v2/bld/watcom/h/wdbginfo.h
Reference: open-watcom-v2/bld/comp_cfg/h/langenv.h (name decoration patterns)
Reference: open-watcom-v2/bld/cc/c/cfeinfo.c (GetNamePattern / FEExtName)
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from pathlib import Path

from construct import (
    Container,
    Int8ul,
    Int16ul,
    Int32ul,
    Struct,
)


# ── Constants & Construct definitions ────────────────────────────────────────

WAT_DBG_SIGNATURE = 0x8386

# Master debug header — 14 bytes at the very end of the file
MasterDbgHeader = Struct(
    "signature" / Int16ul,      # 0x8386
    "exe_major_ver" / Int8ul,   # 3
    "exe_minor_ver" / Int8ul,   # 0
    "obj_major_ver" / Int8ul,   # 1
    "obj_minor_ver" / Int8ul,   # 0 or 3
    "lang_size" / Int16ul,      # size of language table
    "segment_size" / Int16ul,   # size of segment address table
    "debug_size" / Int32ul,     # total debug info size (including this header)
)

# Section debug header — 14 bytes
SectionDbgHeader = Struct(
    "mod_offset" / Int32ul,
    "gbl_offset" / Int32ul,
    "addr_offset" / Int32ul,
    "section_size" / Int32ul,
    "section_id" / Int16ul,
)

# Global symbol kind flags
GBL_KIND_STATIC = 0x01
GBL_KIND_DATA = 0x02
GBL_KIND_CODE = 0x04


# ── Watcom name demangling ───────────────────────────────────────────────────
#
# The Watcom C compiler decorates symbol names based on the target system
# and calling convention. For x86 targets (DOS, OS/2, Windows):
#
#   Code (functions):  pattern "*_"  → name + trailing underscore
#   Data (globals):    pattern "_*"  → leading underscore + name
#
# Where "*" is the base name placeholder. These are the default patterns
# for the __watcall (register-based) calling convention.
#
# Source: open-watcom-v2/bld/comp_cfg/h/langenv.h lines 74-75:
#   #define TS_DATA_MANGLE  "_*"
#   #define TS_CODE_MANGLE  "*_"
#
# The pattern is applied in open-watcom-v2/bld/cg/c/objname.c GetExtName(),
# which splits the pattern on "*" into prefix and suffix, then wraps the
# base name.
#
# For __cdecl on x86, the pattern is "_*" for both code and data (leading
# underscore only). For __stdcall it's "_*@<n>" where <n> is parameter
# byte count. These are set via #pragma aux in the runtime headers.
#
# Since Caesar II is compiled with default __watcall convention, we can
# reliably reverse the decoration:
#   - Code symbol ending with "_"  → strip suffix → __watcall function
#   - Data symbol starting with "_" → strip prefix → __watcall data
#   - No decoration match → leave as-is (e.g. assembly symbols)


def demangle_watcom_symbol(
    name: str, is_code: bool, is_data: bool
) -> tuple[str, str | None]:
    """Demangle a Watcom-decorated symbol name.

    Reverses the x86 name decoration applied by the Watcom C compiler.
    Returns (demangled_name, calling_convention).

    The calling convention is only meaningful for code symbols:
      - "__watcall" for the default register-based convention (pattern "*_")
      - None for data symbols or undecorated names

    Source: open-watcom-v2/bld/comp_cfg/h/langenv.h
      TS_CODE_MANGLE = "*_"  (code: name + trailing underscore)
      TS_DATA_MANGLE = "_*"  (data: leading underscore + name)
    """
    if is_code and name.endswith("_") and len(name) > 1:
        # Code symbol with trailing underscore → __watcall function
        # Pattern: "*_" from TS_CODE_MANGLE
        return name[:-1], "__watcall"

    if is_data and name.startswith("_") and len(name) > 1:
        # Data symbol with leading underscore → __watcall decorated data
        # Pattern: "_*" from TS_DATA_MANGLE
        # Note: calling convention is not meaningful for data symbols
        return name[1:], None

    # No decoration match — assembly symbols, intrinsics, or custom pragmas
    return name, None


# ── Data classes ─────────────────────────────────────────────────────────────


@dataclass
class ModuleInfo:
    """A source module (compilation unit)."""

    index: int
    name: str
    language: str
    locals_entries: int
    locals_offset: int
    types_entries: int
    types_offset: int
    lines_entries: int
    lines_offset: int


@dataclass
class GlobalSymbol:
    """A global symbol (function or data label).

    The ``name`` field holds the raw (decorated) name as stored in the
    debug info. Use ``demangled_name`` for the clean source-level name
    with Watcom decoration stripped.
    """

    name: str
    segment: int
    offset: int
    module_index: int
    kind: int
    kind_str: str = ""
    demangled_name: str = ""
    calling_convention: str | None = None

    def __post_init__(self) -> None:
        parts = []
        if self.kind & GBL_KIND_STATIC:
            parts.append("static")
        if self.kind & GBL_KIND_CODE:
            parts.append("code")
        if self.kind & GBL_KIND_DATA:
            parts.append("data")
        self.kind_str = " ".join(parts) if parts else "unknown"

        # Demangle the Watcom-decorated name
        self.demangled_name, self.calling_convention = demangle_watcom_symbol(
            self.name, self.is_code, self.is_data
        )

    @property
    def is_code(self) -> bool:
        return bool(self.kind & GBL_KIND_CODE)

    @property
    def is_data(self) -> bool:
        return bool(self.kind & GBL_KIND_DATA)

    @property
    def is_static(self) -> bool:
        return bool(self.kind & GBL_KIND_STATIC)


@dataclass
class LineEntry:
    """A source line to code offset mapping."""

    line: int
    code_offset: int


@dataclass
class LineSegment:
    """Line number info for one segment of a module."""

    addr_info_offset: int
    entries: list[LineEntry] = field(default_factory=list)


@dataclass
class AddrEntry:
    """One module-range entry inside a seg_dbg_info block."""

    size: int
    mod: int


@dataclass
class SegAddrInfo:
    """Parsed seg_dbg_info: one logical segment block in the address info section.

    ``base_offset`` is the linker-time flat logical offset from the start
    of the code (or data) group.
    ``base_segment`` is the linker's internal segment index (1=code, 2=data).
    """

    base_offset: int
    base_segment: int
    entries: list[AddrEntry]


@dataclass
class WatcomDebugInfo:
    """Complete parsed Watcom debug info."""

    exe_major_ver: int
    exe_minor_ver: int
    obj_major_ver: int
    obj_minor_ver: int
    debug_size: int
    languages: list[str]
    segment_table: list[int]
    modules: list[ModuleInfo]
    symbols: list[GlobalSymbol]
    addr_info: list[SegAddrInfo] = field(default_factory=list)
    line_numbers: dict[int, list[LineSegment]] = field(default_factory=dict)


# ── Parsing functions ────────────────────────────────────────────────────────


def parse_watcom_debug(filepath: Path) -> WatcomDebugInfo:
    """Parse Watcom Debug Info 3.0 from a DOS4GW executable."""
    data = filepath.read_bytes()
    file_size = len(data)

    # Step 1: Read master header from end of file
    master_offset = file_size - MasterDbgHeader.sizeof()
    master = MasterDbgHeader.parse(data[master_offset:])

    if master.signature != WAT_DBG_SIGNATURE:
        raise ValueError(
            f"Invalid Watcom debug signature: 0x{master.signature:04X} "
            f"(expected 0x{WAT_DBG_SIGNATURE:04X})"
        )

    is_v3 = master.exe_major_ver >= 3
    debug_start = file_size - master.debug_size

    # Step 2: Read language table
    lang_data = data[debug_start : debug_start + master.lang_size]
    languages: list[str] = []
    pos = 0
    while pos < len(lang_data):
        end = lang_data.index(b"\x00", pos)
        lang = lang_data[pos:end].decode("ascii", errors="replace")
        if lang:
            languages.append(lang)
        pos = end + 1

    # Step 3: Read segment address table
    seg_table_start = debug_start + master.lang_size
    segment_table: list[int] = []
    for i in range(master.segment_size // 2):
        seg_val = Int16ul.parse(
            data[seg_table_start + i * 2 : seg_table_start + i * 2 + 2]
        )
        segment_table.append(seg_val)

    # Step 4: Read section header
    section_start = debug_start + master.lang_size + master.segment_size
    section_hdr = SectionDbgHeader.parse(
        data[section_start : section_start + SectionDbgHeader.sizeof()]
    )

    # Step 5: Parse module info
    modules = _parse_modules(data, section_start, section_hdr, languages, is_v3)

    # Step 6: Parse global symbols
    symbols = _parse_global_symbols(data, section_start, section_hdr, is_v3)

    # Step 7: Parse line numbers
    line_numbers = _parse_line_numbers(data, section_start, modules, is_v3)

    # Step 8: Parse address info
    addr_info = _parse_addr_info(data, section_start, section_hdr)

    return WatcomDebugInfo(
        exe_major_ver=master.exe_major_ver,
        exe_minor_ver=master.exe_minor_ver,
        obj_major_ver=master.obj_major_ver,
        obj_minor_ver=master.obj_minor_ver,
        debug_size=master.debug_size,
        languages=languages,
        segment_table=segment_table,
        modules=modules,
        symbols=symbols,
        addr_info=addr_info,
        line_numbers=line_numbers,
    )


def _module_key(name: str) -> str:
    """Stable module identity across original and staged build paths."""
    base = name.replace("\\", "/").rsplit("/", 1)[-1].lower()
    for suffix in (".cpp", ".asm", ".c", ".obj"):
        if base.endswith(suffix):
            return base[: -len(suffix)]
    return base


def rebuild_watcom_global_symbol_table(
    reference_path: Path, rebuilt_path: Path,
) -> bytes:
    """Replace only the rebuild's global-symbol table with PS's symbols.

    The reconstructed vendor OMF objects reproduce code/data/fixups but do
    not carry the original private Watcom debug-symbol records.  Preserve the
    rebuild's module records and line-number demand data, while serializing
    the authoritative reference symbols against the corresponding rebuilt
    module indices.  Module identity is basename-based because staging paths
    intentionally differ (for example ``D:\\C2\\CODE`` versus ``Z:\\src``).
    """
    reference_info = parse_watcom_debug(reference_path)
    rebuilt_info = parse_watcom_debug(rebuilt_path)

    def module_map(info: WatcomDebugInfo) -> dict[str, int]:
        result: dict[str, int] = {}
        for module in info.modules:
            key = _module_key(module.name)
            if key in result:
                raise ValueError(f"duplicate Watcom debug module key: {key}")
            result[key] = module.index
        return result

    reference_modules = module_map(reference_info)
    rebuilt_modules = module_map(rebuilt_info)
    if reference_modules.keys() != rebuilt_modules.keys():
        only_reference = sorted(
            reference_modules.keys() - rebuilt_modules.keys()
        )
        only_rebuilt = sorted(rebuilt_modules.keys() - reference_modules.keys())
        raise ValueError(
            "Watcom debug module sets differ; "
            f"PS-only={only_reference}, rebuild-only={only_rebuilt}"
        )
    rebuilt_index = {
        reference_modules[key]: rebuilt_modules[key]
        for key in reference_modules
    }

    symbols = bytearray()
    for symbol in reference_info.symbols:
        name = symbol.name.encode("ascii")
        if len(name) > 0xFF:
            raise ValueError(
                f"Watcom debug symbol name is too long: {symbol.name}"
            )
        symbols += struct.pack(
            "<IHHBB", symbol.offset, symbol.segment,
            rebuilt_index[symbol.module_index], symbol.kind, len(name),
        )
        symbols += name

    data = rebuilt_path.read_bytes()
    master_offset = len(data) - MasterDbgHeader.sizeof()
    master = MasterDbgHeader.parse(data[master_offset:])
    debug_start = len(data) - master.debug_size
    section_start = debug_start + master.lang_size + master.segment_size
    section = SectionDbgHeader.parse(
        data[section_start:section_start + SectionDbgHeader.sizeof()]
    )
    old_gbl_start = section_start + section.gbl_offset
    old_addr_start = section_start + section.addr_offset
    old_gbl_size = old_addr_start - old_gbl_start
    delta = len(symbols) - old_gbl_size

    out = bytearray(data[:old_gbl_start])
    out += symbols
    out += data[old_addr_start:]
    struct.pack_into("<I", out, section_start + 8, section.addr_offset + delta)
    struct.pack_into("<I", out, section_start + 12, section.section_size + delta)
    new_master_offset = len(out) - MasterDbgHeader.sizeof()
    struct.pack_into("<I", out, new_master_offset + 10, master.debug_size + delta)
    if len(out) - (master.debug_size + delta) != debug_start:
        raise ValueError("Watcom debug symbol rewrite moved the trailer start")
    return bytes(out)


def _parse_modules(
    data: bytes,
    section_start: int,
    section_hdr: Container,
    languages: list[str],
    is_v3: bool,
) -> list[ModuleInfo]:
    """Parse module info records."""
    modules: list[ModuleInfo] = []
    pos = section_start + section_hdr.mod_offset
    end = section_start + section_hdr.gbl_offset
    index = 0

    while pos < end:
        language_off = Int16ul.parse(data[pos : pos + 2])
        pos += 2

        demands = []
        for _ in range(3):
            info_off = Int32ul.parse(data[pos : pos + 4])
            entries = Int16ul.parse(data[pos + 4 : pos + 6])
            demands.append((info_off, entries))
            pos += 6

        name_len = data[pos]
        pos += 1
        name = data[pos : pos + name_len].decode("ascii", errors="replace")
        pos += name_len

        lang_str = ""
        if language_off < len(languages[0]) + 1 if languages else 0:
            lang_str = languages[0] if languages else "unknown"

        modules.append(
            ModuleInfo(
                index=index,
                name=name,
                language=lang_str,
                locals_entries=demands[0][1],
                locals_offset=demands[0][0],
                types_entries=demands[1][1],
                types_offset=demands[1][0],
                lines_entries=demands[2][1],
                lines_offset=demands[2][0],
            )
        )
        index += 1

    return modules


def _parse_global_symbols(
    data: bytes,
    section_start: int,
    section_hdr: Container,
    is_v3: bool,
) -> list[GlobalSymbol]:
    """Parse global symbol records."""
    symbols: list[GlobalSymbol] = []
    pos = section_start + section_hdr.gbl_offset
    end = section_start + section_hdr.addr_offset

    while pos < end:
        if is_v3:
            offset = Int32ul.parse(data[pos : pos + 4])
            segment = Int16ul.parse(data[pos + 4 : pos + 6])
            mod = Int16ul.parse(data[pos + 6 : pos + 8])
            kind = data[pos + 8]
            name_len = data[pos + 9]
            name = data[pos + 10 : pos + 10 + name_len].decode(
                "ascii", errors="replace"
            )
            pos += 10 + name_len
        else:
            offset = Int32ul.parse(data[pos : pos + 4])
            segment = Int16ul.parse(data[pos + 4 : pos + 6])
            mod = Int16ul.parse(data[pos + 6 : pos + 8])
            name_len = data[pos + 8]
            name = data[pos + 9 : pos + 9 + name_len].decode(
                "ascii", errors="replace"
            )
            kind = 0
            pos += 9 + name_len

        symbols.append(
            GlobalSymbol(
                name=name,
                segment=segment,
                offset=offset,
                module_index=mod,
                kind=kind,
            )
        )

    return symbols


def _parse_line_numbers(
    data: bytes,
    section_start: int,
    modules: list[ModuleInfo],
    is_v3: bool,
) -> dict[int, list[LineSegment]]:
    """Parse line number info for all modules."""
    result: dict[int, list[LineSegment]] = {}

    for mod in modules:
        if mod.lines_entries == 0:
            continue

        line_base = section_start + mod.lines_offset
        num_offsets = mod.lines_entries + 1
        offsets = []
        for i in range(num_offsets):
            off = Int32ul.parse(
                data[line_base + i * 4 : line_base + i * 4 + 4]
            )
            offsets.append(off)

        segments: list[LineSegment] = []
        for i in range(mod.lines_entries):
            block_start = section_start + offsets[i]
            block_end_off = offsets[i + 1] if i + 1 < len(offsets) else None
            coff = 0

            while True:
                pos = block_start + coff
                if is_v3:
                    addr_info_off = Int32ul.parse(data[pos : pos + 4])
                    count = Int16ul.parse(data[pos + 4 : pos + 6])
                    pos += 6
                else:
                    addr_info_off = Int16ul.parse(data[pos : pos + 2])
                    count = Int16ul.parse(data[pos + 2 : pos + 4])
                    pos += 4

                entries = []
                for _ in range(count):
                    line = Int16ul.parse(data[pos : pos + 2])
                    code_off = Int32ul.parse(data[pos + 2 : pos + 6])
                    entries.append(LineEntry(line=line, code_offset=code_off))
                    pos += 6

                segments.append(
                    LineSegment(
                        addr_info_offset=addr_info_off, entries=entries
                    )
                )

                header_size = 6 if is_v3 else 4
                coff += header_size + count * 6

                if block_end_off is not None:
                    if coff >= (offsets[i + 1] - offsets[i]):
                        break
                else:
                    break

        result[mod.index] = segments

    return result


def _parse_addr_info(
    data: bytes,
    section_start: int,
    section_hdr: Container,
) -> list[SegAddrInfo]:
    """Parse the seg_dbg_info address-info blocks."""
    result: list[SegAddrInfo] = []
    pos = section_start + section_hdr.addr_offset
    end = section_start + section_hdr.section_size

    while pos < end:
        if pos + 8 > end:
            break

        base_offset = Int32ul.parse(data[pos : pos + 4])
        base_segment = Int16ul.parse(data[pos + 4 : pos + 6])
        raw_count = Int16ul.parse(data[pos + 6 : pos + 8])
        count = raw_count & 0x7FFF
        pos += 8

        entries: list[AddrEntry] = []
        for _ in range(count):
            if pos + 6 > end:
                break
            size = Int32ul.parse(data[pos : pos + 4])
            mod = Int16ul.parse(data[pos + 4 : pos + 6])
            entries.append(AddrEntry(size=size, mod=mod))
            pos += 6

        result.append(
            SegAddrInfo(
                base_offset=base_offset,
                base_segment=base_segment,
                entries=entries,
            )
        )

    return result


def build_addr_info_base_map(addr_info: list[SegAddrInfo]) -> dict[int, int]:
    """Build a map from addr_info byte-offset to cumulative code base.

    Line number entries use addr_info_offset (a byte offset into the
    addr_info section) to identify which module's code range they belong
    to.  The addr_info section has an 8-byte header per seg_dbg_info
    block, then 6-byte entries.  We build a map from the byte offset of
    each entry to the cumulative code base for that module.
    """
    base_map: dict[int, int] = {}
    for ai in addr_info:
        if ai.base_segment != 1:  # only code segment
            continue
        cumulative = ai.base_offset
        byte_offset = 8  # skip seg_dbg_info header (4+2+2)
        for entry in ai.entries:
            base_map[byte_offset] = cumulative
            cumulative += entry.size
            byte_offset += 6  # each addr_dbg_info is 4+2 bytes
    return base_map

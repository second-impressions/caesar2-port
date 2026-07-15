"""Export command: parse PS.EXE and write symbols.json for Ghidra import.

Binary parsing is delegated to the reccmp fork (``reccmp.formats.lx`` /
``.watcom_debug``); this module owns only the symbols.json shape and the
c2 naming conventions.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Optional

import typer
from reccmp.formats.lx import LXImage
from reccmp.formats.watcom_debug import (
    WatcomDebugInfo,
    WatcomSymbol,
    parse_watcom_debug_file,
)

from c2 import le
from c2.models.export import (
    AddrInfoExport,
    DebugInfoExport,
    EntryPointExport,
    LineEntryExport,
    MemObjectExport,
    MemoryMapExport,
    ModuleExport,
    SourceFileExport,
    StackExport,
    StatsExport,
    SymbolExport,
    SymbolsJsonExport,
)

# GBL_KIND_* flags (wdbginfo.h)
_KIND_STATIC = 0x01
_KIND_DATA = 0x02
_KIND_CODE = 0x04


# ── c2 naming conventions ────────────────────────────────────────────────────
#
# Deliberately NOT reccmp's demangler: reccmp additionally strips a single
# leading underscore from code symbols as ``__cdecl`` (a display heuristic).
# symbols.json is the toolchain's name authority — AIL cdecl exports like
# ``_DLL_read`` must keep their raw spelling, matching the .c sources and
# the delink allowlists.


def _demangle(raw: str, is_code: bool, is_data: bool) -> tuple[str, str | None]:
    """Reverse the Watcom __watcall decoration (TS_CODE_MANGLE ``*_`` /
    TS_DATA_MANGLE ``_*``).  Returns (demangled_name, calling_convention)."""
    if is_code and raw.endswith("_") and len(raw) > 1:
        return raw[:-1], "__watcall"
    if is_data and raw.startswith("_") and len(raw) > 1:
        return raw[1:], None
    return raw, None


def _kind_str(kind: int) -> str:
    parts = []
    if kind & _KIND_STATIC:
        parts.append("static")
    if kind & _KIND_CODE:
        parts.append("code")
    if kind & _KIND_DATA:
        parts.append("data")
    return " ".join(parts) if parts else "unknown"


def _display_name(sym: WatcomSymbol) -> tuple[str, str | None]:
    return _demangle(sym.raw_name, sym.is_code, sym.is_data)


# ── LE object views ──────────────────────────────────────────────────────────


def _obj_type_str(flags: int) -> str:
    if flags & 0x0004:
        return "code"
    if flags & 0x0002:
        return "data"
    return "rodata"


def _obj_flags_str(flags: int) -> str:
    r = "R" if flags & 0x0001 else "-"
    w = "W" if flags & 0x0002 else "-"
    x = "X" if flags & 0x0004 else "-"
    bits = "32bit" if flags & 0x2000 else "16bit"
    return f"{r}{w}{x} {bits}"


# ── Human-readable output ────────────────────────────────────────────────────


def _print_exe_info(img: LXImage) -> None:
    """Print LE executable structure summary."""
    print(f"\n{'=' * 70}")
    print("LE Executable (Caesar II game code)")
    print(f"{'=' * 70}")
    print(f"  MZ stub offset:   0x{le.mz_offset(img):08X}")
    print(f"  LE header offset: 0x{img.le_offset:08X}")
    cpu = "80386" if img.header.cpu_type == 2 else f"type {img.header.cpu_type}"
    print(f"  CPU type:         {cpu}")
    print(f"  Pages:            {img.header.module_number_of_pages} x "
          f"{img.header.page_size} bytes")
    print(f"  Data pages at:    0x{le.data_pages_abs(img):08X} (file offset)")
    print(f"  Entry point:      Object {img.header.eip_object_nb} + "
          f"0x{img.header.eip:X} = 0x{img.entry:X}")
    esp_obj = img.sections[img.header.esp_object_nb - 1]
    print(f"  Stack:            Object {img.header.esp_object_nb} + "
          f"0x{img.header.esp:X} = 0x{esp_obj.virtual_address + img.header.esp:X}")

    print(f"\n  Objects ({len(img.sections)}):")
    print(
        f"  {'#':>3s}  {'Type':>6s}  {'Flags':>12s}  {'Base':>10s}  "
        f"{'VirtSize':>10s}  {'Pages':>5s}  {'FileOff':>10s}  {'FileSize':>10s}"
    )
    for i, section in enumerate(img.sections):
        flags = le.object_raw_flags(img, i)
        print(
            f"  {i + 1:3d}  {_obj_type_str(flags):>6s}  {_obj_flags_str(flags):>12s}  "
            f"0x{section.virtual_address:08X}  {section.virtual_size:>10,}  "
            f"{le.object_num_pages(img, i):>5d}  "
            f"0x{le.object_file_offset(img, i):08X}  {le.object_file_size(img, i):>10,}"
        )


def _print_debug_info(info: WatcomDebugInfo) -> None:
    """Print Watcom debug info summary."""
    print(f"\n{'=' * 70}")
    print("Watcom Debug Info 3.0")
    print(f"{'=' * 70}")
    exe_ver, obj_ver = info.executable_version, info.object_version
    print(f"  Version:     {exe_ver[0]}.{exe_ver[1]} (obj {obj_ver[0]}.{obj_ver[1]})")
    print(f"  Debug size:  {info.debug_size:,} bytes (0x{info.debug_size:X})")
    print(f"  Languages:   {list(info.languages)}")
    print(f"  Segments:    {list(info.segment_selectors)}")

    print(f"\n  Modules ({len(info.modules)}):")
    for mod in info.modules:
        extras = []
        if mod.locals_entries:
            extras.append(f"locals={mod.locals_entries}")
        if mod.types_entries:
            extras.append(f"types={mod.types_entries}")
        lc = sum(1 for e in info.line_numbers if e.module_index == mod.index)
        if lc:
            extras.append(f"lines={lc}")
        extra_str = f"  [{', '.join(extras)}]" if extras else ""
        print(f"    {mod.index:3d}) {mod.name}{extra_str}")

    code_count = sum(1 for s in info.symbols if s.is_code and not s.is_static)
    data_count = sum(1 for s in info.symbols if s.is_data and not s.is_static)
    static_code = sum(1 for s in info.symbols if s.is_code and s.is_static)
    static_data = sum(1 for s in info.symbols if s.is_data and s.is_static)
    print(f"\n  Global symbols: {len(info.symbols)}")
    print(f"    Code: {code_count}, Data: {data_count}")
    print(f"    Static code: {static_code}, Static data: {static_data}")

    mods_with_lines = len({e.module_index for e in info.line_numbers})
    print(f"\n  Line numbers: {len(info.line_numbers)} entries "
          f"across {mods_with_lines} files")

    print(f"\n  Address info: {len(info.addr_info or [])} blocks")
    for ai in info.addr_info or []:
        print(
            f"    seg {ai.base_segment}: base=0x{ai.base_offset:X}, "
            f"{len(ai.entry_sizes)} modules, "
            f"total=0x{sum(ai.entry_sizes):X} bytes"
        )


def _print_symbols(info: WatcomDebugInfo, img: LXImage) -> None:
    """Print all symbols with resolved addresses."""
    print(f"\n{'=' * 70}")
    print("Global Symbols")
    print(f"{'=' * 70}")

    for sym in info.symbols:
        base = (img.sections[sym.segment - 1].virtual_address
                if sym.segment <= len(img.sections) else 0)
        name, conv = _display_name(sym)
        conv_str = f"  [{conv}]" if conv else ""
        print(f"  0x{base + sym.offset:08X}  {_kind_str(sym.kind):>12s}  "
              f"{name}{conv_str}")


# ── Builder ───────────────────────────────────────────────────────────────


class _FileRange:
    """Accumulator for source file address ranges (internal use only)."""

    __slots__ = ("min_address", "max_address", "line_count", "sym_count", "source")

    def __init__(self, address: int, source: str = "lines") -> None:
        self.min_address = address
        self.max_address = address
        self.line_count = 0
        self.sym_count = 0
        self.source = source

    def update(self, address: int) -> None:
        self.min_address = min(self.min_address, address)
        self.max_address = max(self.max_address, address)


def build_export(info: WatcomDebugInfo, img: LXImage) -> SymbolsJsonExport:
    """Build the unified JSON export."""
    # ── Memory map ───────────────────────────────────────────────────────
    objects_out: list[MemObjectExport] = []
    for i, section in enumerate(img.sections):
        flags = le.object_raw_flags(img, i)
        file_offset = le.object_file_offset(img, i)
        objects_out.append(MemObjectExport(
            index=i + 1,
            type=_obj_type_str(flags),
            base_address=f"0x{section.virtual_address:X}",
            base_address_int=section.virtual_address,
            virtual_size=section.virtual_size,
            virtual_size_hex=f"0x{section.virtual_size:X}",
            file_size=le.object_file_size(img, i),
            file_offset=f"0x{file_offset:X}",
            file_offset_int=file_offset,
            num_pages=le.object_num_pages(img, i),
            flags=f"0x{flags:X}",
            flags_str=_obj_flags_str(flags),
        ))

    memory_map = MemoryMapExport(
        format="le_flat_binary",
        architecture="x86:LE:32:default",
        le_mz_offset=f"0x{le.mz_offset(img):X}",
        le_header_offset=f"0x{img.le_offset:X}",
        objects=objects_out,
    )

    hdr = img.header
    if hdr.eip_object_nb <= len(img.sections):
        entry_addr = img.sections[hdr.eip_object_nb - 1].virtual_address + hdr.eip
        memory_map.entry_point = EntryPointExport(
            object=hdr.eip_object_nb,
            offset=f"0x{hdr.eip:X}",
            offset_int=hdr.eip,
            address=f"0x{entry_addr:X}",
            address_int=entry_addr,
        )

    if hdr.esp_object_nb <= len(img.sections):
        stack_addr = img.sections[hdr.esp_object_nb - 1].virtual_address + hdr.esp
        memory_map.stack = StackExport(
            object=hdr.esp_object_nb,
            offset=f"0x{hdr.esp:X}",
            address=f"0x{stack_addr:X}",
        )

    # ── Segment maps ─────────────────────────────────────────────────────
    seg_base: dict[int, int] = {}
    seg_vsize: dict[int, int] = {}
    for i, section in enumerate(img.sections):
        seg_base[i + 1] = section.virtual_address
        seg_vsize[i + 1] = section.virtual_size

    # ── Symbols ──────────────────────────────────────────────────────────
    symbols_out: list[SymbolExport] = []
    resolved_count = 0
    beyond_count = 0

    for sym in info.symbols:
        name, conv = _display_name(sym)
        entry = SymbolExport(
            name=name,
            raw_name=sym.raw_name,
            segment=sym.segment,
            offset=sym.offset,
            offset_hex=f"0x{sym.offset:08X}",
            module_index=sym.module_index,
            kind=_kind_str(sym.kind),
            is_code=sym.is_code,
            is_data=sym.is_data,
            is_static=sym.is_static,
            calling_convention=conv,
        )

        if sym.segment in seg_base:
            ghidra_addr = seg_base[sym.segment] + sym.offset
            entry.address = ghidra_addr
            entry.address_hex = f"0x{ghidra_addr:08X}"
            entry.le_object = sym.segment
            resolved_count += 1

            if sym.offset >= seg_vsize.get(sym.segment, 0):
                entry.beyond_vsize = True
                beyond_count += 1

        symbols_out.append(entry)

    # ── Line numbers ─────────────────────────────────────────────────────
    code_base = seg_base.get(1, 0)
    mod_short_names = {
        m.index: (m.name.rsplit("\\", 1)[1] if "\\" in m.name else m.name)
        for m in info.modules
    }

    lines_out: list[LineEntryExport] = []
    for lentry in info.line_numbers:
        lines_out.append(LineEntryExport(
            line=lentry.line,
            file=mod_short_names[lentry.module_index],
            module_index=lentry.module_index,
            offset=lentry.code_offset,
            address=code_base + lentry.code_offset,
            address_hex=f"0x{code_base + lentry.code_offset:08X}",
        ))

    lines_out.sort(key=lambda e: e.address)

    # ── Source files ──────────────────────────────────────────────────────
    file_ranges: dict[int, _FileRange] = {}
    for ln in lines_out:
        mi = ln.module_index
        if mi not in file_ranges:
            file_ranges[mi] = _FileRange(ln.address)
        r = file_ranges[mi]
        r.update(ln.address)
        r.line_count += 1

    line_modules = set(file_ranges.keys())
    for sym in info.symbols:
        if not sym.is_code:
            continue
        mi = sym.module_index
        if mi is None or mi in line_modules:
            continue
        if sym.segment not in seg_base:
            continue
        addr = seg_base[sym.segment] + sym.offset
        if mi not in file_ranges:
            file_ranges[mi] = _FileRange(addr, source="symbols")
        r = file_ranges[mi]
        r.update(addr)
        r.sym_count += 1

    source_files_out: list[SourceFileExport] = []
    for mi, r in sorted(file_ranges.items(), key=lambda x: x[1].min_address):
        mod = info.modules[mi]
        mod_name = mod.name
        short_name = mod_name.rsplit("\\", 1)[1] if "\\" in mod_name else mod_name
        source_files_out.append(SourceFileExport(
            file=short_name,
            full_path=mod_name,
            module_index=mi,
            language=mod.language,
            min_address=r.min_address,
            min_address_hex=f"0x{r.min_address:08X}",
            max_address=r.max_address,
            max_address_hex=f"0x{r.max_address:08X}",
            line_count=r.line_count,
            sym_count=r.sym_count,
            source=r.source,
        ))

    # ── Modules ──────────────────────────────────────────────────────────
    modules_out: list[ModuleExport] = []
    for mod in info.modules:
        modules_out.append(ModuleExport(
            index=mod.index,
            name=mod.name,
            language=mod.language,
            has_locals=mod.locals_entries > 0,
            has_types=mod.types_entries > 0,
            has_lines=mod.lines_entries > 0,
        ))

    # ── Address info ─────────────────────────────────────────────────────
    addr_info_out: list[AddrInfoExport] = []
    for ai in info.addr_info or []:
        addr_info_out.append(AddrInfoExport(
            base_segment=ai.base_segment,
            base_offset=ai.base_offset,
            base_offset_hex=f"0x{ai.base_offset:08X}",
            module_count=len(ai.entry_sizes),
            total_declared_bytes=sum(ai.entry_sizes),
        ))

    return SymbolsJsonExport(
        memory_map=memory_map,
        debug_info=DebugInfoExport(
            format="watcom_debug_v3",
            version=f"{info.executable_version[0]}.{info.executable_version[1]}",
            debug_size=info.debug_size,
            languages=list(info.languages),
            segment_table=list(info.segment_selectors),
            addr_info=addr_info_out,
        ),
        modules=modules_out,
        source_files=source_files_out,
        symbols=symbols_out,
        line_numbers=lines_out,
        stats=StatsExport(
            total_symbols=len(info.symbols),
            code_symbols=sum(1 for s in info.symbols if s.is_code),
            data_symbols=sum(1 for s in info.symbols if s.is_data),
            static_symbols=sum(1 for s in info.symbols if s.is_static),
            resolved_symbols=resolved_count,
            beyond_vsize=beyond_count,
            total_modules=len(info.modules),
            total_source_files=len(source_files_out),
            total_line_entries=len(lines_out),
        ),
    )


def _extract_le_objects(img: LXImage, output_dir: Path) -> None:
    """Extract LE object data as flat binary files (BSS zero-padded)."""
    output_dir.mkdir(parents=True, exist_ok=True)
    for i, section in enumerate(img.sections):
        flags = le.object_raw_flags(img, i)
        if _obj_type_str(flags) == "code":
            bin_name = "le_code.bin"
        elif i + 1 == 2:
            bin_name = "le_data.bin"
        else:
            bin_name = f"le_obj{i + 1}.bin"
        data = bytes(section.view)
        if section.virtual_size > len(data):
            data += b"\x00" * (section.virtual_size - len(data))
        (output_dir / bin_name).write_bytes(data)


# ── Typer command ─────────────────────────────────────────────────────────


def export(
    input: Annotated[Path, typer.Argument(help="Path to PS.EXE")],
    output: Annotated[
        Optional[Path],
        typer.Option("--output", "-o", help="Output JSON file (default: data/out/symbols.json)"),
    ] = None,
    no_extract: Annotated[
        bool,
        typer.Option("--no-extract", help="Skip extracting le_code.bin / le_data.bin"),
    ] = False,
    symbols: Annotated[
        bool,
        typer.Option("--symbols", help="Print full symbol listing"),
    ] = False,
) -> None:
    """Parse PS.EXE: extract LE objects, parse Watcom debug info, write symbols.json."""
    from c2.original import ensure_original

    ensure_original(input)

    # Default output: data/out/symbols.json next to the input file
    output_dir = input.parent
    output_path = output or (output_dir / "out" / "symbols.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Parse executable structure
    typer.echo(f"Input: {input} ({input.stat().st_size:,} bytes)")
    img = le.load_le(input)
    _print_exe_info(img)

    # Extract LE objects
    if not no_extract:
        _extract_le_objects(img, output_path.parent)
        for i, section in enumerate(img.sections):
            flags = le.object_raw_flags(img, i)
            name = "le_code.bin" if _obj_type_str(flags) == "code" else "le_data.bin"
            typer.echo(f"\n  Extracted {name}: {section.virtual_size:,} bytes")

    # Parse Watcom debug info
    info = parse_watcom_debug_file(input)
    _print_debug_info(info)

    if symbols:
        _print_symbols(info, img)

    # Export unified JSON
    result = build_export(info, img)
    output_path.write_text(result.model_dump_json(indent=2, exclude_none=True))

    stats = result.stats
    typer.echo(f"\n{'=' * 70}")
    typer.echo(f"Wrote {output_path}")
    typer.echo(f"{'=' * 70}")
    typer.echo(f"  {stats.total_symbols} symbols ({stats.resolved_symbols} resolved)")
    typer.echo(f"  {stats.total_line_entries} line number entries")
    typer.echo(f"  {stats.total_modules} modules")
    if stats.beyond_vsize:
        typer.echo(f"  WARNING: {stats.beyond_vsize} symbols beyond virtual size")

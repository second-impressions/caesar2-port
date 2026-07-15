"""Export command: parse PS.EXE and write symbols.json for Ghidra import."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Optional

import typer

from c2.parsers.debug import WatcomDebugInfo, build_addr_info_base_map, parse_watcom_debug
from c2.parsers.exe import LEHeader, extract_le_objects, parse_exe
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


# ── Human-readable output ────────────────────────────────────────────────────


def _print_exe_info(le: LEHeader) -> None:
    """Print LE executable structure summary."""
    print(f"\n{'=' * 70}")
    print("LE Executable (Caesar II game code)")
    print(f"{'=' * 70}")
    print(f"  MZ stub offset:   0x{le.mz_offset:08X}")
    print(f"  LE header offset: 0x{le.le_offset:08X}")
    cpu = "80386" if le.cpu_type == 2 else f"type {le.cpu_type}"
    print(f"  CPU type:         {cpu}")
    print(f"  Pages:            {le.num_pages} x {le.page_size} bytes")
    print(f"  Data pages at:    0x{le.data_pages_abs:08X} (file offset)")

    if le.entry_address is not None:
        print(
            f"  Entry point:      Object {le.eip_object} + "
            f"0x{le.eip:X} = 0x{le.entry_address:X}"
        )
    if le.stack_address is not None:
        print(
            f"  Stack:            Object {le.esp_object} + "
            f"0x{le.esp:X} = 0x{le.stack_address:X}"
        )

    print(f"\n  Objects ({le.num_objects}):")
    print(
        f"  {'#':>3s}  {'Type':>6s}  {'Flags':>12s}  {'Base':>10s}  "
        f"{'VirtSize':>10s}  {'Pages':>5s}  {'FileOff':>10s}  {'FileSize':>10s}"
    )
    print(
        f"  {'---':>3s}  {'------':>6s}  {'------------':>12s}  {'----------':>10s}  "
        f"{'----------':>10s}  {'-----':>5s}  {'----------':>10s}  {'----------':>10s}"
    )
    for obj in le.objects:
        file_off = le.object_file_offset(obj)
        file_sz = le.object_file_size(obj)
        print(
            f"  {obj.index:3d}  {obj.type_str:>6s}  {obj.flags_str:>12s}  "
            f"0x{obj.reloc_base_addr:08X}  {obj.virtual_size:>10,}  "
            f"{obj.num_pages:>5d}  0x{file_off:08X}  {file_sz:>10,}"
        )


def _print_debug_info(info: WatcomDebugInfo) -> None:
    """Print Watcom debug info summary."""
    print(f"\n{'=' * 70}")
    print("Watcom Debug Info 3.0")
    print(f"{'=' * 70}")
    print(
        f"  Version:     {info.exe_major_ver}.{info.exe_minor_ver} "
        f"(obj {info.obj_major_ver}.{info.obj_minor_ver})"
    )
    print(f"  Debug size:  {info.debug_size:,} bytes (0x{info.debug_size:X})")
    print(f"  Languages:   {info.languages}")
    print(f"  Segments:    {info.segment_table}")

    line_counts: dict[int, int] = {}
    for mod_idx, segments in info.line_numbers.items():
        line_counts[mod_idx] = sum(len(seg.entries) for seg in segments)
    modules_with_lines = [m for m in info.modules if line_counts.get(m.index, 0) > 0]

    print(f"\n  Modules ({len(info.modules)}):")
    for mod in info.modules:
        extras = []
        if mod.locals_entries:
            extras.append(f"locals={mod.locals_entries}")
        if mod.types_entries:
            extras.append(f"types={mod.types_entries}")
        lc = line_counts.get(mod.index, 0)
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

    total_lines = sum(
        sum(len(seg.entries) for seg in segs)
        for segs in info.line_numbers.values()
    )
    print(f"\n  Line numbers: {total_lines} entries across {len(modules_with_lines)} files")

    print(f"\n  Address info: {len(info.addr_info)} blocks")
    for ai in info.addr_info:
        total_bytes = sum(e.size for e in ai.entries)
        print(
            f"    seg {ai.base_segment}: base=0x{ai.base_offset:X}, "
            f"{len(ai.entries)} modules, "
            f"total=0x{total_bytes:X} bytes"
        )


def _print_symbols(info: WatcomDebugInfo, le: LEHeader) -> None:
    """Print all symbols with resolved addresses."""
    print(f"\n{'=' * 70}")
    print("Global Symbols")
    print(f"{'=' * 70}")

    seg_base = {obj.index: obj.reloc_base_addr for obj in le.objects}

    for sym in info.symbols:
        base = seg_base.get(sym.segment, 0)
        addr = base + sym.offset
        kind_parts = []
        if sym.is_static:
            kind_parts.append("static")
        if sym.is_code:
            kind_parts.append("code")
        if sym.is_data:
            kind_parts.append("data")
        kind_str = " ".join(kind_parts)
        conv = f"  [{sym.calling_convention}]" if sym.calling_convention else ""
        print(f"  0x{addr:08X}  {kind_str:>12s}  {sym.demangled_name}{conv}")


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


def build_export(info: WatcomDebugInfo, le: LEHeader) -> SymbolsJsonExport:
    """Build the unified JSON export."""
    # ── Memory map ───────────────────────────────────────────────────────
    objects_out: list[MemObjectExport] = []
    for obj in le.objects:
        file_offset = le.object_file_offset(obj)
        file_size = le.object_file_size(obj)
        objects_out.append(MemObjectExport(
            index=obj.index,
            type=obj.type_str,
            base_address=f"0x{obj.reloc_base_addr:X}",
            base_address_int=obj.reloc_base_addr,
            virtual_size=obj.virtual_size,
            virtual_size_hex=f"0x{obj.virtual_size:X}",
            file_size=file_size,
            file_offset=f"0x{file_offset:X}",
            file_offset_int=file_offset,
            num_pages=obj.num_pages,
            flags=f"0x{obj.flags:X}",
            flags_str=obj.flags_str,
        ))

    memory_map = MemoryMapExport(
        format="le_flat_binary",
        architecture="x86:LE:32:default",
        le_mz_offset=f"0x{le.mz_offset:X}",
        le_header_offset=f"0x{le.le_offset:X}",
        objects=objects_out,
    )

    if le.eip_object <= len(le.objects):
        eip_obj = le.objects[le.eip_object - 1]
        entry_addr = eip_obj.reloc_base_addr + le.eip
        memory_map.entry_point = EntryPointExport(
            object=le.eip_object,
            offset=f"0x{le.eip:X}",
            offset_int=le.eip,
            address=f"0x{entry_addr:X}",
            address_int=entry_addr,
        )

    if le.esp_object <= len(le.objects):
        esp_obj = le.objects[le.esp_object - 1]
        stack_addr = esp_obj.reloc_base_addr + le.esp
        memory_map.stack = StackExport(
            object=le.esp_object,
            offset=f"0x{le.esp:X}",
            address=f"0x{stack_addr:X}",
        )

    # ── Segment maps ─────────────────────────────────────────────────────
    seg_base: dict[int, int] = {}
    seg_vsize: dict[int, int] = {}
    for obj in le.objects:
        seg_base[obj.index] = obj.reloc_base_addr
        seg_vsize[obj.index] = obj.virtual_size

    # ── Symbols ──────────────────────────────────────────────────────────
    symbols_out: list[SymbolExport] = []
    resolved_count = 0
    beyond_count = 0

    for sym in info.symbols:
        entry = SymbolExport(
            name=sym.demangled_name,
            raw_name=sym.name,
            segment=sym.segment,
            offset=sym.offset,
            offset_hex=f"0x{sym.offset:08X}",
            module_index=sym.module_index,
            kind=sym.kind_str,
            is_code=sym.is_code,
            is_data=sym.is_data,
            is_static=sym.is_static,
            calling_convention=sym.calling_convention,
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
    addr_info_base_map = build_addr_info_base_map(info.addr_info)
    code_base = seg_base.get(1, 0)

    lines_out: list[LineEntryExport] = []
    for mod_idx, segments in info.line_numbers.items():
        mod = info.modules[mod_idx]
        mod_name = mod.name
        if "\\" in mod_name:
            mod_name = mod_name.rsplit("\\", 1)[1]

        for seg in segments:
            module_base = addr_info_base_map.get(seg.addr_info_offset, 0)
            for lentry in seg.entries:
                flat_offset = module_base + lentry.code_offset
                ghidra_addr = code_base + flat_offset
                lines_out.append(LineEntryExport(
                    line=lentry.line,
                    file=mod_name,
                    module_index=mod_idx,
                    offset=flat_offset,
                    address=ghidra_addr,
                    address_hex=f"0x{ghidra_addr:08X}",
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
    for ai in info.addr_info:
        addr_info_out.append(AddrInfoExport(
            base_segment=ai.base_segment,
            base_offset=ai.base_offset,
            base_offset_hex=f"0x{ai.base_offset:08X}",
            module_count=len(ai.entries),
            total_declared_bytes=sum(e.size for e in ai.entries),
        ))

    return SymbolsJsonExport(
        memory_map=memory_map,
        debug_info=DebugInfoExport(
            format="watcom_debug_v3",
            version=f"{info.exe_major_ver}.{info.exe_minor_ver}",
            debug_size=info.debug_size,
            languages=info.languages,
            segment_table=info.segment_table,
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
    if not input.exists():
        typer.echo(f"Error: {input} not found", err=True)
        raise typer.Exit(1)

    # Default output: data/out/symbols.json next to the input file
    output_dir = input.parent
    output_path = output or (output_dir / "out" / "symbols.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Parse executable structure
    typer.echo(f"Input: {input} ({input.stat().st_size:,} bytes)")
    _mz, _bw_headers, le = parse_exe(input)
    _print_exe_info(le)

    # Extract LE objects
    if not no_extract:
        extract_le_objects(input, le, output_path.parent)
        for obj in le.objects:
            name = "le_code.bin" if obj.type_str == "code" else "le_data.bin"
            typer.echo(f"\n  Extracted {name}: {obj.virtual_size:,} bytes")

    # Parse Watcom debug info
    info = parse_watcom_debug(input)
    _print_debug_info(info)

    if symbols:
        _print_symbols(info, le)

    # Export unified JSON
    result = build_export(info, le)
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

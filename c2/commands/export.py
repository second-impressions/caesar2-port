"""symbols.json generation (build metadata derived from the original).

Binary parsing is delegated to the reccmp fork (``reccmp.formats.lx`` /
``.watcom_debug``); this module owns the symbols.json contract consumed
by ``c2 rebuild`` and ``c2 delink``, and the c2 naming conventions.

Not a CLI command: :func:`ensure_symbols_json` runs automatically inside
``rebuild``/``delink``, regenerating ``.c2-cache/symbols.json`` whenever
it is missing or older than the original executable.
"""

from __future__ import annotations

from pathlib import Path

import typer
from reccmp.formats.lx import LXImage
from reccmp.formats.watcom_debug import (
    WatcomDebugInfo,
    parse_watcom_debug_file,
)

from c2 import le
from c2.original import ensure_original
from c2.models.export import (
    MemObjectExport,
    MemoryMapExport,
    ModuleExport,
    SymbolExport,
    SymbolsJsonExport,
)

# ── c2 naming conventions ────────────────────────────────────────────────────
#
# Deliberately NOT reccmp's demangler: reccmp additionally strips a single
# leading underscore from code symbols as ``__cdecl`` (a display heuristic).
# symbols.json is the toolchain's name authority — AIL cdecl exports like
# ``_DLL_read`` must keep their raw spelling, matching the .c sources and
# the delink allowlists.


def _demangle(raw: str, is_code: bool, is_data: bool) -> str:
    """Reverse the Watcom __watcall decoration (TS_CODE_MANGLE ``*_`` /
    TS_DATA_MANGLE ``_*``)."""
    if is_code and raw.endswith("_") and len(raw) > 1:
        return raw[:-1]
    if is_data and raw.startswith("_") and len(raw) > 1:
        return raw[1:]
    return raw


def _obj_type_str(flags: int) -> str:
    if flags & 0x0004:
        return "code"
    if flags & 0x0002:
        return "data"
    return "rodata"


def build_export(info: WatcomDebugInfo, img: LXImage) -> SymbolsJsonExport:
    """Build the symbols.json export."""
    objects_out = [
        MemObjectExport(
            index=i + 1,
            type=_obj_type_str(le.object_raw_flags(img, i)),
            base_address_int=section.virtual_address,
            virtual_size=section.virtual_size,
            file_size=le.object_file_size(img, i),
            file_offset_int=le.object_file_offset(img, i),
            num_pages=le.object_num_pages(img, i),
        )
        for i, section in enumerate(img.sections)
    ]

    modules_out = [
        ModuleExport(index=m.index, name=m.name, language=m.language)
        for m in info.modules
    ]

    symbols_out = [
        SymbolExport(
            name=_demangle(s.raw_name, s.is_code, s.is_data),
            raw_name=s.raw_name,
            segment=s.segment,
            offset=s.offset,
            module_index=s.module_index,
            is_code=s.is_code,
            is_data=s.is_data,
            is_static=s.is_static,
        )
        for s in info.symbols
    ]

    return SymbolsJsonExport(
        memory_map=MemoryMapExport(objects=objects_out),
        modules=modules_out,
        symbols=symbols_out,
    )


def ensure_symbols_json(
    exe_path: Path,
    output_path: Path = Path(".c2-cache/symbols.json"),
) -> Path:
    """Regenerate symbols.json from *exe_path* when missing or stale.

    Staleness is mtime-based (the original never changes in practice —
    its hash is pinned — so this only ever fires on a fresh checkout or
    a deleted cache)."""
    if (output_path.exists()
            and output_path.stat().st_mtime >= exe_path.stat().st_mtime):
        return output_path

    ensure_original(exe_path)
    img = le.load_le(exe_path)
    info = parse_watcom_debug_file(exe_path)
    result = build_export(info, img)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(result.model_dump_json(indent=2))
    typer.echo(
        f"  symbols.json regenerated from {exe_path} "
        f"({len(info.symbols)} symbols, {len(info.modules)} modules)")
    return output_path

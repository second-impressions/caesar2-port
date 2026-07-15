"""Watcom Debug Info 3.0 *writer* helpers.

Parsing lives in the reccmp fork (``reccmp.formats.watcom_debug``); this
module owns the one write-side operation the rebuild needs: grafting
PS's authoritative global-symbol table into the freshly linked image's
debug trailer.
"""

from __future__ import annotations

import struct
from pathlib import Path

from reccmp.formats.watcom_debug import parse_watcom_debug_file

# Trailer layout (wdbginfo.h): master header = <H4BHHI (14 bytes):
#   signature, exe_major, exe_minor, obj_major, obj_minor,
#   lang_size, segment_size, debug_size
# section header = <4IH (18 bytes):
#   mod_offset, gbl_offset, addr_offset, section_size, section_id
_MASTER_FMT = "<H4BHHI"
_MASTER_SIZE = struct.calcsize(_MASTER_FMT)
_SECTION_FMT = "<4IH"
_SECTION_SIZE = struct.calcsize(_SECTION_FMT)


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
    reference_info = parse_watcom_debug_file(reference_path)
    rebuilt_info = parse_watcom_debug_file(rebuilt_path)

    def module_map(info) -> dict[str, int]:
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
        name = symbol.raw_name.encode("ascii")
        if len(name) > 0xFF:
            raise ValueError(
                f"Watcom debug symbol name is too long: {symbol.raw_name}"
            )
        symbols += struct.pack(
            "<IHHBB", symbol.offset, symbol.segment,
            rebuilt_index[symbol.module_index], symbol.kind, len(name),
        )
        symbols += name

    data = rebuilt_path.read_bytes()
    master_offset = len(data) - _MASTER_SIZE
    (_sig, _exe_maj, _exe_min, _obj_maj, _obj_min,
     lang_size, segment_size, debug_size) = struct.unpack_from(
        _MASTER_FMT, data, master_offset)
    debug_start = len(data) - debug_size
    section_start = debug_start + lang_size + segment_size
    (_mod_off, gbl_offset, addr_offset, section_size, _sect_id) = (
        struct.unpack_from(_SECTION_FMT, data, section_start))
    old_gbl_start = section_start + gbl_offset
    old_addr_start = section_start + addr_offset
    old_gbl_size = old_addr_start - old_gbl_start
    delta = len(symbols) - old_gbl_size

    out = bytearray(data[:old_gbl_start])
    out += symbols
    out += data[old_addr_start:]
    struct.pack_into("<I", out, section_start + 8, addr_offset + delta)
    struct.pack_into("<I", out, section_start + 12, section_size + delta)
    new_master_offset = len(out) - _MASTER_SIZE
    struct.pack_into("<I", out, new_master_offset + 10, debug_size + delta)
    if len(out) - (debug_size + delta) != debug_start:
        raise ValueError("Watcom debug symbol rewrite moved the trailer start")
    return bytes(out)

"""Pydantic models for the symbols.json build-metadata export.

symbols.json is the machine-readable contract between ``c2 export`` and
the build toolchain (``c2 rebuild`` / ``c2 delink``): the LE memory map
plus the Watcom debug-info module and symbol tables.  It deliberately
contains ONLY what those consumers read — the Ghidra-import era's
line-number/source-file/debug-metadata sections are gone with the
Ghidra tooling.
"""

from __future__ import annotations

from pydantic import BaseModel


class MemObjectExport(BaseModel):
    index: int                      # 1-based LE object number
    type: str                       # "code" / "data" / "rodata"
    base_address_int: int           # reloc base virtual address
    virtual_size: int
    file_size: int
    file_offset_int: int
    num_pages: int


class MemoryMapExport(BaseModel):
    objects: list[MemObjectExport]


class ModuleExport(BaseModel):
    index: int
    name: str                       # full compiler-recorded source path
    language: str


class SymbolExport(BaseModel):
    name: str                       # demangled (c2 naming rules)
    raw_name: str                   # as stored in the debug info
    segment: int                    # 1-based LE object number
    offset: int                     # byte offset within the object
    module_index: int
    is_code: bool
    is_data: bool
    is_static: bool


class SymbolsJsonExport(BaseModel):
    memory_map: MemoryMapExport
    modules: list[ModuleExport]
    symbols: list[SymbolExport]

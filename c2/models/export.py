"""Pydantic models for the unified symbols.json export.

These mirror the static inner classes in ImportCaesar2.java.
Field names use snake_case (matching both Python convention and Gson).
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class MemObjectExport(BaseModel):
    """An LE object (code/data segment)."""

    index: int
    type: str
    base_address: str
    base_address_int: int
    virtual_size: int
    virtual_size_hex: str
    file_size: int
    file_offset: str
    file_offset_int: int
    num_pages: int
    flags: str
    flags_str: str


class EntryPointExport(BaseModel):
    """LE entry point info."""

    object: int
    offset: str
    offset_int: int
    address: str
    address_int: int


class StackExport(BaseModel):
    """LE stack info."""

    object: int
    offset: str
    address: str


class MemoryMapExport(BaseModel):
    """Top-level memory map section."""

    format: str
    architecture: str
    le_mz_offset: str
    le_header_offset: str
    objects: list[MemObjectExport]
    entry_point: Optional[EntryPointExport] = None
    stack: Optional[StackExport] = None


class SymbolExport(BaseModel):
    """A resolved global symbol."""

    name: str
    raw_name: str
    segment: int
    offset: int
    offset_hex: str
    module_index: Optional[int]
    kind: str
    is_code: bool
    is_data: bool
    is_static: bool
    calling_convention: Optional[str] = None
    address: Optional[int] = None
    address_hex: Optional[str] = None
    le_object: Optional[int] = None
    beyond_vsize: Optional[bool] = None


class LineEntryExport(BaseModel):
    """A source line → code address mapping."""

    line: int
    file: str
    module_index: int
    offset: int
    address: int
    address_hex: str


class SourceFileExport(BaseModel):
    """Address range for a source file (for Program Tree)."""

    file: str
    full_path: str
    module_index: int
    language: str
    min_address: int
    min_address_hex: str
    max_address: int
    max_address_hex: str
    line_count: int
    sym_count: int
    source: str  # "lines" or "symbols"


class ModuleExport(BaseModel):
    """A source module (compilation unit)."""

    index: int
    name: str
    language: str
    has_locals: bool
    has_types: bool
    has_lines: bool


class AddrInfoExport(BaseModel):
    """Address info block summary."""

    base_segment: int
    base_offset: int
    base_offset_hex: str
    module_count: int
    total_declared_bytes: int


class DebugInfoExport(BaseModel):
    """Debug info metadata."""

    format: str
    version: str
    debug_size: int
    languages: list[str]
    segment_table: list[int]
    addr_info: list[AddrInfoExport]


class StatsExport(BaseModel):
    """Export statistics."""

    total_symbols: int
    code_symbols: int
    data_symbols: int
    static_symbols: int
    resolved_symbols: int
    beyond_vsize: int
    total_modules: int
    total_source_files: int
    total_line_entries: int


class SymbolsJsonExport(BaseModel):
    """Root export structure — serialized to symbols.json."""

    memory_map: MemoryMapExport
    debug_info: DebugInfoExport
    modules: list[ModuleExport]
    source_files: list[SourceFileExport]
    symbols: list[SymbolExport]
    line_numbers: list[LineEntryExport]
    stats: StatsExport

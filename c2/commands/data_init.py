from __future__ import annotations

import json
import re
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import typer
from pycparser import c_ast, c_generator

from c2.commands.c_source import parse_c


_SYMBOLS = Path("data/out/symbols.json")
_EXE = Path("data/PS.EXE")
_SEARCH_GLOBS = ["decomp/include/*.h", "decomp/src/*.c"]
_DECL_INDEX_CACHE: dict | None = None
_HEADER_GLOB = ["decomp/include/*.h"]

_CODE_BASE = 0x10000
_DATA_BASE = 0x90000

# Per-symbol explanatory comments emitted above the matching initializer
# in datainit.c.  Use sparingly — only for symbols whose raw byte
# layout is opaque without an accompanying explanation (e.g.  binary
# file-format header magic stored as int[]).
_SYMBOL_COMMENTS: dict[str, str] = {
    "LBM_HEADER1": (
        "IFF / Deluxe Paint LBM file header written to disk by\n"
        "   write_lbm() before the pixel data.  Bytes spell:\n"
        "     'FORM' <size:BE> 'PBM ' 'BMHD' <14:BE>\n"
        "     <width=640> <height=480> <0> <0> <8bpp> <0> <0>\n"
        "     <0xff:transp> <1:compress> <1:pad>\n"
        "     <width=640> <height=480>\n"
        "     'CMAP' <0x300:BE>  (24-bit, 256-entry palette follows)\n"
        "   Declared int[] so the loader can `memcpy` 48 bytes in one\n"
        "   shot; the values are pure binary, not numeric."
    ),
    "LBM_HEADER2": (
        "IFF / Deluxe Paint LBM body chunk header: 'BODY' <size:BE>.\n"
        "   Written between the CMAP palette and the raw 640x480 pixel\n"
        "   data.  Same int[] storage rationale as LBM_HEADER1."
    ),
}


@dataclass(frozen=True)
class DataSym:
    name: str
    offset: int
    address: int
    size: int
    file_bytes: int
    file_backed: bool
    module: str = ""


def _is_library_module(mod_name: str) -> bool:
    """True for Watcom CRT / linked-library (AIL) modules whose initialized
    data we do NOT reproduce in the game's datainit.c.

    Game modules are ``D:\\C2\\CODE\\*`` C sources or the local ``*.asm``
    sources; everything else is library code (bare CRT module names like
    ``cstrt386``, or ``R:\\NET\\LIBS\\AIL\\*`` paths).  An unknown/empty
    module name is treated as game (never skipped) to stay conservative.

    This is what keeps the CRT ``__nullarea`` placeholder (data offset 0)
    from being emitted: its gap-to-next-symbol size swallows the program's
    unnamed string-literal pool, but those strings are reproduced by the
    functions' own string literals, not by a datainit.c blob.
    """
    if not mod_name:
        return False
    u = mod_name.upper()
    if u.startswith("D:\\C2\\CODE\\"):
        return False
    if u.endswith(".ASM"):
        return False
    return True


@dataclass(frozen=True)
class CTypeShape:
    base: str
    dims: tuple[int | None, ...]
    decl_text: str
    source: Path


def _load_symbols() -> tuple[list[DataSym], int, int]:
    sym = json.loads(_SYMBOLS.read_text())
    data_obj = sym["memory_map"]["objects"][1]
    file_size = int(data_obj["file_size"])
    file_off = int(data_obj["file_offset_int"])
    modules = sym.get("modules") or []

    def _mod_name(s: dict) -> str:
        mi = s.get("module_index")
        if isinstance(mi, int) and 0 <= mi < len(modules):
            return modules[mi].get("name", "") or ""
        return ""

    raw_syms = sorted(
        [s for s in sym["symbols"] if s.get("segment") == 2 and s.get("is_data")],
        key=lambda s: s["offset"],
    )
    out: list[DataSym] = []
    for i, s in enumerate(raw_syms):
        if i + 1 < len(raw_syms):
            next_off = raw_syms[i + 1]["offset"]
        else:
            if data_obj.get("virtual_size_int") is not None:
                next_off = int(data_obj["virtual_size_int"])
            else:
                vsize = data_obj["virtual_size"]
                next_off = int(vsize, 16) if isinstance(vsize, str) else int(vsize)
        size = max(0, next_off - s["offset"])
        if s["offset"] < file_size:
            fb = min(size, file_size - s["offset"])
        else:
            fb = 0
        out.append(
            DataSym(s["name"], s["offset"], s["address"], size, fb, fb > 0, _mod_name(s))
        )
    return out, file_off, file_size


def _read_file_bytes(ds: DataSym, file_off: int) -> bytes:
    if ds.file_bytes <= 0:
        return b""
    with _EXE.open("rb") as f:
        f.seek(file_off + ds.offset)
        return f.read(ds.file_bytes)


# ── Struct field walking ──────────────────────────────────────────────────────

def _build_struct_defs() -> dict[str, list[tuple[str, c_ast.Node]]]:
    """Map ``struct foo`` → list of (field_name, field_type_AST) for every
    named struct definition found in hand-written headers.
    """
    out: dict[str, list[tuple[str, c_ast.Node]]] = {}
    for glob in _HEADER_GLOB:
        for p in sorted(Path().glob(glob)):
            try:
                ast = parse_c(p.read_text(errors="ignore"), str(p))
            except Exception:  # noqa: BLE001
                continue
            for ext in ast.ext:
                inner = None
                if isinstance(ext, c_ast.Decl) and isinstance(ext.type, c_ast.Struct) and ext.type.decls:
                    inner = ext.type
                elif isinstance(ext, c_ast.Typedef) and isinstance(ext.type, c_ast.TypeDecl) and isinstance(ext.type.type, c_ast.Struct) and ext.type.type.decls:
                    inner = ext.type.type
                if inner and inner.name:
                    out[inner.name] = [(fd.name, fd.type) for fd in inner.decls]
    return out


def _unwrap_struct_decl(t: c_ast.Node) -> c_ast.Struct | c_ast.Union | None:
    """Pull a Struct/Union node out of a TypeDecl wrapper."""
    if isinstance(t, (c_ast.Struct, c_ast.Union)):
        return t
    if isinstance(t, c_ast.TypeDecl) and isinstance(t.type, (c_ast.Struct, c_ast.Union)):
        return t.type
    return None


def _field_size_and_align(
    t: c_ast.Node,
    sdefs: dict[str, list[tuple[str, c_ast.Node]]] | None = None,
) -> tuple[int, int] | None:
    """Return (size, alignment) for a struct field type, or None if
    the type is unresolvable.

    Handles: pointer, array of resolvable, scalar (char/short/int/long),
    nested anonymous union, nested anonymous struct, named struct/union
    reference (looked up in ``sdefs``).
    """
    if isinstance(t, c_ast.PtrDecl):
        return (4, 4)
    if isinstance(t, c_ast.ArrayDecl):
        elem = _field_size_and_align(t.type, sdefs)
        if elem is None or not isinstance(t.dim, c_ast.Constant):
            return None
        try:
            n = int(t.dim.value, 0)
        except ValueError:
            return None
        return (elem[0] * n, elem[1])
    if isinstance(t, c_ast.TypeDecl):
        q = t.type
        if isinstance(q, c_ast.IdentifierType):
            names = q.names
            if "char" in names:
                return (1, 1)
            if "short" in names:
                return (2, 2)
            if "int" in names or "long" in names:
                return (4, 4)
        # TypeDecl wrapping a nested struct or union.
        sub = _unwrap_struct_decl(t)
        if sub is not None:
            return _struct_or_union_size(sub, sdefs)
    if isinstance(t, (c_ast.Struct, c_ast.Union)):
        return _struct_or_union_size(t, sdefs)
    return None


def _struct_or_union_size(
    node: c_ast.Struct | c_ast.Union,
    sdefs: dict[str, list[tuple[str, c_ast.Node]]] | None,
) -> tuple[int, int] | None:
    fields: list[tuple[str, c_ast.Node]] | None
    if node.decls:
        fields = [(fd.name, fd.type) for fd in node.decls]
    elif sdefs is not None and node.name and node.name in sdefs:
        fields = sdefs[node.name]
    else:
        return None
    if isinstance(node, c_ast.Union):
        max_sz = max_al = 0
        for _fname, ftype in fields:
            sa = _field_size_and_align(ftype, sdefs)
            if sa is None:
                return None
            if sa[0] > max_sz:
                max_sz = sa[0]
            if sa[1] > max_al:
                max_al = sa[1]
        if max_al and max_sz % max_al:
            max_sz += max_al - (max_sz % max_al)
        return (max_sz, max_al or 1)
    layout = _compute_struct_layout(fields, sdefs)
    if layout is None:
        return None
    return (layout[0], layout[2])


def _compute_struct_layout(
    fields: list[tuple[str, c_ast.Node]],
    sdefs: dict[str, list[tuple[str, c_ast.Node]]] | None = None,
) -> tuple[int, list[tuple[str, c_ast.Node, int, int]], int] | None:
    """Walk a struct's fields, computing per-field (offset, size) under
    Watcom -zp4 natural alignment.  Returns (total_size, fields_resolved,
    max_align) or None if any field is unresolvable.
    """
    offset = 0
    max_align = 1
    out = []
    for fname, ftype in fields:
        sa = _field_size_and_align(ftype, sdefs)
        if sa is None:
            return None
        sz, al = sa
        if al > max_align:
            max_align = al
        if offset % al:
            offset += al - (offset % al)
        out.append((fname, ftype, sz, offset))
        offset += sz
    if offset % max_align:
        offset += max_align - (offset % max_align)
    return offset, out, max_align


def _classify_field(ftype: c_ast.Node) -> tuple | None:
    """Return a tag for rendering: ('scalar', signed, size) | ('array',
    signed, elem_size, count) | ('ptr',) | None.
    """
    if isinstance(ftype, c_ast.PtrDecl):
        return ("ptr",)
    if isinstance(ftype, c_ast.ArrayDecl):
        if not isinstance(ftype.dim, c_ast.Constant):
            return None
        n = int(ftype.dim.value, 0)
        inner = ftype.type
        if not isinstance(inner, c_ast.TypeDecl):
            return None
        q = inner.type
        if not isinstance(q, c_ast.IdentifierType):
            return None
        names = q.names
        signed = "unsigned" not in names
        if "char" in names:
            return ("array", signed, 1, n)
        if "short" in names:
            return ("array", signed, 2, n)
        if "int" in names or "long" in names:
            return ("array", signed, 4, n)
        return None
    if isinstance(ftype, c_ast.TypeDecl):
        q = ftype.type
        if not isinstance(q, c_ast.IdentifierType):
            return None
        names = q.names
        signed = "unsigned" not in names
        if "char" in names:
            return ("scalar", signed, 1)
        if "short" in names:
            return ("scalar", signed, 2)
        if "int" in names or "long" in names:
            return ("scalar", signed, 4)
    return None


_SCALAR_FMTS = {
    (True, 1):  "<b", (False, 1): "<B",
    (True, 2):  "<h", (False, 2): "<H",
    (True, 4):  "<i", (False, 4): "<I",
}


def _read_scalar(raw: bytes, off: int, signed: bool, size: int) -> int:
    return struct.unpack_from(_SCALAR_FMTS[(signed, size)], raw, off)[0]


def _load_data_fixups() -> dict[int, tuple[int, int]]:
    """Return {data_seg_byte_offset → (target_obj, target_offset)} for the
    LE data segment of PS.EXE.  Cached on first call.
    """
    from c2.parsers.exe import parse_exe
    from c2.commands.fixups import parse_le_fixups
    _, _, le = parse_exe(_EXE)
    _, data_fm = parse_le_fixups(
        _EXE, le.le_offset, le.page_size, le.num_pages,
        le.objects[0].num_pages, le.objects[1].num_pages,
    )
    return data_fm


def _build_addr_index() -> tuple[dict[int, str], dict[int, str]]:
    """Return ({code_abs_addr → name}, {data_abs_addr → name})."""
    sym = json.loads(_SYMBOLS.read_text())
    code_idx, data_idx = {}, {}
    for s in sym["symbols"]:
        if s.get("is_data"):
            data_idx[s["address"]] = s["name"]
        else:
            code_idx[s["address"]] = s["name"]
    return code_idx, data_idx


class _PtrResolver:
    def __init__(self) -> None:
        self._fm: dict[int, tuple[int, int]] | None = None
        self._code: dict[int, str] | None = None
        self._data: dict[int, str] | None = None
        self._sorted_data: list[tuple[int, str]] | None = None

    def _ensure(self) -> None:
        if self._fm is None:
            self._fm = _load_data_fixups()
            self._code, self._data = _build_addr_index()
            self._sorted_data = sorted(self._data.items())

    def _resolve_interior(self, abs_addr: int) -> str | None:
        """Find the nearest data symbol <= abs_addr and render an interior
        pointer as ``(char *)&name + delta``.  Bails if the nearest symbol
        is suspiciously far away (probably a CRT scratch buffer).
        """
        assert self._sorted_data is not None
        from bisect import bisect_right
        addrs = [a for a, _ in self._sorted_data]
        i = bisect_right(addrs, abs_addr) - 1
        if i < 0:
            return None
        base_addr, base_name = self._sorted_data[i]
        delta = abs_addr - base_addr
        # Bail if there's a clearly closer next symbol that we straddled past.
        if delta > 0x10000:
            return None
        return f"(char *)&{base_name} + {delta}"

    def resolve_string(self, data_off: int) -> str | None:
        """If the LE fixup at ``data_off`` points to a NUL-terminated
        printable ASCII string inside the data segment, return a C
        string literal for it.  Otherwise return None.
        """
        self._ensure()
        assert self._fm is not None
        fx = self._fm.get(data_off)
        if fx is None:
            return None
        obj, tgt = fx
        if obj != 2:
            return None
        # Read up to ~256 bytes from the data segment at offset `tgt`.
        # Cached: load the whole data segment once via the symbols.json
        # `memory_map` slot (object 1).
        if not hasattr(self, "_data_bytes"):
            sym = json.loads(_SYMBOLS.read_text())
            data_obj = sym["memory_map"]["objects"][1]
            file_off = int(data_obj["file_offset_int"])
            sz = int(data_obj["file_size"])
            with _EXE.open("rb") as f:
                f.seek(file_off)
                self._data_bytes = f.read(sz)
        buf = self._data_bytes  # type: ignore[attr-defined]
        if tgt >= len(buf):
            return None
        nul = buf.find(b"\x00", tgt, min(tgt + 256, len(buf)))
        if nul < 0:
            return None
        sliced = buf[tgt:nul]
        if not all(32 <= b < 127 for b in sliced):
            return None
        s = sliced.decode("ascii")
        s = s.replace("\\", "\\\\").replace('"', '\\"')
        return '"' + s + '"'

    def resolve(self, data_off: int, raw_val: int) -> str | None:
        self._ensure()
        assert self._fm is not None and self._code is not None and self._data is not None
        fx = self._fm.get(data_off)
        if fx is None:
            return "0" if raw_val == 0 else None
        obj, tgt = fx
        if obj == 1:
            abs_addr = _CODE_BASE + tgt
            nm = self._code.get(abs_addr)
            return nm  # function pointer: bare name (interior code pointers are rare)
        if obj == 2:
            abs_addr = _DATA_BASE + tgt
            nm = self._data.get(abs_addr)
            if nm:
                # Array-typed targets decay to the address of their first
                # element, so the natural C form is `name` (not `&name`).
                # Scalar / struct-instance targets still want `&name`.
                shape = (_DECL_INDEX_CACHE or {}).get(nm)
                if shape is not None and shape.dims:
                    return nm
                return f"&{nm}"
            return self._resolve_interior(abs_addr)
        return None


def _render_value_at(
    raw: bytes, abs_off: int, rel_off: int, ftype: c_ast.Node,
    sdefs: dict[str, list[tuple[str, c_ast.Node]]],
    pr: _PtrResolver,
) -> str | None:
    """Render a single field value (possibly a nested struct/union/array)
    starting at ``raw[rel_off]``.  ``abs_off`` is the absolute data-segment
    byte offset of ``raw[rel_off]`` (used for fixup lookup).
    """
    # Pointer
    if isinstance(ftype, c_ast.PtrDecl):
        val = struct.unpack_from("<I", raw, rel_off)[0]
        return pr.resolve(abs_off, val)
    # Nested struct/union (anonymous or named)
    sub = _unwrap_struct_decl(ftype)
    if sub is not None:
        return _render_struct_or_union_at(raw, abs_off, rel_off, sub, sdefs, pr)
    # Array
    if isinstance(ftype, c_ast.ArrayDecl):
        if not isinstance(ftype.dim, c_ast.Constant):
            return None
        n = int(ftype.dim.value, 0)
        # char[N] (signed or unsigned) of printable ASCII -> string literal.
        inner_cls = _classify_field(ftype)
        if inner_cls is not None and inner_cls[0] == "array" and inner_cls[2] == 1:
            lit = _try_string_literal(raw, rel_off, n)
            if lit is not None:
                return lit
        # Otherwise render element-by-element.
        elem_sa = _field_size_and_align(ftype.type, sdefs)
        if elem_sa is None:
            return None
        elem_sz = elem_sa[0]
        parts = []
        for i in range(n):
            v = _render_value_at(
                raw, abs_off + i * elem_sz, rel_off + i * elem_sz,
                ftype.type, sdefs, pr,
            )
            if v is None:
                return None
            parts.append(v)
        return "{ " + ", ".join(parts) + " }"
    # Scalar
    if isinstance(ftype, c_ast.TypeDecl):
        cls = _classify_field(ftype)
        if cls is None or cls[0] != "scalar":
            return None
        return str(_read_scalar(raw, rel_off, cls[1], cls[2]))
    return None


def _render_struct_or_union_at(
    raw: bytes, abs_off: int, rel_off: int,
    node: c_ast.Struct | c_ast.Union,
    sdefs: dict[str, list[tuple[str, c_ast.Node]]],
    pr: _PtrResolver,
) -> str | None:
    if node.decls:
        fields = [(fd.name, fd.type) for fd in node.decls]
    elif node.name and node.name in sdefs:
        fields = sdefs[node.name]
    else:
        return None
    if isinstance(node, c_ast.Union):
        # C89 union initializer: braces around the first member only.
        first = fields[0]
        v = _render_value_at(raw, abs_off, rel_off, first[1], sdefs, pr)
        if v is None:
            return None
        return "{ " + v + " }"
    # Struct: walk layout, render each field.
    layout = _compute_struct_layout(fields, sdefs)
    if layout is None:
        return None
    _sz, fr, _al = layout
    parts = []
    for _fname, ftype, _fsz, foff in fr:
        v = _render_value_at(raw, abs_off + foff, rel_off + foff, ftype, sdefs, pr)
        if v is None:
            return None
        parts.append(v)
    return "{ " + ", ".join(parts) + " }"


def _render_struct_instance(
    name: str, raw: bytes, struct_name: str, data_off: int,
    sdefs: dict[str, list[tuple[str, c_ast.Node]]],
    pr: _PtrResolver,
) -> str | None:
    """Single instance (non-array) struct initializer."""
    fields = sdefs.get(struct_name)
    if not fields:
        return None
    layout = _compute_struct_layout(fields, sdefs)
    if layout is None:
        return None
    size, _fr, _al = layout
    if len(raw) < size:
        return None
    body = _render_struct_or_union_at(raw, data_off, 0, c_ast.Struct(struct_name, None), sdefs, pr)
    if body is None:
        return None
    return f"struct {struct_name} {name} = {body};"


def _render_struct_array(
    name: str, raw: bytes, struct_name: str, data_off: int,
    sdefs: dict[str, list[tuple[str, c_ast.Node]]],
    pr: _PtrResolver,
) -> str | None:
    fields = sdefs.get(struct_name)
    if not fields:
        return None
    layout = _compute_struct_layout(fields, sdefs)
    if layout is None:
        return None
    size, fr, _al = layout
    if size == 0:
        return None
    # Compute the un-padded (compact) size in case PS source packed this
    # struct.  If raw cleanly divides only by the un-padded size, use that.
    unpadded = 0
    if fr:
        last_f = fr[-1]
        unpadded = last_f[3] + last_f[2]
    n_inst = len(raw) // size
    tail = len(raw) - n_inst * size
    if (tail and unpadded and unpadded < size
            and len(raw) % unpadded == 0):
        size = unpadded
        n_inst = len(raw) // size
        tail = 0
    # Tolerate trailing zero pad (Watcom occasionally rounds the symbol size up).
    if tail and any(b != 0 for b in raw[n_inst * size:]):
        return None
    if n_inst == 0:
        return None
    classed = []
    for fname, ftype, _sz, off in fr:
        cls = _classify_field(ftype)
        # cls may be None for nested struct/union fields — still OK because
        # _render_value_at handles them.  We just lose the fast scalar path.
        classed.append((cls, ftype, off))
    insts = []
    for i in range(n_inst):
        ibase = i * size
        parts = []
        for cls, ftype, off in classed:
            field_off = ibase + off
            if cls is None:
                v = _render_value_at(raw, data_off + field_off, field_off, ftype, sdefs, pr)
                if v is None:
                    return None
            elif cls[0] == "ptr":
                val = struct.unpack_from("<I", raw, field_off)[0]
                v = pr.resolve(data_off + field_off, val)
                if v is None:
                    return None
            elif cls[0] == "scalar":
                v = str(_read_scalar(raw, field_off, cls[1], cls[2]))
            elif cls[0] == "array":
                _, signed, esz, n = cls
                # char[N] (signed or unsigned): try string literal first.
                if esz == 1:
                    lit = _try_string_literal(raw, field_off, n)
                    if lit is not None:
                        parts.append(lit)
                        continue
                vals = [str(_read_scalar(raw, field_off + j*esz, signed, esz)) for j in range(n)]
                v = "{ " + ", ".join(vals) + " }"
            else:
                return None
            parts.append(v)
        insts.append("{ " + ", ".join(parts) + " }")
    body = ",\n    ".join(insts)
    return f"struct {struct_name} {name}[{n_inst}] = {{\n    {body}\n}};"


def ext_name_placeholder(decl_text: str) -> str | None:
    """Given a stringified function-pointer-typed Decl like
    ``void *(*MEM_alloc)(unsigned int size)``, replace the variable
    name with the empty placeholder ``*`` and return
    ``void *(*)(unsigned int size)``.  Returns None on parse failure.
    """
    # The variable name lives immediately inside `(*<name>)`.
    import re
    m = re.search(r"\(\s*\*\s*([A-Za-z_]\w*)\s*\)", decl_text)
    if not m:
        return None
    return decl_text[: m.start()] + "(*)" + decl_text[m.end():]


def _decl_name_type(t: c_ast.Node) -> tuple[str, tuple[int | None, ...]] | None:
    dims: list[int | None] = []
    while isinstance(t, c_ast.ArrayDecl):
        if t.dim is None:
            dims.append(None)
        elif isinstance(t.dim, c_ast.Constant) and t.dim.type == "int":
            try:
                dims.append(int(t.dim.value, 0))
            except ValueError:
                return None
        else:
            return None
        t = t.type
    if isinstance(t, c_ast.TypeDecl):
        q = t.type
        if isinstance(q, c_ast.IdentifierType):
            return " ".join(q.names), tuple(dims)
        if isinstance(q, (c_ast.Struct, c_ast.Union)) and q.name:
            return f"{q.__class__.__name__.lower()} {q.name}", tuple(dims)
    # Function pointer: `ret (*)(args)`.  For the no-arg / scalar-return
    # case we return a stable `ret (*)(void)` key (every PS dispatch
    # table).  For arbitrary signatures we accept scalar slots and
    # stash the full type text in `base` (with the name replaced by an
    # empty placeholder) so the renderer can rebuild the declaration.
    if isinstance(t, c_ast.PtrDecl) and isinstance(t.type, c_ast.FuncDecl):
        fd = t.type
        args = fd.args.params if fd.args else []
        ret = fd.type
        # Canonical `ret (*)(void)` shortcut when ret is a plain ident.
        if (
            isinstance(ret, c_ast.TypeDecl)
            and isinstance(ret.type, c_ast.IdentifierType)
            and all(
                isinstance(p, c_ast.Typename)
                and isinstance(p.type, c_ast.TypeDecl)
                and isinstance(p.type.type, c_ast.IdentifierType)
                and p.type.type.names == ["void"]
                for p in args
            )
        ):
            ret_str = " ".join(ret.type.names)
            return f"{ret_str} (*)(void)", tuple(dims)
        # Arbitrary signature, scalar only.
        if not dims:
            gen = c_generator.CGenerator()
            try:
                sig = gen.visit(t).strip()
            except Exception:  # noqa: BLE001
                return None
            # When pycparser visits a name-less PtrDecl-FuncDecl, the
            # output already has `(*)` rather than `(*name)`.  When it
            # visits a full Decl, the name is embedded inside `(*name)`
            # and we strip it with `ext_name_placeholder`.
            if "(*)" in sig:
                return sig, tuple(dims)
            placeholder = ext_name_placeholder(sig)
            if placeholder is not None:
                return placeholder, tuple(dims)
    # Pointer to scalar (e.g. `char *`).
    if isinstance(t, c_ast.PtrDecl) and isinstance(t.type, c_ast.TypeDecl):
        inner = t.type.type
        if isinstance(inner, c_ast.IdentifierType):
            return " ".join(inner.names) + " *", tuple(dims)
    # Anonymous struct or other complex form: not currently initializer-renderable.
    return None


def _try_string_literal(raw: bytes, off: int, n: int) -> str | None:
    """If ``raw[off:off+n]`` is printable ASCII followed by zero pad,
    return a C string literal; else return None.

    Heuristic guards (avoid false positives on tiny binary char arrays):
      * At least 2 printable bytes before the first NUL.
      * Every byte before the first NUL is printable (32..126, plus
        tab/CR/LF).
      * Every byte at or after the first NUL is also 0 (no garbage tail).
    """
    if n < 2:
        return None
    slc = raw[off:off + n]
    if len(slc) < n:
        return None
    # Locate the first NUL terminator.  If there is none, the whole
    # range must be printable.
    nul = slc.find(b"\0")
    if nul < 0:
        content = slc
        tail = b""
    else:
        content = slc[:nul]
        tail = slc[nul:]
    if len(content) < 2:
        return None
    if any(b not in (9, 10, 13) and not (32 <= b < 127) for b in content):
        return None
    if any(b != 0 for b in tail):
        return None
    s = content.decode("ascii")
    s = s.replace("\\", "\\\\").replace('"', '\\"')
    s = s.replace("\t", "\\t").replace("\r", "\\r").replace("\n", "\\n")
    return '"' + s + '"'


def _build_decl_index() -> dict[str, CTypeShape]:
    gen = c_generator.CGenerator()
    found: dict[str, CTypeShape] = {}
    for glob in _SEARCH_GLOBS:
        for path in sorted(Path().glob(glob)):
            try:
                ast = parse_c(path.read_text(errors="ignore"), str(path))
            except Exception:
                continue
            for ext in ast.ext:
                if not isinstance(ext, c_ast.Decl) or not ext.name:
                    continue
                shape = _decl_name_type(ext.type)
                if shape is None:
                    continue
                base, dims = shape
                # Score sources by trust: hand-written hand-headers >
                # generated c2_data.h > .c file definitions (those tend
                # to lag behind the most recent header rename).
                ps = str(path)
                if ps.endswith(("c2_data.h", "c2_funcs.h")):
                    score = 1
                elif ps.endswith(".h"):
                    score = 2
                else:
                    score = 0
                old = found.get(ext.name)
                if old is not None:
                    op = str(old.source)
                    if op.endswith(("c2_data.h", "c2_funcs.h")):
                        old_score = 1
                    elif op.endswith(".h"):
                        old_score = 2
                    else:
                        old_score = 0
                    if old_score > score:
                        continue
                found[ext.name] = CTypeShape(base, dims, gen.visit(ext), path)
    global _DECL_INDEX_CACHE
    _DECL_INDEX_CACHE = found
    return found


def _ctype_size(base: str) -> int | None:
    if base in {"char", "signed char", "unsigned char"}:
        return 1
    if base in {"short", "signed short", "unsigned short"}:
        return 2
    if base in {"int", "signed int", "unsigned int"}:
        return 4
    return None


def _unpack_scalar(raw: bytes, off: int, base: str) -> int | str:
    if base == "char":
        return raw[off]
    if base in {"unsigned char"}:
        return raw[off]
    if base == "signed char":
        return struct.unpack_from("<b", raw, off)[0]
    if base in {"short", "signed short"}:
        return struct.unpack_from("<h", raw, off)[0]
    if base == "unsigned short":
        return struct.unpack_from("<H", raw, off)[0]
    if base in {"int", "signed int"}:
        return struct.unpack_from("<i", raw, off)[0]
    if base == "unsigned int":
        return struct.unpack_from("<I", raw, off)[0]
    raise ValueError(base)


def _format_nested(vals: list[int | str], dims: tuple[int, ...], indent: int = 0) -> str:
    sp = " " * indent
    if not dims:
        return str(vals.pop(0))
    n = dims[0]
    if len(dims) == 1:
        row = [str(vals.pop(0)) for _ in range(n)]
        return "{ " + ", ".join(row) + " }"
    parts = []
    for _ in range(n):
        parts.append(" " * (indent + 4) + _format_nested(vals, dims[1:], indent + 4))
    return "{\n" + ",\n".join(parts) + "\n" + sp + "}"


def _resolve_dims(dims: tuple[int | None, ...], raw_len: int, elem: int) -> tuple[int, ...] | None:
    if not dims:
        return ()
    unknowns = [i for i, d in enumerate(dims) if d is None]
    if len(unknowns) > 1:
        return None
    known_prod = elem
    for d in dims:
        if d is not None:
            known_prod *= d
    if unknowns:
        if known_prod == 0 or raw_len % known_prod != 0:
            return None
        out = list(dims)
        out[unknowns[0]] = raw_len // known_prod
        return tuple(int(d) for d in out)  # type: ignore[arg-type]
    total = known_prod
    if total > raw_len:
        return None
    return tuple(int(d) for d in dims)  # type: ignore[arg-type]


def _render_initializer(
    name: str, raw: bytes, shape: CTypeShape,
    data_off: int = 0,
    sdefs: dict[str, list[tuple[str, c_ast.Node]]] | None = None,
    pr: _PtrResolver | None = None,
) -> str | None:
    # Struct array: `struct foo bar[]`, or single instance `struct foo bar`.
    if shape.base.startswith("struct ") and sdefs is not None and pr is not None:
        struct_name = shape.base[len("struct "):]
        if shape.dims and len(shape.dims) == 1:
            return _render_struct_array(name, raw, struct_name, data_off, sdefs, pr)
        if not shape.dims:
            return _render_struct_instance(name, raw, struct_name, data_off, sdefs, pr)
        return None
    # Scalar function-pointer slot: e.g.
    #   shape.base = "void *(*)(unsigned int size)"
    #   -> emit `void *(*name)(unsigned int size) = malloc;`
    if ("(*)" in shape.base and not shape.dims and pr is not None
            and not shape.base.endswith(" (*)(void)")):
        if len(raw) != 4:
            return None
        val = struct.unpack_from("<I", raw, 0)[0]
        v = pr.resolve(data_off, val)
        if v is None:
            return None
        decl_with_name = shape.base.replace("(*)", f"(*{name})", 1)
        return f"{decl_with_name} = {v};"
    # Function-pointer array: `ret (*name[N])(void)` rendered from LE fixups.
    if shape.base.endswith(" (*)(void)") and pr is not None:
        if not (shape.dims and len(shape.dims) == 1):
            return None
        n = shape.dims[0]
        if n is None:
            n = len(raw) // 4
        if n * 4 > len(raw):
            return None
        ret_type = shape.base[: -len(" (*)(void)")]
        parts = []
        for i in range(n):
            val = struct.unpack_from("<I", raw, i * 4)[0]
            v = pr.resolve(data_off + i * 4, val)
            if v is None:
                return None
            parts.append(v)
        body = ",\n    ".join(parts)
        return f"{ret_type} (*{name}[{n}])(void) = {{\n    {body}\n}};"
    # `char *foo[N]` / `unsigned char *foo[N]` / ... : per-entry pointer
    # resolution via the same LE fixup path.  When the element type is
    # `char *` (or `unsigned char *`) and the fixup points to a
    # NUL-terminated printable ASCII string, emit it as a C string
    # literal for readability.
    if shape.base.endswith(" *") and pr is not None and shape.dims and len(shape.dims) == 1:
        n = shape.dims[0]
        if n is None:
            n = len(raw) // 4
        if n * 4 > len(raw):
            return None
        is_charptr = shape.base in ("char *", "unsigned char *", "signed char *")
        parts = []
        for i in range(n):
            val = struct.unpack_from("<I", raw, i * 4)[0]
            v = None
            if is_charptr:
                v = pr.resolve_string(data_off + i * 4)
            if v is None:
                v = pr.resolve(data_off + i * 4, val)
            if v is None:
                return None
            parts.append(v)
        body = ",\n    ".join(parts)
        return f"{shape.base}{name}[{n}] = {{\n    {body}\n}};"
    elem = _ctype_size(shape.base)
    if elem is None:
        return None
    # Scalar (no array dims): emit `T name = <val>;` when raw matches elem size.
    if not shape.dims:
        if len(raw) != elem:
            return None
        val = _unpack_scalar(raw, 0, shape.base)
        return f"{shape.base} {name} = {val};"
    dims = _resolve_dims(shape.dims, len(raw), elem)
    if dims is None:
        return None
    total = elem
    for d in dims:
        total *= d
    if total > len(raw):
        return None
    # Top-level `char foo[N]`: try a string literal first.
    if elem == 1 and len(dims) == 1 and shape.base in {"char", "signed char", "unsigned char"}:
        lit = _try_string_literal(raw, 0, dims[0])
        if lit is not None:
            suffix = f"[{dims[0]}]"
            return f"{shape.base} {name}{suffix} = {lit};"
    vals = [_unpack_scalar(raw, i, shape.base) for i in range(0, total, elem)]
    init = _format_nested(vals, dims)
    suffix = "".join(f"[{d}]" for d in dims)
    return f"{shape.base} {name}{suffix} = {init};"


def _hex_dump(raw: bytes, width: int = 16) -> str:
    lines = []
    for i in range(0, len(raw), width):
        chunk = raw[i:i+width]
        lines.append(f"{i:04x}: " + " ".join(f"{b:02x}" for b in chunk))
    return "\n".join(lines)


def _gen_datainit_file(out_path: Path) -> tuple[int, int]:
    """Rebuild ``decomp/src/datainit.c`` from current symbol metadata.

    Returns (initializer_count, struct_skip_count).
    """
    import pycparser
    from pycparser import c_ast as _ca
    syms, file_off, _ = _load_symbols()
    by_name = {s.name: s for s in syms}
    decls = _build_decl_index()
    sdefs = _build_struct_defs()
    pr = _PtrResolver()
    code_idx, _ = _build_addr_index()
    code_names = set(code_idx.values())

    src_dir = Path("decomp/src")
    defined_elsewhere: set[str] = set()
    for p in src_dir.glob("*.c"):
        if p.name == out_path.name:
            continue
        try:
            ast = parse_c(p.read_text(errors="replace"), p.name)
        except pycparser.c_parser.ParseError:
            continue
        for node in ast.ext:
            if (
                isinstance(node, _ca.Decl) and node.name
                and "extern" not in (node.storage or [])
                and not isinstance(node.type, _ca.FuncDecl)
            ):
                defined_elsewhere.add(node.name)

    body_lines: list[str] = []
    skipped = 0
    for sym in sorted(decls):
        if sym in defined_elsewhere:
            continue
        ds = by_name.get(sym)
        if not ds or not ds.file_bytes:
            continue
        # CRT / linked-library data (e.g. cstrt386's __nullarea, which
        # otherwise absorbs the unnamed string-literal pool) is not part
        # of the game's own static data — we link the real CRT/AIL.
        if _is_library_module(ds.module):
            continue
        raw = _read_file_bytes(ds, file_off)
        init = _render_initializer(
            sym, raw, decls[sym],
            data_off=ds.offset, sdefs=sdefs, pr=pr,
        )
        if init is None:
            if decls[sym].base.startswith("struct "):
                skipped += 1
            continue
        comment = _SYMBOL_COMMENTS.get(sym)
        if comment:
            body_lines.append("/* " + comment + " */")
        body_lines.append(init)
        body_lines.append("")

    # Collect referenced names that need forward decls.
    body_text = "\n".join(body_lines)
    fn_refs: set[str] = set()
    data_refs: set[str] = set()
    # Use a lookahead for the trailing delimiter so consecutive matches
    # like `{ A, B, C }` find every identifier (the regex engine would
    # otherwise consume the comma after A and skip B).
    for m in re.finditer(r"(?:[,{])\s*([a-zA-Z_]\w+)\s*(?=[,}])", body_text):
        nm = m.group(1)
        if nm in code_names:
            fn_refs.add(nm)
    # Scalar function-pointer slots: `... = name;` at end of statement.
    for m in re.finditer(r"=\s*([a-zA-Z_]\w+)\s*;", body_text):
        nm = m.group(1)
        if nm in code_names:
            fn_refs.add(nm)
    for m in re.finditer(r"&([a-zA-Z_]\w+)\b", body_text):
        data_refs.add(m.group(1))

    # Which data refs need explicit forward decls (not in headers / .c)?
    declared_names: set[str] = set()
    for h in Path("decomp/include").glob("*.h"):
        for m in re.finditer(r"\bextern\s+[^;]+?\b([a-zA-Z_]\w+)\s*[;\[]", h.read_text(errors="replace")):
            declared_names.add(m.group(1))
    for p in src_dir.glob("*.c"):
        if p.name == out_path.name:
            continue
        for m in re.finditer(r"^\s*(?:extern\s+)?\w[\w\s\*]+\b([a-zA-Z_]\w+)\s*(?:\[|;|=)", p.read_text(errors="replace"), re.M):
            declared_names.add(m.group(1))
    undeclared_data = sorted(data_refs - declared_names)

    header = [
        "// Static data initializers extracted from PS.EXE via `c2 data-init --all`.",
        "//",
        "// These globals are declared `extern` in c2_data.h or in a hand-written",
        "// header (entities.h / smacker.h / c2_types.h); their initial bytes are",
        "// taken verbatim from the LE data segment in PS.EXE so the rebuilt image",
        "// reproduces PS startup state.  Hand-decompiled .c files that own one",
        "// of these symbols should move the initializer there (with a matching",
        "// signature) and delete it from this file.",
        "",
        '#include "c2_data.h"',
        "",
    ]
    if undeclared_data:
        header.append("/* Forward externs for data symbols with no .h declaration. */")
        for nm in undeclared_data:
            ds = by_name.get(nm)
            sz = ds.size if ds else 4
            header.append(f"extern char {nm}[{sz}];")
        header.append("")
    # CRT names — use the real prototypes via stdlib.h rather than
    # fake `extern void NAME(void);` lines that would clash with the
    # built-in signatures.
    _CRT_NAMES = {"malloc", "free", "calloc", "realloc"}
    crt_refs = fn_refs & _CRT_NAMES
    other_refs = fn_refs - _CRT_NAMES
    if crt_refs:
        header.append("#include <stdlib.h>")
        header.append("")
    if other_refs:
        header.append("/* Forward decls for callbacks referenced by initializers. */")
        for nm in sorted(other_refs):
            header.append(f"extern void {nm}(void);")
        header.append("")

    out_path.write_text("\n".join(header) + "\n" + body_text + "\n")
    return len([l for l in body_lines if l]), skipped


def data_init(
    symbol: Annotated[str | None, typer.Argument(help="Data symbol to dump. Omit to list file-backed data symbols.")] = None,
    bytes_only: Annotated[bool, typer.Option("--bytes", help="Force hex byte dump even when a C type is known.")] = False,
    limit: Annotated[int, typer.Option("--limit", "-n", help="Limit list output; 0 means no limit.")] = 200,
    write_all: Annotated[bool, typer.Option("--all", help="Regenerate decomp/src/datainit.c with every renderable initializer.")] = False,
) -> None:
    """List or dump initialized data bytes from PS.EXE.

    With no symbol, prints file-backed data symbols and any declaration shape
    found in decomp/include or decomp/src.  With a symbol, emits a C initializer
    when the declaration is a fixed-size scalar array; otherwise emits a hex dump.
    With ``--all``, rewrites ``decomp/src/datainit.c`` containing every initializer
    the renderer can produce — scalars, scalar arrays, multi-dim arrays, and
    struct arrays with pointer fixups resolved against ``symbols.json``.
    """
    if write_all:
        out = Path("decomp/src/datainit.c")
        n_init, n_skip = _gen_datainit_file(out)
        typer.echo(f"wrote {n_init} initializers to {out}")
        if n_skip:
            typer.echo(f"skipped {n_skip} struct symbols (nested union/anon-struct fields not yet supported)")
        return

    syms, file_off, _file_size = _load_symbols()
    by_name = {s.name: s for s in syms}
    decls = _build_decl_index()
    sdefs = _build_struct_defs()
    pr = _PtrResolver()

    if symbol is None:
        rows = [s for s in syms if s.file_backed]
        if limit:
            rows = rows[:limit]
        for s in rows:
            sh = decls.get(s.name)
            typ = sh.decl_text if sh else "?"
            typer.echo(f"{s.name:40} off=0x{s.offset:05x} size={s.size:6} file={s.file_bytes:6}  {typ}")
        return

    if symbol not in by_name:
        raise typer.BadParameter(f"unknown data symbol: {symbol}")
    ds = by_name[symbol]
    raw = _read_file_bytes(ds, file_off)
    sh = decls.get(symbol)
    typer.echo(f"/* {symbol}: data+0x{ds.offset:x}, size {ds.size}, file-backed {ds.file_bytes} bytes */")
    if sh:
        typer.echo(f"/* declaration: {sh.decl_text}  ({sh.source}) */")
    if sh and not bytes_only:
        rendered = _render_initializer(
            symbol, raw, sh,
            data_off=ds.offset, sdefs=sdefs, pr=pr,
        )
        if rendered is not None:
            typer.echo(rendered)
            return
        typer.echo("/* initializer not yet renderable; hex bytes follow */")
    typer.echo(_hex_dump(raw))

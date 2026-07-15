"""Carve a named function's bytes + fixup mask out of a pre-link OMF .obj.

The forge fast path is **compile-only** -- no wlink, no LE binary -- so for
every variant we have to recover the target function's bytes directly from
the `.obj`.  Watcom's ``wcc386 -fo=foo.obj`` writes a standard Intel OMF
record stream; :mod:`c2.parsers.omf` already knows how to parse the
``_TEXT`` segment + PUBDEF boundaries + FIXUPP records.  This module is
the thin forge-side wrapper that:

  1. resolves the watcall-mangled symbol name (``show_menus`` ⇒
     ``show_menus_``);
  2. returns ``(bytes, fixup_offsets)`` for that one function, with
     offsets already relative to the function start (matches the
     calling convention of :func:`c2.commands.decomp_verify._build_diff_rows`);
  3. raises a clear error if the symbol is missing (build succeeded but
     the function the user named did not appear -- e.g. inlined, stripped,
     wrong name).

No state is held; the parse is cheap (<5 ms for a typical decomp TU).
"""

from __future__ import annotations

from pathlib import Path

from c2.parsers.omf import parse_obj_functions


class FunctionNotInObj(KeyError):
    """The requested function is not a public symbol in the .obj's _TEXT."""


def carve(obj_path: Path | str, function: str) -> tuple[bytes, set[int]]:
    """Return ``(code_bytes, fixup_byte_offsets)`` for ``function``.

    ``function`` is accepted in either the C source spelling
    (``show_menus``) or the linker-mangled ``__watcall`` spelling
    (``show_menus_``); the trailing underscore is tried automatically.

    The returned fixup set contains *every byte* of every relocation
    field, so a downstream byte-wise diff can mask them by zeroing the
    corresponding positions on both PS and RC sides (same convention as
    :func:`c2.commands.cgex.diff_bytes`).
    """
    obj_path = Path(obj_path)
    funcs = parse_obj_functions(obj_path)
    table = {name: (code, fix) for name, code, fix in funcs}
    for cand in (function, function + "_", function.rstrip("_")):
        if cand in table:
            return table[cand]
    raise FunctionNotInObj(
        f"{function!r} not in {obj_path}; "
        f"available: {sorted(table)[:8]}{'…' if len(table) > 8 else ''}"
    )


def function_line_marks(
    obj_path: Path | str, function: str, func_size: int,
) -> tuple[tuple[int, int], ...]:
    """Return the variant's -d1 LINNUM marks ``((rel_off, line), ...)``.

    Forge variants compile with ``-d1`` (PS_CFLAGS), so every .obj
    already carries the mark stream; this reads it back so the judge
    can feed the dual-marks run ledger (``c2.runledger``) -- the
    attribution-exact ir/islands metric.  Works for BOTH build modes:
    the marks are function-relative offsets, identical in the .obj and
    the linked LE image.

    Returns () when the function or the LINNUM records are missing
    (the judge then degrades to the drift-prone binir ir -- never
    fails the score).
    """
    import struct

    obj_path = Path(obj_path)
    try:
        raw = obj_path.read_bytes()
    except OSError:
        return ()
    # Minimal PUBDEF/SEGDEF walk: find _TEXT's segment index + the
    # function's offset within it.  (parse_obj_functions discards the
    # offsets, so we re-walk; objs are small and this is ~free next to
    # the compile.)
    pos = 0
    lnames: list[str] = [""]
    seg_idx = 0
    seg_names: dict[int, str] = {}
    pubdefs: list[tuple[str, int, int]] = []
    while pos < len(raw):
        rt = raw[pos]
        rl = struct.unpack_from("<H", raw, pos + 1)[0]
        body = raw[pos + 3: pos + 2 + rl]
        if rt == 0x96:                       # LNAMES
            i = 0
            while i < len(body):
                n = body[i]; i += 1
                lnames.append(body[i:i + n].decode("ascii", errors="replace"))
                i += n
        elif rt in (0x98, 0x99):             # SEGDEF / SEGDEF32
            seg_idx += 1
            ni = body[5 if rt == 0x99 else 3]
            seg_names[seg_idx] = lnames[ni] if ni < len(lnames) else "?"
        elif rt in (0x90, 0x91):             # PUBDEF / PUBDEF32
            is32 = rt == 0x91
            seg = body[1]
            i = 2
            if seg == 0:
                i += 2
            while i < len(body):
                n = body[i]; i += 1
                name = body[i:i + n].decode("ascii", errors="replace")
                i += n
                off = struct.unpack_from("<I" if is32 else "<H", body, i)[0]
                i += (4 if is32 else 2) + 1
                pubdefs.append((name, seg, off))
        pos += 3 + rl

    text_seg = next((si for si, nm in seg_names.items() if nm == "_TEXT"), 1)
    func_off = None
    for cand in (function, function + "_", function.rstrip("_")):
        func_off = next((o for n, s, o in pubdefs
                         if n == cand and s == text_seg), None)
        if func_off is not None:
            break
    if func_off is None:
        return ()
    try:
        from c2.decompile._engine.parsers.omf_lines import function_line_map
        return function_line_map(obj_path, func_off, func_size,
                                 text_seg=text_seg)
    except Exception:
        return ()


def carve_all(obj_path: Path | str) -> dict[str, tuple[bytes, set[int]]]:
    """Return the full ``{function: (bytes, fixups)}`` map for an .obj.

    Use when a single experiment touches several functions and you want
    to amortise the OMF parse.
    """
    return {name: (code, fix) for name, code, fix in parse_obj_functions(obj_path)}

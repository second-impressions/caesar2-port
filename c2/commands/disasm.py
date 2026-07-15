r"""disasm command: dump annotated x86 disassembly of a PS.EXE function.

Resolves three kinds of references for each instruction:

  1. **Branch targets** (`call` / `jmp` / `jcc`): looked up against the
     symbol table so cross-function calls show the callee name.
  2. **Memory operands**: the LE fixup table is consulted for any byte
     within the instruction; a hit names the data symbol pointed at.
  3. **Source line numbers**: the Watcom debug-info `line_numbers`
     table maps each code offset to a source line in the original
     `.c` file.

Usage::

    uv run c2 disasm <name>          # by symbol name
    uv run c2 disasm 0x59F76         # by address
    uv run c2 disasm <name> --bytes  # show raw bytes
    uv run c2 disasm <name> --no-fixups  # don't expand data refs
    uv run c2 disasm <name> --size 32    # override size
    uv run c2 disasm <name> -o out.txt    # write to file

Library use::

    from c2.commands.disasm import disasm_function
    for line in disasm_function("set_new_province"):
        print(line)
"""

from __future__ import annotations

import json
import re
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Iterable, Optional

import capstone
import typer


# ── Cached state ────────────────────────────────────────────────────────────

@dataclass
class _Ctx:
    """Everything needed to annotate one PS.EXE function."""
    code: bytes
    code_base: int
    data_base: int
    code_fixups: dict[int, tuple[int, int]]   # code_off → (tgt_obj, tgt_off)
    addr_to_name: dict[int, str]              # virtual addr → symbol name
    name_to_addr: dict[str, int]              # symbol name → virtual addr
    name_to_size: dict[str, int]              # function name → size in bytes
    line_lookup:  dict[int, tuple[str, int]]  # virt addr → (file, line)
    data_bytes:   bytes                       # raw bytes of the data segment
    data_file_size: int                       # how much of data is in the file


# ── String detection ────────────────────────────────────────────────────────

_STRING_MIN_LEN = 3   # minimum printable chars before NUL
_STRING_MAX_LEN = 64  # cap for inline preview


def _peek_string(ctx: _Ctx, vaddr: int) -> Optional[str]:
    """If `vaddr` points to a NUL-terminated printable ASCII run of at
    least ``_STRING_MIN_LEN`` chars *inside* the file-stored portion of
    the data segment, return the string content (truncated to
    ``_STRING_MAX_LEN``).  Otherwise return None.

    Only the file-stored prefix is inspected: bytes past
    ``data_file_size`` exist in the LE image as zero-filled BSS, which
    always parses as a 0-length "string" — never useful, and gives a
    confusing empty annotation.
    """
    off = vaddr - ctx.data_base
    if off < 0 or off >= ctx.data_file_size:
        return None
    end = ctx.data_bytes.find(b"\x00", off, off + _STRING_MAX_LEN + 1)
    if end < 0:
        return None
    raw = ctx.data_bytes[off:end]
    if len(raw) < _STRING_MIN_LEN:
        return None
    if not all(0x20 <= b <= 0x7E or b in (9, 10, 13) for b in raw):
        return None
    return raw.decode("ascii")


_ctx_cache: dict[tuple[Path, Path], _Ctx] = {}


def _build_ctx(symbols_json: Path, exe_path: Path) -> _Ctx:
    """Load and cache everything needed for annotated disasm."""
    key = (symbols_json.resolve(), exe_path.resolve())
    cached = _ctx_cache.get(key)
    if cached is not None:
        return cached

    sym = json.loads(symbols_json.read_text())
    code_base = sym["memory_map"]["objects"][0]["base_address_int"]
    data_base = sym["memory_map"]["objects"][1]["base_address_int"]
    addr_to_name = {s["address"]: s["name"] for s in sym["symbols"]}
    name_to_addr = {s["name"]: s["address"] for s in sym["symbols"]}

    code_syms = sorted(
        [s for s in sym["symbols"] if s.get("is_code")],
        key=lambda s: s["address"],
    )
    name_to_size: dict[str, int] = {}
    for i, s in enumerate(code_syms[:-1]):
        name_to_size[s["name"]] = code_syms[i + 1]["address"] - s["address"]

    # Source-line lookup
    line_lookup: dict[int, tuple[str, int]] = {}
    for ln in sym.get("line_numbers", []):
        line_lookup[ln["offset"] + code_base] = (
            ln.get("file", ""), ln.get("line", 0),
        )

    # Code section + fixup table
    from c2.commands.decomp_verify import _load_le_code_and_fixups
    from c2.commands.fixups import parse_le_fixups

    code_bin, _ = _load_le_code_and_fixups(exe_path)
    le_off = int(sym["memory_map"]["le_header_offset"], 16)
    raw = exe_path.read_bytes()
    obj_off_val = struct.unpack_from("<I", raw, le_off + 0x40)[0]
    obj_abs = le_off + obj_off_val
    code_pages = struct.unpack_from("<I", raw, obj_abs + 16)[0]
    data_pages = struct.unpack_from("<I", raw, obj_abs + 24 + 16)[0]
    code_fixups, _ = parse_le_fixups(
        exe_path, le_off, 4096,
        code_pages + data_pages, code_pages, data_pages,
    )

    # Pull the file-stored portion of the data segment so _peek_string()
    # can detect string literals at fixup targets.  The LE virtual size
    # is far larger than file_size (the rest is zero-filled BSS), so we
    # only keep what's actually in the file.
    data_obj = sym["memory_map"]["objects"][1]
    data_file_off = data_obj["file_offset_int"]
    data_file_size = data_obj["file_size"]
    data_bytes = raw[data_file_off : data_file_off + data_file_size]

    ctx = _Ctx(
        code=code_bin, code_base=code_base, data_base=data_base,
        code_fixups=code_fixups, addr_to_name=addr_to_name,
        name_to_addr=name_to_addr, name_to_size=name_to_size,
        line_lookup=line_lookup,
        data_bytes=data_bytes, data_file_size=data_file_size,
    )
    _ctx_cache[key] = ctx
    return ctx


# ── Annotation helpers ──────────────────────────────────────────────────────

def _resolve_fixup(
    ctx: _Ctx, func_offset: int, insn_off: int, insn_size: int,
) -> Optional[str]:
    """If any byte of this instruction is a fixup site, return its target
    as ``"name"`` or ``"name+0x.."`` (or absolute hex if not in the
    symbol table).

    When the fixup target lies inside a printable NUL-terminated string
    in the data segment, the literal is appended as ``= "…"`` so the
    decomp writer can replace the symbol with a string literal in C.
    """
    for k in range(insn_size):
        rec = ctx.code_fixups.get(func_offset + insn_off + k)
        if rec is None:
            continue
        tgt_obj, tgt_off = rec
        vaddr = (ctx.code_base if tgt_obj == 1 else ctx.data_base) + tgt_off
        # Resolve the symbolic name first.
        name = ctx.addr_to_name.get(vaddr)
        if name is None:
            # Find nearest symbol below; otherwise use raw hex.
            below = max(
                (a for a in ctx.addr_to_name if a <= vaddr),
                default=None,
            )
            if below is not None and (vaddr - below) < 0x1000:
                name = f"{ctx.addr_to_name[below]}+0x{vaddr - below:X}"
            else:
                name = f"0x{vaddr:X}"

        # Code-segment fixups (branches that went via fixup, not relative)
        # never point at strings; only inspect data-segment refs.
        if tgt_obj != 1:
            preview = _peek_string(ctx, vaddr)
            if preview is not None:
                # Truncate visually at MAX_LEN so a long string doesn't
                # blow past the line-width budget; show an ellipsis when
                # it would have been longer.
                shown = preview
                if len(shown) > _STRING_MAX_LEN:
                    shown = shown[:_STRING_MAX_LEN] + "…"
                return f'{name} = "{shown}"'
        return name
    return None


def _resolve_branch(ctx: _Ctx, op_str: str) -> Optional[str]:
    """If `op_str` is a hex absolute address, return the matching
    code-symbol name (if any).  Capstone decodes call/jmp targets into
    'capstone-relative' offsets when started at func_offset, so the
    'address' is computed as (func_addr + cs_address)."""
    m = re.match(r"^0x([0-9a-fA-F]+)$", op_str.strip())
    if not m:
        return None
    t = int(m.group(1), 16)
    return ctx.addr_to_name.get(t)


# ── Core function ───────────────────────────────────────────────────────────

@dataclass
class DisasmLine:
    address:  int
    file:     str
    line:     int
    bytes_:   bytes
    mnemonic: str
    op_str:   str
    target:   Optional[str]   # branch-target symbol name, if any
    data_ref: Optional[str]   # fixed-up data symbol, if any


def disasm_function(
    name_or_addr: str,
    *,
    size: Optional[int] = None,
    symbols_json: Path = Path("data/out/symbols.json"),
    exe_path: Path = Path("data/PS.EXE"),
) -> tuple[int, int, list[DisasmLine]]:
    """Return ``(start_address, size, lines)`` for one function in PS.EXE.

    ``name_or_addr`` may be a symbol name, ``"0x12345"``, or a decimal
    address.  ``size`` overrides the inferred size (default: distance to
    next code symbol).
    """
    ctx = _build_ctx(symbols_json, exe_path)

    # Resolve to a virtual address.
    s = name_or_addr.strip()
    if s.lower().startswith("0x"):
        addr = int(s, 16)
    elif s.isdigit():
        addr = int(s, 10)
    else:
        if s not in ctx.name_to_addr:
            raise KeyError(f"unknown symbol: {s!r}")
        addr = ctx.name_to_addr[s]

    if size is None:
        # Look up by name if we can; otherwise distance to next code sym.
        owner = ctx.addr_to_name.get(addr)
        if owner and owner in ctx.name_to_size:
            size = ctx.name_to_size[owner]
        else:
            sorted_addrs = sorted(ctx.name_to_size)
            # Find nearest code symbol >= addr
            higher = [
                ctx.name_to_addr[n]
                for n in ctx.name_to_size
                if ctx.name_to_addr[n] > addr
            ]
            size = (min(higher) - addr) if higher else 64

    func_off = addr - ctx.code_base
    chunk = ctx.code[func_off : func_off + size]

    cs = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    lines: list[DisasmLine] = []
    for insn in cs.disasm(chunk, addr):
        rel = insn.address - addr
        target = None
        if (insn.mnemonic in ("call", "jmp")
                or insn.mnemonic.startswith("j")):
            target = _resolve_branch(ctx, insn.op_str)
        data_ref = _resolve_fixup(ctx, func_off, rel, insn.size)
        # If a branch target is also a fixup (e.g. cross-section call),
        # prefer the branch resolution.
        if target and data_ref == target:
            data_ref = None
        f, l = ctx.line_lookup.get(insn.address, ("", 0))
        lines.append(DisasmLine(
            address=insn.address, file=f, line=l,
            bytes_=insn.bytes, mnemonic=insn.mnemonic,
            op_str=insn.op_str, target=target, data_ref=data_ref,
        ))

    return addr, size, lines


# `dword ptr ` is the implicit default for 32-bit register / 4-byte
# memory ops in 32-bit code -- always redundant.  Strip it for compact
# output.  Keep `byte ptr` and `word ptr` because those carry width
# info that the mnemonic+register alone would not disambiguate.
_DWORD_PTR_RE = re.compile(r"\bdword ptr ")


def format_disasm_line(
    ln: DisasmLine, *, show_bytes: bool = True, show_lines: bool = True,
    simplify: bool = True,
) -> str:
    """Format one disassembly line.

    `simplify=True` (default) strips redundant `dword ptr ` qualifiers
    from operand strings.  Pass `simplify=False` to keep capstone's raw
    output verbatim.
    """
    parts = [f"{ln.address:08X}"]
    if show_lines:
        parts.append(f"L{ln.line}" if ln.line else "    ")
    if show_bytes:
        parts.append(ln.bytes_.hex().ljust(20))
    parts.append(ln.mnemonic)
    op_str = _DWORD_PTR_RE.sub("", ln.op_str) if simplify else ln.op_str
    parts.append(op_str)
    note_parts = []
    if ln.target:
        note_parts.append(f"→ {ln.target}")
    if ln.data_ref:
        note_parts.append(f"[{ln.data_ref}]")
    line = "  ".join(parts)
    if note_parts:
        line += "    " + " ".join(note_parts)
    return line


# ── CLI ───────────────────────────────────────────────────────────────────

def _trailing_next_module_table(
    ctx: "_Ctx", addr: int, size: int, lines: list[DisasmLine],
) -> tuple[list[DisasmLine], int, Optional[str]]:
    """Split off a trailing NEXT-module switch/scan table from the disasm.

    ``symbols.json`` has no size field: each function's extent is derived as
    the distance to the next code symbol.  Watcom emits a function's switch /
    scan tables *just before* that function's entry label, so the LAST
    function of a module absorbs the leading tables of the NEXT module's first
    function into its computed extent (worked example: ``stop_system`` ->
    ``sim_mouse``).  Those bytes are DATA -- disassembling them yields garbage.

    Detect a fixup-bearing table sitting after the function's terminal
    ``ret`` / tail ``jmp`` and return ``(code_lines, table_bytes, next_name)``
    so the caller can render one annotation line instead of the garbage.
    Returns the input unchanged (``table_bytes == 0``) when there is no such
    table -- a normal function whose code runs to the next symbol.
    """
    if not lines:
        return lines, 0, None
    term_i = None
    for i, ln in enumerate(lines):
        if ln.mnemonic == "ret" or ln.mnemonic == "jmp":
            term_i = i
    if term_i is None or term_i >= len(lines) - 1:
        return lines, 0, None
    term = lines[term_i]
    tail_off = (term.address + len(term.bytes_)) - ctx.code_base
    end_off = (addr - ctx.code_base) + size
    # A real jump/scan table carries a loader fixup per 4-byte address entry;
    # require >= 2 so we never trim a lone stray fixup on real trailing code.
    fixup_hits = sum(1 for o in ctx.code_fixups if tail_off <= o < end_off)
    if fixup_hits < 2:
        return lines, 0, None
    nxt = ctx.addr_to_name.get(addr + size)
    nxt_name = nxt.rstrip("_") if nxt else None
    return lines[: term_i + 1], end_off - tail_off, nxt_name


def disasm(
    name: Annotated[
        str,
        typer.Argument(help="Function name or hex address (e.g. 'main' or '0x10010')"),
    ],
    size: Annotated[
        Optional[int],
        typer.Option("--size", "-n",
                     help="Override function size (bytes); default is distance to next code symbol"),
    ] = None,
    show_bytes: Annotated[
        bool,
        typer.Option("--bytes/--no-bytes",
                     help="Show raw instruction bytes"),
    ] = True,
    show_lines: Annotated[
        bool,
        typer.Option("--lines/--no-lines",
                     help="Show source line numbers from debug info"),
    ] = True,
    output: Annotated[
        Optional[Path],
        typer.Option("--output", "-o", help="Write to file instead of stdout"),
    ] = None,
    symbols_json: Annotated[
        Path,
        typer.Option("--symbols", help="Path to symbols.json"),
    ] = Path("data/out/symbols.json"),
    exe_path: Annotated[
        Path,
        typer.Option("--exe", help="Path to PS.EXE"),
    ] = Path("data/PS.EXE"),
) -> None:
    r"""Dump annotated disassembly of one PS.EXE function.

    Each line shows: address, source-line number (if known), instruction
    bytes, mnemonic, operands.  Branch instructions are annotated with
    the target symbol name; memory references show the symbol resolved
    via the LE fixup table.
    """
    try:
        addr, sz, lines = disasm_function(
            name, size=size,
            symbols_json=symbols_json, exe_path=exe_path,
        )
    except KeyError as e:
        typer.echo(f"error: {e}", err=True)
        raise typer.Exit(1)
    except FileNotFoundError as e:
        typer.echo(f"error: {e}", err=True)
        raise typer.Exit(1)

    # Split off a trailing next-module switch/scan table absorbed into this
    # function's derived extent (symbol-extent over-reach; see helper).  Only
    # when the size was not explicitly overridden.
    table_bytes = 0
    table_next = None
    if size is None:
        ctx = _build_ctx(symbols_json, exe_path)
        lines, table_bytes, table_next = _trailing_next_module_table(
            ctx, addr, sz, lines,
        )

    code_sz = sz - table_bytes
    hdr = f"=== {name} @ 0x{addr:X} ({code_sz} bytes) ==="
    if table_bytes:
        hdr += (f"   [+{table_bytes}b trailing {table_next or 'next-module'} "
                f"switch/scan table -- symbol-extent over-reach, elided]")
    out_lines = [hdr]
    out_lines.extend(
        format_disasm_line(ln, show_bytes=show_bytes, show_lines=show_lines)
        for ln in lines
    )
    if table_bytes:
        tbl_addr = addr + code_sz
        out_lines.append(
            f"          … {table_bytes} byte(s) of {table_next or 'next-module'}"
            f"'s switch/scan table at 0x{tbl_addr:X} (data, not this "
            f"function's code) …"
        )
    text = "\n".join(out_lines) + "\n"

    if output:
        output.write_text(text)
        typer.echo(f"wrote {output}", err=True)
    else:
        typer.echo(text, nl=False)


if __name__ == "__main__":
    typer.run(disasm)

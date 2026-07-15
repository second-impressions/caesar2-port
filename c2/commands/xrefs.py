"""xrefs command: cross-references for code or data symbols in PS.EXE.

Two modes:

  * Code xrefs (callers): ``c2 xrefs <function_name>`` lists every
    function that contains a ``call`` or ``jmp`` whose target is the
    given function.

  * Data xrefs: ``c2 xrefs <data_symbol>`` (or ``c2 xrefs +0xXX
    <symbol>`` for a struct-field offset) lists every function that
    reads or writes the data symbol (any instruction whose op_str
    references the symbol via an LE fixup or relative load).

The implementation walks every code symbol with ``disasm_function``
from ``c2.commands.disasm`` and inspects each instruction's ``target``
and ``data_ref`` fields.  This keeps the lookup fully consistent with
``c2 disasm``'s own annotation logic — branch targets are resolved
through the symbol table and data refs through the LE fixup table.

Examples::

    # Who calls this function?
    uv run c2 xrefs get_army_walk_dirc

    # Who reads/writes citizen_list[i].target_kind (field offset 0x2C)?
    uv run c2 xrefs citizen_list --field 0x2C

    # All usages of a global scalar
    uv run c2 xrefs map_direction
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Optional

import typer

from c2.commands.disasm import disasm_function, _build_ctx


def xrefs(
    target: Annotated[
        str,
        typer.Argument(help="Symbol name (function or data) to find xrefs for"),
    ],
    field: Annotated[
        Optional[str],
        typer.Option("--field", "-f",
                     help="Struct-field offset (hex or decimal) added to "
                          "the data symbol's address; matches references "
                          "to that exact byte position"),
    ] = None,
    show_addr: Annotated[
        bool,
        typer.Option("--addr/--no-addr",
                     help="Show the call/access site address per match"),
    ] = True,
    show_op: Annotated[
        bool,
        typer.Option("--op/--no-op",
                     help="Show the instruction mnemonic and operands"),
    ] = True,
    only: Annotated[
        Optional[str],
        typer.Option("--only",
                     help="Restrict to matches in callers whose name "
                          "contains this substring"),
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
    """List functions that reference the given symbol.

    Code targets get caller analysis (call/jmp xrefs).
    Data targets get reader/writer analysis (memory-operand xrefs).
    """
    ctx = _build_ctx(symbols_json, exe_path)

    if target not in ctx.name_to_addr:
        typer.echo(f"error: unknown symbol {target!r}", err=True)
        raise typer.Exit(1)

    sym = json.loads(symbols_json.read_text())
    target_sym = next((s for s in sym["symbols"] if s["name"] == target), None)
    if target_sym is None:
        typer.echo(f"error: {target!r} not in symbol table", err=True)
        raise typer.Exit(1)

    is_data = target_sym.get("is_data", False)

    # Build the matching predicate per mode.
    if is_data:
        # Match references to either the bare symbol or symbol+0xN.
        if field is not None:
            try:
                field_off = int(field, 0)
            except ValueError:
                typer.echo(f"error: --field must be hex or decimal, got {field!r}",
                           err=True)
                raise typer.Exit(1)
            wanted = f"{target}+0x{field_off:X}" if field_off else target
            mode = f"data field {target}+0x{field_off:X}"
        else:
            wanted = target
            mode = f"data symbol {target}"

        def matches(ln) -> bool:
            return ln.data_ref == wanted
    else:
        wanted = target
        mode = f"code symbol {target}"

        def matches(ln) -> bool:
            return ln.target == wanted

    # Walk every code function and collect hits.
    code_funcs = sorted(
        (s for s in sym["symbols"] if s.get("is_code")),
        key=lambda s: s["address"],
    )
    hits: list[tuple[str, int, str, str]] = []  # (caller, addr, mnem, op_str)
    for s in code_funcs:
        if s["name"] == target:
            continue
        if only and only not in s["name"]:
            continue
        try:
            _, _, lines = disasm_function(
                s["name"],
                symbols_json=symbols_json, exe_path=exe_path,
            )
        except (KeyError, ValueError):
            continue
        for ln in lines:
            if matches(ln):
                hits.append((s["name"], ln.address, ln.mnemonic, ln.op_str))

    if not hits:
        typer.echo(f"no xrefs for {mode}")
        raise typer.Exit(0)

    typer.echo(f"=== {len(hits)} xref(s) to {mode} ===")
    by_caller: dict[str, list[tuple[int, str, str]]] = {}
    for c, a, m, o in hits:
        by_caller.setdefault(c, []).append((a, m, o))
    name_w = max(len(c) for c in by_caller)
    for caller in sorted(by_caller):
        for a, m, o in by_caller[caller]:
            parts = [caller.ljust(name_w)]
            if show_addr:
                parts.append(f"0x{a:X}")
            if show_op:
                parts.append(f"{m} {o}")
            typer.echo("  " + "  ".join(parts))


if __name__ == "__main__":
    typer.run(xrefs)

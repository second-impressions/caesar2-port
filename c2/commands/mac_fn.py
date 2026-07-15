"""`c2 mac-fn` -- the Mac PPC source-shape oracle for single-function decomps.

The 1996 CW Pro 1 Mac builds compile the SAME C source un-scheduled and
without cross-function tail merges, and carry every function's name +
exact byte range via traceback tables (c2.macref).  During a recovery,
`c2 mac-fn <name>` prints a statement-level readable PPC rendition of
the original function: arm structure, goto-convergence points, table
indexing and constants read straight off the listing.

Validated: devolve/evolve_a_building -- the Mac disasm reproduces the
recovered goto/do_call source shape line for line (and showed Mac
evolve carries NO 0x5DF block, independently confirming the recovery).

Usage:
    c2 mac-fn devolve_a_building            # French retail (default)
    c2 mac-fn get_tb_value --build demo     # demo build
    c2 mac-fn --grep '^forum_'              # name search
    c2 mac-fn pos_sound --bytes             # opcodes alongside
    c2 mac-fn sail_to_target --both         # FR + demo side info
"""
from __future__ import annotations

import typer

from c2 import macref


def mac_fn(
    name: str = typer.Argument(None, help="function name (PC symbol name)"),
    build: str = typer.Option("fr", "--build", help="fr (retail, 1575 fns) "
                              "or demo (1309 fns)"),
    grep: str = typer.Option(None, "--grep", help="regex-search the name "
                             "index instead of disassembling"),
    with_bytes: bool = typer.Option(False, "--bytes",
                                    help="show raw opcodes"),
    both: bool = typer.Option(False, "--both",
                              help="also report the other build's range"),
    rebuild_toc_map: bool = typer.Option(
        False, "--rebuild-toc-map",
        help="re-derive the TOC->PC-global-name map (co-occurrence over "
             "both corpora; ~1 min) and exit"),
) -> None:
    """Disassemble a named function from the Mac reference binaries."""
    if rebuild_toc_map:
        tm = macref.build_toc_map(build)
        typer.secho(f"# toc map rebuilt: {len(tm)} slots -> "
                    f"{macref._toc_map_path(build)}", fg="green")
        return
    if grep:
        b = macref.get(build)
        hits = b.grep(grep)
        typer.secho(f"# {len(hits)} match(es) in {build} "
                    f"({len(b.index)} functions)", fg="cyan")
        for nm in hits:
            s, e = b.by_name[nm]
            typer.echo(f"  {nm:42s} {e - s:6d}b")
        return
    if not name:
        typer.secho("name or --grep required", fg="red")
        raise typer.Exit(1)

    b = macref.get(build)
    rng = b.lookup(name)
    if rng is None:
        near = b.grep(name)[:8]
        typer.secho(f"[!] {name!r} not in {build} index", fg="red")
        if near:
            typer.echo("    near: " + ", ".join(near))
        other = "demo" if build == "fr" else "fr"
        try:
            if macref.get(other).lookup(name):
                typer.secho(f"    -> present in --build {other}", fg="yellow")
        except FileNotFoundError:
            pass
        raise typer.Exit(1)

    s, e = rng
    typer.secho(f"# {name}  [{build}]  code+{s:#x}..{e:#x}  ({e - s} bytes, "
                f"{(e - s) // 4} ins)", fg="cyan", bold=True)
    if both:
        other = "demo" if build == "fr" else "fr"
        try:
            r2 = macref.get(other).lookup(name)
            typer.echo(f"# {other}: " +
                       (f"{r2[1] - r2[0]} bytes" if r2 else "absent"))
        except FileNotFoundError:
            typer.echo(f"# {other}: not extracted")
    typer.echo(b.disasm(name, with_bytes=with_bytes))

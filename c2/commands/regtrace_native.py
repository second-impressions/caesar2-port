"""c2 regtrace-native — the real allocator's decisions for a function, via the
instrumented compiler image (no QEMU, no breakpoints).

Compiles the whole real TU containing ``<func>`` under the
``localhost/watcom-10.0a-wibo-trace`` image (byte-identical .obj to the
verifier) and reads the ``~WV1`` register-allocation trace from stdout: per
conflict, its **savings**, register class, and the **assigned register** -- the
piece the QEMU ``c2 regtrace`` could not capture.

    uv run c2 regtrace-native move_army
    uv run c2 regtrace-native move_army --file int_c2.c --json

This is the podman-native counterpart to ``c2 regtrace`` and shares the proven
PS.EXE flags. The H2 self-check confirms our offline ShellSort reproduces the
real order (so a divergence can be reasoned about offline). See
``c2.regalloc`` and the watcom10.0a RE repo (docs/verification.md).
"""
from __future__ import annotations

import json as _json

import typer

from c2 import regalloc
from c2.commands.regtrace import _find_function, INCLUDE_DIR, _ANNOT


def regtrace_native(
    name: str = typer.Argument(..., help="function to trace"),
    file: str = typer.Option(None, "--file", help="source file to disambiguate"),
    cflags: str = typer.Option(regalloc.PS_CFLAGS, "--cflags", help="compiler flags"),
    json_out: bool = typer.Option(False, "--json", help="emit raw JSON only"),
    tu: bool = typer.Option(False, "--tu", help="compile the whole TU (all routines) instead of a target-only snippet"),
    all_routines: bool = typer.Option(False, "--all", help="show every routine, not just the target"),
):
    """Trace the live 10.0a allocator for a function via the trace image.

    Also available as ``c2 regtrace <fn> --native`` (same engine)."""
    run_native(name, file=file, cflags=cflags, json_out=json_out, tu=tu,
               all_routines=all_routines)


def run_native(name, *, file=None, cflags=regalloc.PS_CFLAGS, json_out=False,
               tu=False, all_routines=False):
    """Core of the native trace (callable -- shared by ``c2 regtrace-native``
    and ``c2 regtrace --native``)."""
    src_file, start, end, preamble = _find_function(name, file)
    full = src_file.read_text(errors="replace")
    if tu:
        files = {"TARGET.C": full}            # byte-faithful but routines aren't name-attributed
    else:
        lines = full.splitlines()
        body = "\n".join(lines[start - 1:end]) + "\n"
        # Target-ONLY snippet: file preamble (includes + file-level decls) + just
        # this function. Callees get their prototypes from the headers, so codegen
        # matches the full-TU build (Rule 37) and the trace holds exactly this
        # routine. (If a callee has NO visible prototype the snippet can diverge;
        # use --tu to cross-check, or rely on decomp-verify for byte-equality.)
        files = {"TARGET.C": preamble + "\n" + body}
    for h in INCLUDE_DIR.glob("*.h"):
        files[h.name.upper()] = h.read_text(errors="replace")

    td = regalloc.trace_compile(files, cflags=cflags, main="TARGET.C")

    key = name if name in td["by_func"] else name.rstrip("_")
    target = td["by_func"].get(key)
    if target is None and not tu and len(td["routines"]) == 1:
        target = td["routines"][0]

    if json_out:
        out = dict(td)
        out.pop("stdout", None)
        out["target_func"] = key
        typer.echo(_json.dumps(out, indent=2))
        return

    cm = td["cost_model"]
    typer.secho(f"# regtrace-native {name}  (image {regalloc.TRACE_IMAGE})", fg="cyan", bold=True)
    typer.echo(f"flags: {cflags}")
    typer.echo(f"cost model: " + " ".join(f"{k}={v}" for k, v in cm.items())
               + f"   loop_base(W)={td['loop_base']}")
    typer.echo(f"routines: {len(td['routines'])}   "
               f"functions: {td['func_order']}   target: {key}")

    def show(routine, label):
        ok = regalloc.reproduce_order(routine)
        typer.secho(f"\n{label}: {len(routine['alloc'])} allocations "
                    f"(H2 offline-reproduce: {'OK' if ok else 'MISMATCH'})",
                    fg="green" if ok else "red", bold=True)
        typer.echo(f"  {'savings':>7}  {'class':>5}  {'kind':>9}  {'reg':>4}  range")
        for a in routine["alloc"]:
            reg = a["reg_name"] or "(spill)"
            typer.echo(f"  {a['savings']:>7}  {a['regclass_name']:>5}  "
                       f"{(a['nameclass_name'] or '?'):>9}  {reg:>4}  "
                       f"{a['first']}..{a['last']}")

    if all_routines or target is None:
        if target is None:
            typer.secho(f"\n(could not attribute {key!r} by source order; showing all)",
                        fg="yellow")
        for r in td["routines"]:
            who = next((n for n, rr in td["by_func"].items() if rr is r), f"routine[{r['index']}]")
            show(r, who)
    else:
        show(target, key)

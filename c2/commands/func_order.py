"""func-order command: verify that functions in each decomp/src/*.c file
appear in the SAME order as they are laid out in PS.EXE.

Watcom emits functions into the object/TU in source order, and several
codegen effects depend on that order — most importantly the compiler's
*cross-function tail-merge* (a later function whose epilogue is byte-
identical to an earlier function's tail is rewritten to `jmp` into that
earlier tail; the donor MUST precede the dependent).  See
docs/CODEGEN-RESIDUE study + AGENTS.md Rule 42.

PS.EXE's per-TU function order is recoverable from symbols.json: each
code symbol carries a ``module_index`` (its translation unit) and an
``address``.  Sorting a TU's code symbols by address reproduces the
original source order of that .c file.  This tool compares that against
the actual function-definition order in decomp/src/<tu>.c (parsed with
the project's pycparser front-end, not regex).

    uv run c2 func-order                 # check every .c file
    uv run c2 func-order --file map.c    # one file
    uv run c2 func-order --json          # machine-readable
    uv run c2 func-order -v              # show the full expected order

Exit status is non-zero if any file is misordered, so it doubles as a
CI / pre-refactor guard.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Annotated

import typer

from c2.commands.c_source import classify_source


def _tu_basename(full_path: str) -> str:
    """basename of a DOS path like 'D:\\C2\\CODE\\MAP.C' -> 'map.c'."""
    return os.path.basename(full_path.replace("\\", "/")).lower()


def _ps_addr_by_tu(symbols_json: Path) -> dict[str, dict[str, int]]:
    """Return {tu_basename: {func_name: PS address}}.

    Only code symbols, only non-static (statics are invisible at -d1 and
    cannot be ordered), grouped by their owning translation unit.  The
    address — not a positional rank — is the ordering key, so that
    functions PS folds to a SINGLE address (identical-code-folded
    aliases, e.g. the empty `c3 ret` demo hooks all at 0x713CE) form an
    unordered equivalence class instead of being tie-broken arbitrarily.
    """
    sym = json.loads(symbols_json.read_text())
    mod_path = {sf["module_index"]: sf.get("full_path", "")
                for sf in sym.get("source_files", [])}
    by_tu: dict[str, dict[str, int]] = {}
    for s in sym["symbols"]:
        if not s.get("is_code"):
            continue
        if s.get("is_static"):
            continue
        fp = mod_path.get(s.get("module_index"), "")
        if not fp:
            continue
        tu = _tu_basename(fp)
        if not tu.endswith(".c"):
            continue
        by_tu.setdefault(tu, {})[s["name"]] = s["address"]
    return by_tu


def _src_func_order(c_file: Path) -> list[str]:
    """Function-definition names in source order, via pycparser."""
    decls = classify_source(c_file.read_text(errors="replace"), str(c_file))
    return [fd.decl.name for fd in decls.func_defs]


def _moved_code_names() -> set[str]:
    """Functions with the Rule 125 moved-code signature (zero -d1 line
    records): the peephole optimizer relocated their body (CallRet +
    StraightenCode haul / CloneCode), so their SYMBOL address does not
    reflect their source-definition position.  These are legitimate
    address-order exceptions — e.g. ``helping`` (action.c) must be
    defined after ``act_about`` even though its symbol precedes it.
    See c2/commands/moved_code_hints.py."""
    try:
        from c2.commands.moved_code_hints import scan_all

        return {h.name for h in scan_all()}
    except Exception:
        return set()


def _violations(addr_of: dict[str, int],
                src_order: list[str],
                exempt: set[str] | None = None,
                ) -> list[tuple[str, int, str, int]]:
    """Find source functions that appear BEFORE an earlier-addressed one.

    The source function order, mapped to PS addresses, must be
    monotonically non-decreasing.  Functions sharing an address (folded
    aliases) may appear in any relative order — only a strict address
    inversion (a function whose PS address is LESS than the max address
    seen so far in source order) is a real misordering.

    Functions in ``exempt`` (Rule 125 moved-code) are skipped entirely:
    their symbol address is an optimizer artifact, not a source
    position.

    Returns (name, addr, prev_name, prev_addr) for each violation.
    """
    out: list[tuple[str, int, str, int]] = []
    exempt = exempt or set()
    seq = [(n, addr_of[n]) for n in src_order
           if n in addr_of and n not in exempt]
    max_addr = -1
    max_name = ""
    for name, addr in seq:
        if addr < max_addr:
            out.append((name, addr, max_name, max_addr))
        else:
            max_addr, max_name = addr, name
    return out


def func_order(
    symbols_json: Annotated[
        Path,
        typer.Option("--symbols", help="Path to symbols.json"),
    ] = Path("data/out/symbols.json"),
    src_dir: Annotated[
        Path,
        typer.Option("--src", help="Directory of decomp .c files"),
    ] = Path("decomp/src"),
    file: Annotated[
        str | None,
        typer.Option("--file", "-f", help="Check only this .c file (basename)"),
    ] = None,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Print the full PS order for misordered files"),
    ] = False,
    as_json: Annotated[
        bool,
        typer.Option("--json", help="Emit JSON"),
    ] = False,
) -> None:
    if not symbols_json.exists():
        typer.echo(f"error: {symbols_json} not found", err=True)
        raise typer.Exit(2)
    if not src_dir.exists():
        typer.echo(f"error: {src_dir} not found", err=True)
        raise typer.Exit(2)

    ps_addr = _ps_addr_by_tu(symbols_json)
    moved = _moved_code_names()

    targets = sorted(src_dir.glob("*.c"))
    if file:
        want = file.lower()
        targets = [p for p in targets if p.name.lower() == want]
        if not targets:
            typer.echo(f"error: {file} not found in {src_dir}", err=True)
            raise typer.Exit(2)

    report: list[dict] = []
    for c_file in targets:
        tu = c_file.name.lower()
        addr_of = ps_addr.get(tu)
        if not addr_of:
            continue  # no PS symbols attributed to this TU
        try:
            actual = _src_func_order(c_file)
        except Exception as e:  # parse failure — report, don't crash the sweep
            report.append({"file": tu, "error": f"parse: {e}",
                           "inversions": [], "n_common": 0})
            continue
        # ICF equivalence classes: any PS address shared by >=2 code symbols
        # is a folded-alias / fall-through-pinned class whose member
        # addresses are a PLACEMENT artifact, not a source position (e.g.
        # gloop_end+mloop_end at 0x3D9DF, pinned after just_idle's tail-call
        # fall-through; mloop_end/year_end are dead ICF twins).  Their source
        # position is free, so they must not constrain the address-monotone
        # check (Watcom decouples placement from source order here).
        _addr_count: dict[int, int] = {}
        for _a in addr_of.values():
            _addr_count[_a] = _addr_count.get(_a, 0) + 1
        icf = {n for n, a in addr_of.items() if _addr_count[a] > 1}
        viol = _violations(addr_of, actual, exempt=moved | icf)
        common = [n for n in actual if n in addr_of]
        ps_sorted = sorted(addr_of, key=lambda n: (addr_of[n], n))
        report.append({
            "file": tu,
            "n_common": len(common),
            "n_ps": len(addr_of),
            "inversions": [
                {"name": n, "addr": f"{a:#x}",
                 "after": pn, "after_addr": f"{pa:#x}"}
                for n, a, pn, pa in viol
            ],
            "ps_order": ps_sorted if verbose else None,
        })

    bad = [r for r in report if r["inversions"] or r.get("error")]

    if as_json:
        typer.echo(json.dumps(
            {"files": report, "misordered": len(bad),
             "checked": len(report)}, indent=2))
        raise typer.Exit(1 if bad else 0)

    for r in sorted(report, key=lambda r: -len(r["inversions"])):
        if r.get("error"):
            typer.echo(f"  ⚠️  {r['file']:<16} {r['error']}")
            continue
        if not r["inversions"]:
            continue
        typer.echo(f"  ✗  {r['file']:<16} {len(r['inversions'])} misordered "
                   f"(of {r['n_common']} common, {r['n_ps']} in PS)")
        for inv in r["inversions"]:
            typer.echo(f"        {inv['name']!r} ({inv['addr']}) appears after "
                       f"{inv['after']!r} ({inv['after_addr']}) — should precede it")
        if verbose and r.get("ps_order"):
            typer.echo("        PS order: " + ", ".join(r["ps_order"]))

    ok = len(report) - len(bad)
    typer.echo(f"\nfunc-order: {ok}/{len(report)} files match PS layout"
               + (f"; {len(bad)} misordered" if bad else "  ✓"))
    raise typer.Exit(1 if bad else 0)

"""stubs command: rank STUB-annotated functions by caller pressure.

Triage tool for picking the next decomp target.  Walks every code
function in PS.EXE, counts how many ``call``/``jmp`` instructions
target each stub, and prints a leaderboard sorted by caller count.

Higher caller count = higher leverage: turning that one stub into
a real C body (or even just pinning a canonical signature) unblocks
every site that references it.

Examples::

    # Top 20 stubs by caller count.
    uv run c2 stubs

    # Top 50 small (≤200 b) stubs — best leverage-per-effort ratio.
    uv run c2 stubs --max-size 200 --limit 50

    # Stubs in lib32.c only.
    uv run c2 stubs --file lib32

    # JSON for further processing.
    uv run c2 stubs --json
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Annotated, Optional

import typer

from c2.commands.disasm import disasm_function, _build_ctx
from c2.commands.tail_merge import scan_tail_merge_donor


# Regex: ``// STUB: C2 0xADDR`` annotation.  Matches the exact form
# emitted by ``c2 decomp``.
_STUB_RE = re.compile(r"^//\s*STUB:\s*\w+\s+0x([0-9A-Fa-f]+)", re.MULTILINE)


def _collect_stub_addrs(src_dir: Path) -> dict[int, str]:
    """Walk decomp/src/*.c and return ``{address_int: source_filename}``
    for every ``// STUB:`` annotation.  An address present in multiple
    files (rare but possible for aliased function bodies) is recorded
    against the first file the scanner sees.
    """
    addrs: dict[int, str] = {}
    for f in sorted(src_dir.glob("*.c")):
        txt = f.read_text(errors="replace")
        for m in _STUB_RE.finditer(txt):
            a = int(m.group(1), 16)
            addrs.setdefault(a, f.name)
    return addrs


def _function_size(code_sorted: list[dict], idx: int) -> int:
    """Approximate function size = next code symbol's address minus
    this one's.  Caesar II's symbol table has back-to-back code so
    this matches the actual byte size for all but the very last
    function in a section.
    """
    if idx + 1 < len(code_sorted):
        return max(0, code_sorted[idx + 1]["address"] - code_sorted[idx]["address"])
    return 0


def stubs(
    limit: Annotated[
        int,
        typer.Option("--limit", "-n",
                     help="Show top N stubs (use 0 for all)."),
    ] = 30,
    min_callers: Annotated[
        int,
        typer.Option("--min-callers",
                     help="Only stubs with at least N callers."),
    ] = 1,
    max_size: Annotated[
        Optional[int],
        typer.Option("--max-size",
                     help="Only stubs whose body is at most N bytes "
                          "(good triage filter: small + many callers = "
                          "highest leverage-per-effort)."),
    ] = None,
    file_filter: Annotated[
        Optional[str],
        typer.Option("--file",
                     help="Restrict to stubs in source files whose "
                          "filename contains this substring."),
    ] = None,
    name_filter: Annotated[
        Optional[str],
        typer.Option("--name",
                     help="Restrict to stubs whose name contains "
                          "this substring."),
    ] = None,
    donors: Annotated[
        bool,
        typer.Option("--donors",
                     help="Rank stubs by tail-merge dependents "
                          "(Rule 15/42) instead of caller count.  "
                          "Each dependent is a function whose last "
                          "instruction is a near jmp INTO the stub's "
                          "body \u2014 decompiling the donor will "
                          "flip those dependents byte-exact for free "
                          "once the shared epilogue matches."),
    ] = False,
    show_deps: Annotated[
        bool,
        typer.Option("--show-deps",
                     help="With --donors, list dependent function "
                          "names under each donor row."),
    ] = False,
    include_decompiled: Annotated[
        bool,
        typer.Option("--include-decompiled",
                     help="With --donors, also list donors whose body "
                          "is already decompiled (audit mode).  "
                          "Default lists only stubs (next decomp "
                          "targets)."),
    ] = False,
    as_json: Annotated[
        bool,
        typer.Option("--json", help="Emit JSON instead of a text table."),
    ] = False,
    src_dir: Annotated[
        Path,
        typer.Option("--src", help="Decomp source directory."),
    ] = Path("decomp/src"),
    symbols_json: Annotated[
        Path,
        typer.Option("--symbols", help="Path to symbols.json."),
    ] = Path("data/out/symbols.json"),
    exe_path: Annotated[
        Path,
        typer.Option("--exe", help="Path to PS.EXE."),
    ] = Path("data/PS.EXE"),
) -> None:
    """Rank STUB-annotated functions by caller count for triage.

    The output table answers "which stub, if I decompiled it next,
    would unblock the most callers?"  Combine with ``--max-size`` to
    bias toward small bodies that are quick wins.

    With ``--donors``, ranks stubs by **tail-merge dependents**
    instead: each row's `deps` column counts functions whose last
    instruction is an unconditional jmp INTO the stub's body
    (Rule 15/42 cross-function tail-merge).  Decompiling such a
    donor will flip every dependent byte-exact for free, once the
    donor's epilogue matches the dependents' shared tail \u2014 a
    2-15\u00d7 multiplier vs ranking by caller count.
    """
    if donors:
        _run_donors_mode(
            limit=limit,
            max_size=max_size,
            file_filter=file_filter,
            name_filter=name_filter,
            show_deps=show_deps,
            include_decompiled=include_decompiled,
            as_json=as_json,
            src_dir=src_dir,
            symbols_json=symbols_json,
            exe_path=exe_path,
        )
        return

    # 1. Find stub addresses + their source file.
    stub_addrs = _collect_stub_addrs(src_dir)
    if not stub_addrs:
        typer.echo("no STUB annotations found", err=True)
        raise typer.Exit(1)

    # 2. Load symbol table; map stub addresses → names.
    sym = json.loads(symbols_json.read_text())
    code_sorted = sorted(
        (s for s in sym["symbols"] if s.get("is_code")),
        key=lambda s: s["address"],
    )
    addr_to_idx = {s["address"]: i for i, s in enumerate(code_sorted)}

    stub_records: list[dict] = []
    for addr, src_file in stub_addrs.items():
        idx = addr_to_idx.get(addr)
        if idx is None:
            continue  # stub address not in symbol table (shouldn't happen)
        s = code_sorted[idx]
        stub_records.append({
            "name":    s["name"],
            "address": addr,
            "size":    _function_size(code_sorted, idx),
            "file":    src_file,
        })

    # 3. Walk all code functions once; count call-target frequency.
    #    `disasm_function` resolves branch targets via the symbol table,
    #    so `ln.target` is the symbolic name we want to count.
    _ = _build_ctx(symbols_json, exe_path)  # warm caches once

    callers: Counter[str] = Counter()
    for s in code_sorted:
        try:
            _, _, lines = disasm_function(
                s["name"],
                symbols_json=symbols_json, exe_path=exe_path,
            )
        except (KeyError, ValueError):
            continue
        for ln in lines:
            if ln.target:
                callers[ln.target] += 1

    # 4. Annotate each stub with its caller count and apply filters.
    for r in stub_records:
        r["callers"] = callers.get(r["name"], 0)

    if min_callers > 0:
        stub_records = [r for r in stub_records if r["callers"] >= min_callers]
    if max_size is not None:
        stub_records = [r for r in stub_records if 0 < r["size"] <= max_size]
    if file_filter:
        stub_records = [r for r in stub_records if file_filter in r["file"]]
    if name_filter:
        stub_records = [r for r in stub_records if name_filter in r["name"]]

    # 5. Sort: callers desc, then size asc (smaller = quicker win).
    stub_records.sort(key=lambda r: (-r["callers"], r["size"]))

    if limit > 0:
        stub_records = stub_records[:limit]

    if as_json:
        typer.echo(json.dumps({"stubs": stub_records}, indent=2))
        return

    if not stub_records:
        typer.echo("no stubs match the given filters")
        return

    # 6. Pretty table.  Column widths set just wide enough for the
    #    selected rows so the output stays narrow.
    name_w = max(4, max(len(r["name"]) for r in stub_records))
    file_w = max(4, max(len(r["file"]) for r in stub_records))

    header = (
        f"  {'callers':>7}  {'size':>5}  {'name':<{name_w}}  "
        f"{'file':<{file_w}}  address"
    )
    typer.echo(header)
    typer.echo("  " + "-" * (len(header) - 2))
    for r in stub_records:
        typer.echo(
            f"  {r['callers']:>7}  {r['size']:>5}  "
            f"{r['name']:<{name_w}}  {r['file']:<{file_w}}  "
            f"0x{r['address']:05X}"
        )

    # 7. Footer with totals (over the full unfiltered set).
    total_stubs = len(stub_addrs)
    typer.echo(
        f"\n  shown {len(stub_records)} of {total_stubs} stubs "
        f"({sum(r['callers'] for r in stub_records)} cumulative caller refs)"
    )


def _run_donors_mode(
    *,
    limit: int,
    max_size: Optional[int],
    file_filter: Optional[str],
    name_filter: Optional[str],
    show_deps: bool,
    include_decompiled: bool,
    as_json: bool,
    src_dir: Path,
    symbols_json: Path,
    exe_path: Path,
) -> None:
    """Implementation of ``c2 stubs --donors``.

    Walks every code function and uses ``scan_tail_merge_donor`` from
    ``c2.commands.tail_merge`` to detect Rule 15/42 tail-jmp sites.
    Aggregates by donor and ranks by ``len(dependents)`` then donor
    size (smaller = quicker decomp).  Filters to stub donors by
    default since those are the actionable next-decomp targets.
    """
    # Stub set + symbol table (same as caller-count mode).
    stub_addrs = _collect_stub_addrs(src_dir)

    sym = json.loads(symbols_json.read_text())
    code_sorted = sorted(
        (s for s in sym["symbols"] if s.get("is_code")),
        key=lambda s: s["address"],
    )
    addr_to_idx = {s["address"]: i for i, s in enumerate(code_sorted)}
    name_to_addr = {s["name"]: s["address"] for s in code_sorted}

    # Source-file lookup for donors.  Decompiled donors live in some
    # .c file; we extract their filenames from FUNCTION: annotations
    # so the ``file`` column matches the same source-of-truth as for
    # stubs.  Falls back to "<unknown>" if we can't find it.
    func_files: dict[int, str] = {}
    fn_re = re.compile(
        r"^//\s*FUNCTION:\s*\w+\s+0x([0-9A-Fa-f]+)", re.MULTILINE,
    )
    for f in sorted(src_dir.glob("*.c")):
        txt = f.read_text(errors="replace")
        for m in fn_re.finditer(txt):
            func_files.setdefault(int(m.group(1), 16), f.name)
        for m in _STUB_RE.finditer(txt):
            func_files.setdefault(int(m.group(1), 16), f.name)

    # Walk every function; for each, scan its tail for a donor jmp.
    # Aggregate by donor name.
    ctx = _build_ctx(symbols_json, exe_path)

    # Reuse the tail_merge module's scanner.  It needs the function's
    # raw bytes; we already have them in `ctx.code` indexed by
    # `addr - code_base`.
    code_bytes = ctx.code
    code_base = ctx.code_base

    donors_map: dict[str, dict] = {}
    for s in code_sorted:
        addr = s["address"]
        idx = addr_to_idx[addr]
        size = _function_size(code_sorted, idx)
        if size <= 0:
            continue
        off = addr - code_base
        chunk = code_bytes[off:off + size]
        hint = scan_tail_merge_donor(
            chunk, addr, is_vaddr=True,
            symbols_json=symbols_json,
            code_bytes=code_bytes, code_base=code_base,
        )
        if hint is None:
            continue
        d = donors_map.setdefault(
            hint.donor_name,
            {
                "name": hint.donor_name,
                "address": hint.donor_start,
                "size": 0,            # filled below
                "file": "",           # filled below
                "is_stub": False,     # filled below
                "deps": [],
            },
        )
        d["deps"].append({
            "name": s["name"],
            "address": addr,
            "size": size,
            "merge_offset": hint.merge_offset_in_donor,
            "tail_bytes": len(hint.tail_bytes),
        })

    # Annotate donors with size, file, and stub status.
    for d in donors_map.values():
        donor_addr = d["address"]
        donor_idx = addr_to_idx.get(donor_addr)
        if donor_idx is not None:
            d["size"] = _function_size(code_sorted, donor_idx)
        d["file"] = func_files.get(donor_addr, "<unknown>")
        d["is_stub"] = donor_addr in stub_addrs
        d["dep_count"] = len(d["deps"])
        d["blocked_bytes"] = sum(dep["size"] for dep in d["deps"])

    rows = list(donors_map.values())

    if not include_decompiled:
        rows = [r for r in rows if r["is_stub"]]
    if max_size is not None:
        rows = [r for r in rows if 0 < r["size"] <= max_size]
    if file_filter:
        rows = [r for r in rows if file_filter in r["file"]]
    if name_filter:
        rows = [r for r in rows if name_filter in r["name"]]

    # Sort: dep_count desc, then size asc (smaller donor = quicker win).
    rows.sort(key=lambda r: (-r["dep_count"], r["size"]))

    if limit > 0:
        rows = rows[:limit]

    if as_json:
        typer.echo(json.dumps({"donors": rows}, indent=2))
        return

    if not rows:
        typer.echo("no donor candidates match the given filters")
        return

    # Pretty table.
    name_w = max(4, max(len(r["name"]) for r in rows))
    file_w = max(4, max(len(r["file"]) for r in rows))

    header = (
        f"  {'deps':>4}  {'size':>5}  {'blkd':>5}  {'stub':>4}  "
        f"{'name':<{name_w}}  {'file':<{file_w}}  address"
    )
    typer.echo(header)
    typer.echo("  " + "-" * (len(header) - 2))
    for r in rows:
        stub_mark = "yes" if r["is_stub"] else "no"
        typer.echo(
            f"  {r['dep_count']:>4}  {r['size']:>5}  "
            f"{r['blocked_bytes']:>5}  {stub_mark:>4}  "
            f"{r['name']:<{name_w}}  {r['file']:<{file_w}}  "
            f"0x{r['address']:05X}"
        )
        if show_deps:
            for dep in sorted(r["deps"], key=lambda d: -d["size"]):
                typer.echo(
                    f"        \u21b3 {dep['name']:<{name_w}}  "
                    f"({dep['size']} b, merge +0x{dep['merge_offset']:X})"
                )

    # Footer.
    total_donors = len(donors_map)
    total_stub_donors = sum(1 for r in donors_map.values() if r["is_stub"])
    typer.echo(
        f"\n  shown {len(rows)} of "
        f"{total_stub_donors if not include_decompiled else total_donors} "
        f"donor candidates "
        f"({sum(r['dep_count'] for r in rows)} dependents, "
        f"{sum(r['blocked_bytes'] for r in rows)} blocked bytes)"
    )


if __name__ == "__main__":
    typer.run(stubs)

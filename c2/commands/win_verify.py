"""``c2 win-verify`` -- byte-verify the decomp source against CAESAR2.EXE.

The Windows analogue of ``c2 decomp-verify``.  ``decomp-verify`` builds the
tree with Watcom and compares against the DOS ``PS.EXE``; ``win-verify``
builds each TU with **MSVC 4.0 /Od** (the proven CAESAR2.EXE toolchain) and
compares each function against the Windows ``CAESAR2.EXE`` build -- a second,
independent byte oracle on the SAME source tree.

Two figures per function (mirroring the dual oracle/shape split in
``decomp-verify``):

* **byte_diff** -- the raw masked byte diff (the ORACLE; 0 ⇒ byte-exact).
* **struct_diff** -- mnemonic + reloc/displacement-normalised operand
  mismatches (the WORKABLE figure: /Od shuffles stack slots, so raw byte
  diff is noisy -- structural diff isolates real shape divergence).

A function is **exact** when its compiled bytes match somewhere in
``.text`` under DIR32/REL32 masking (map-independent, so a stale func-map
entry never yields a false diff).

Results are cached at ``.c2-cache/win-verify.json`` (whole-tree, incremental
on changed TUs, full rebuild when a header changes) -- the Win mirror of
``.c2-cache/verify.json``.  ``c2 decomp-verify --target win`` is the thin
front door that dispatches into this engine; both render from the same cache.

Usage::

    c2 win-verify                       # whole-tree summary (cached)
    c2 win-verify totalXpercent         # one function's verdict (cache-or-verify)
    c2 win-verify -v find_enemy         # + the structural PS-vs-RC asm diff
    c2 win-verify --file pcsound.c      # every decompiled function in a TU
    c2 win-verify --diffing             # only the not-yet-exact functions
    c2 win-verify --json                # structured {summary,files,functions}
    c2 win-verify --no-cache            # force a fresh MSVC build

See also: ``c2 win-decompile`` (Ghidra /Od source-shape oracle),
``c2 decomp-verify`` (the DOS byte oracle), and
``docs/windows-dual-target-feasibility.md``.
"""
from __future__ import annotations

from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.markup import escape

from c2 import win_bytes as wb
from c2 import win_verify_cache as wvc

console = Console()


# ── per-function diff view ────────────────────────────────────────────────────
def _print_diff(v: "wb.FuncVerdict") -> None:
    """Aligned MSVC-of-our-source vs CAESAR2.EXE (difflib insert/del/replace).

    Two tiers of divergence are coloured distinctly:
      [yellow]≠[/] structural  -- different mnemonic/addressing shape (real),
      [cyan]·[/]  slot/imm noise -- same shape, only a displacement/immediate
                  differs (the /Od stack-slot shuffle; usually not a source bug).
    """
    if v.win_va is None:
        return
    console.print(
        f"\n[bold]{v.name}[/]  ({v.size} B)   "
        f"[dim]OUR SOURCE via MSVC /Od  │  CAESAR2.EXE @ {v.win_va:#x} "
        f"(map: {v.confidence})[/]")
    _MARK = {"equal": ("  ", None), "slot": ("· ", "cyan"), "struct": ("≠ ", "yellow")}
    for row in wb.aligned_diff(v):
        oa, ta = escape(row["ours"]), escape(row["theirs"])
        mark, col = _MARK[row["kind"]]
        if col:
            console.print(f"  [{col}]{mark}{oa:<34}[/] │ [{col}]{ta}[/]", highlight=False)
        else:
            console.print(f"  {mark}{oa:<34} │ {ta}", highlight=False)


def _verdict_line(v: "wb.FuncVerdict") -> str:
    if v.status == "exact":
        return f"[green]✓[/] {v.name} — MSVC byte-exact vs CAESAR2.EXE ({v.size}b)"
    if v.status == "diff":
        return (f"[yellow]≠[/] {v.name} — diff: "
                f"{v.struct_diff}/{v.insn_total} struct  "
                f"[dim](win {v.win_va:#x}, map {v.confidence})[/]")
    if v.status == "nomap":
        return f"[dim]?[/] {v.name} — no CAESAR2.EXE mapping (compiles, {v.size}b)"
    return f"[red]·[/] {v.name} — no body in {v.tu}.c (stub / not decompiled)"


def _row_verdict_line(r: dict) -> str:
    """Same shape as ``_verdict_line`` but for a cache row (no rebuild)."""
    st = r["status"]
    name = r["name"]
    if st == "exact":
        return f"[green]✓[/] {name} — byte-exact vs CAESAR2.EXE ({r['size']}b)"
    if st == "diff":
        va = r.get("win_va")
        va_s = f"{va:#x}" if isinstance(va, int) else "?"
        return (f"[yellow]≠[/] {name} — diff: "
                f"{r['struct_diff']}/{r['insn_total']} struct  "
                f"[dim](win {va_s}, map {r.get('confidence','')})[/]")
    if st == "nomap":
        return f"[dim]?[/] {name} — no CAESAR2.EXE mapping"
    return f"[red]·[/] {name} — no body"


# ── shared renderer: cache-backed summary / file / diffing ─────────────────────
def run(function: Optional[str] = None,
       file: Optional[str] = None,
       verbose: bool = False,
       diffing: bool = False,
       json_out: bool = False,
       no_cache: bool = False,
       guards: bool = False,
       cb_tu=None) -> None:
    """Cache-backed ``win-verify`` entry point.

    Shared by the ``c2 win-verify`` command and ``c2 decomp-verify --target
    win``.  Resolves to cache rows for the project/`--file` views (rebuilding
    incrementally as needed); for a single function, uses the per-fn
    cache-or-verify path so a stale TU is rebuilt on demand."""
    if not wb.WIN_EXE.exists():
        console.print(f"[red]CAESAR2.EXE not found at {wb.WIN_EXE}[/]")
        raise typer.Exit(1)

    # ── single function: cache-or-verify, render verdict (+ optional diff) ──
    if function:
        tu = wb.tu_of(function)
        if tu is None:
            console.print(f"[red]no definition of {function!r} found in decomp/src[/]")
            raise typer.Exit(1)
        # If this TU is stale (or no_cache), refresh just it first.
        if no_cache:
            wvc.verify_tu(tu)
            wvc.refresh(force=True, cb=cb_tu)
        r = wvc.func_row_or_verify(function)
        if json_out:
            import json
            out = {**r, "diff_rows": _diff_rows_if_diff(function, r)}
            typer.echo(json.dumps(out, indent=1))
            return
        console.print(_row_verdict_line(r))
        if verbose and r["status"] == "diff":
            v = _verdict_from_row(r)
            if v is not None:
                _print_diff(v)
        return

    # ── file or whole tree: refresh the cache, render from rows ──────────────
    if no_cache:
        cache, _ = wvc.refresh(force=True, cb=cb_tu)
    else:
        cache, _ = wvc.refresh(cb=cb_tu)
    files = cache.get("files", {})
    rows = cache.get("functions", [])

    # ── Rule 158 sweep: folded-guard fingerprints across every win-diff ────
    if guards:
        _guard_sweep(rows, file, json_out)
        return

    if json_out:
        import json
        typer.echo(json.dumps(
            {"summary": cache.get("summary"), "files": files,
             "functions": rows}, indent=1))
        return

    target_tus: Optional[set[str]] = None
    if file:
        target_tus = {Path(file).stem}

    diff_rows = []
    tus_show = target_tus or set(files.keys())
    for tu in sorted(tus_show):
        f = files.get(tu, {})
        if f.get("failed_tu"):
            console.print(f"[red]✗ {tu}.c — MSVC compile failed:[/] {f.get('error','')}")
            continue
        tu_rows = [r for r in rows if r["tu"] == tu]
        fe = sum(1 for r in tu_rows if r["status"] == "exact")
        fd = sum(1 for r in tu_rows if r["status"] == "diff")
        fn = sum(1 for r in tu_rows if r["status"] == "nomap")
        if file:
            console.print(f"[bold]{tu}.c[/]: "
                          f"[green]{fe} exact[/], [yellow]{fd} diff[/], "
                          f"[dim]{fn} nomap[/]")
        for r in tu_rows:
            if r["status"] == "diff":
                diff_rows.append(r)
            if verbose and target_tus and r["status"] == "diff":
                v = _verdict_from_row(r)
                if v is not None:
                    _print_diff(v)

    if diffing or file:
        for r in sorted(diff_rows, key=lambda r: r["struct_diff"]):
            console.print("  " + _row_verdict_line(r))

    console.rule("[bold]win-verify summary")
    s = cache.get("summary", {})
    console.print(
        f"[green]{s.get('exact',0)} byte-exact vs CAESAR2.EXE[/]  ·  "
        f"[yellow]{s.get('diff',0)} diff[/]  ·  "
        f"[dim]{s.get('nomap',0)} no-map · {s.get('absent',0)} stub · "
        f"{s.get('failed_tu',0)} TU build-fail[/]  "
        f"[dim]({s.get('compared',0)} compared)[/]")
    if not file and not diffing:
        console.print("[dim]→ c2 win-verify --diffing  (workable list) · "
                      "-v <fn>  (structural diff) · c2 win-decompile <fn>  "
                      "(/Od source shape)[/]")


def _guard_sweep(rows: list[dict], file: Optional[str],
                 json_out: bool) -> None:
    """Corpus sweep for Rule 158 folded-guard fingerprints.

    Scans every win-DIFF function's aligned diff for one-sided
    zero-compare runs (see ``wb.guard_hits``) and cross-references the
    PS-side verify cache so still-PS-diffing hits (the actionable set)
    sort first.
    """
    import json as _json

    # PS-side status from verify.json (best effort).
    ps_diff: dict[str, int] = {}
    try:
        vj = _json.loads(Path(".c2-cache/verify.json").read_text())
        for fn_rec in vj.get("functions", []):
            ps_diff[fn_rec["name"]] = fn_rec.get("diff_byte_count", 0)
    except Exception:
        pass

    target = Path(file).stem if file else None
    hits_out = []
    scanned = 0
    for r in rows:
        if r.get("status") != "diff":
            continue
        if target and r.get("tu") != target:
            continue
        v = _verdict_from_row(r)
        if v is None:
            continue
        scanned += 1
        try:
            hs = wb.guard_hits(v)
        except Exception:
            continue
        for h in hs:
            hits_out.append({
                "name": r["name"], "tu": r["tu"], "side": h.side,
                "kind": h.kind, "insns": h.insns, "after": h.after,
                "ps_byte_diff": ps_diff.get(r["name"]),
            })
    hits_out.sort(key=lambda h: (h["ps_byte_diff"] is None,
                                 -(h["ps_byte_diff"] or 0)))
    if json_out:
        typer.echo(_json.dumps({"scanned": scanned, "hits": hits_out},
                               indent=1))
        return
    console.rule("[bold]Rule 158 folded-guard sweep")
    if not hits_out:
        console.print(f"[green]no folded-guard fingerprints[/] "
                      f"({scanned} win-diff function(s) scanned)")
        return
    for h in hits_out:
        ps = ("PS-exact" if h["ps_byte_diff"] == 0 else
              f"PS {h['ps_byte_diff']}bd" if h["ps_byte_diff"] is not None
              else "PS ?")
        arrow = ("ADD guard" if h["side"] == "theirs" else "REMOVE guard")
        console.print(
            f"[yellow]{h['name']}[/] ({h['tu']}.c, {ps})  {arrow}  "
            f"[{'; '.join(h['insns'])}]  before  "
            f"[dim]{'; '.join(h['after'])}[/]")
    console.print(f"[dim]{scanned} win-diff function(s) scanned; "
                  f"{len(hits_out)} hit(s).  side=theirs ⇒ the original "
                  "has an always-true guard Watcom folds (Rule 158) — add "
                  "`x >= 0 &&` (or the matching form) to the guarded "
                  "condition; still-PS-diffing functions first.[/]")


def _verdict_from_row(r: dict) -> Optional["wb.FuncVerdict"]:
    """Rebuild a FuncVerdict from a cache row for the verbose diff view."""
    if not wb.WIN_EXE.exists():
        return None
    tu = r.get("tu") or wb.tu_of(r["name"])
    if not tu:
        return None
    win = wb.load_win_image()
    ctu = wb.compile_tu(tu)
    fc = ctu.func_code(r["name"])
    if fc is None:
        return None
    code, mask = fc
    n = len(code)
    win_va = r.get("win_va")
    if not isinstance(win_va, int):
        return None
    wbytes = win.func_bytes(win_va, n)
    byte_diff = sum(1 for i in range(min(n, len(wbytes)))
                    if i not in mask and code[i] != wbytes[i]) + abs(n - len(wbytes))
    ours = wb.disasm_norm(code, mask)
    theirs = wb.disasm_norm(wbytes)
    struct_diff = wb._struct_distance([x[2] for x in ours], [x[2] for x in theirs])
    return wb.FuncVerdict(r["name"], tu, "diff", n, byte_diff, struct_diff,
                          len(ours), win_va, r.get("confidence", ""), win_va)


def _diff_rows_if_diff(name: str, r: dict) -> list[dict]:
    """Aligned diff rows for JSON output (only when the function diffs)."""
    if r.get("status") != "diff":
        return []
    v = _verdict_from_row(r)
    return wb.aligned_diff(v) if v is not None else []


# ── command ───────────────────────────────────────────────────────────────────
def win_verify(
    function: Annotated[Optional[str], typer.Argument(
        help="function to verify (omit for a file/tree summary)")] = None,
    file: Annotated[Optional[str], typer.Option(
        "--file", "-f", help="verify every decompiled function in this TU")] = None,
    verbose: Annotated[bool, typer.Option(
        "--verbose", "-v", help="show the structural asm diff for diffs")] = False,
    diffing: Annotated[bool, typer.Option(
        "--diffing", help="summary: list only the not-yet-exact functions")] = False,
    json_out: Annotated[bool, typer.Option(
        "--json", help="emit {summary,files,functions} (or one fn record) as "
                       "JSON on stdout; suppresses textual rendering")] = False,
    no_cache: Annotated[bool, typer.Option(
        "--no-cache", help="force a fresh MSVC build (no .c2-cache reuse)")] = False,
    guards: Annotated[bool, typer.Option(
        "--guards", help="Rule 158 sweep: scan every win-diff function for "
                         "folded always-true-guard fingerprints (one-sided "
                         "zero-compare runs in the aligned diff)")] = False,
) -> None:
    """Byte-verify decompiled functions against the Windows CAESAR2.EXE build."""
    run(function=function, file=file, verbose=verbose, diffing=diffing,
        json_out=json_out, no_cache=no_cache, guards=guards)

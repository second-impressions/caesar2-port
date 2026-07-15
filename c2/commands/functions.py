"""c2 functions -- categorized per-file function inventory.

For ONE decomp source file, lists which functions are byte-exact, which
still diff (sorted by byte_diff desc -- the 'drive to exact' targets),
which are STUBs (not yet decompiled), and which PS functions for the TU
are still MISSING entirely (never touched).

``c2 decomp-verify <file>`` lists the verified (exact/diffing) functions;
this adds the not-yet-done dimension (stub / missing) it only counts, so
you can drive a whole file to byte-exact from one view.

The structured core is ``functions_data()``; the Typer ``functions``
command renders it (or ``--json`` dumps it).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Optional

import typer

_SYMBOLS = Path("data/out/symbols.json")
_EXE = Path("data/PS.EXE")
_DECOMP = Path("decomp")


def _resolve_src(file: str, decomp: Path) -> Path:
    """Accept 'action', 'action.c', or 'decomp/src/action.c'."""
    p = Path(file)
    if p.exists() and p.suffix == ".c":
        return p
    name = p.name
    if not name.endswith(".c"):
        name += ".c"
    return Path(decomp) / "src" / name


# ── data core ────────────────────────────────────────────────────────────
def functions_data(
    file: str,
    *,
    status: Optional[str] = None,
    symbols: Path = _SYMBOLS,
    exe: Path = _EXE,
    decomp: Path = _DECOMP,
    win: bool = False,
) -> dict:
    """Categorized inventory of one decomp source file: exact / diffing /
    stub / missing.  ``status`` filters to one category.

    When ``win`` is set, also load the Windows (CAESAR2.EXE / MSVC /Od) cache
    and report the dual census: which PS-exact functions are ALSO
    byte-exact vs CAESAR2.EXE, and which PS-exact ones win-diff (the
    shape-recovery worklist -- /Od sees shape errors the Watcom byte oracle
    is blind to).  Populates ``win_status`` on each row + a ``shape_recovery``
    section + ``win_summary``.
    """
    # _run_verify (the structured decomp-verify projection) lives in
    # c2.toolapi; imported lazily.
    from c2.toolapi import _run_verify
    from c2.commands.decomp_verify import _parse_annotations
    from c2.commands.c_source import classify_source
    from c2.commands.func_order import _ps_addr_by_tu

    src = _resolve_src(file, Path(decomp))
    if not src.exists():
        return {"file": str(src), "found": False,
                "error": f"no such source file: {src}"}
    tu = src.name.lower()

    data = _run_verify(
        c_files=[src],
        symbols_json=Path(symbols),
        exe_path=Path(exe),
        decomp_dir=Path(decomp),
        function=None,
    )
    recs = data.get("functions", [])

    exact, diffing = [], []
    for rec in recs:
        bd = rec.get("diff_byte_count", 0) or 0
        _sd = rec.get("shape_distance") or {}
        row = {"name": rec.get("name"), "address": rec.get("address"),
               "size": rec.get("size"), "byte_diff": bd,
               "shape_cell": _shape_cell(_sd),
               "shape_total": _sd.get("total", 0),
               "fix_next": _sd.get("fix_next")}
        (exact if bd == 0 else diffing).append(row)
    # rank the diffing section by shape-distance (fix-next layer then total),
    # not byte count -- the per-function judge metric is shape, not bytes.
    _RANK = {"ir": 0, "width": 1, "spill": 2, "seat": 3}
    diffing.sort(key=lambda r: (_RANK.get(r.get("fix_next"), 9),
                                -int(r.get("shape_total", 0))))
    exact.sort(key=lambda r: r["name"] or "")

    # Names actually DEFINED in the source, AST-derived (immune to forward
    # decls).  Address-fold-safe: when several names fold to one address,
    # decomp-verify reports only one (dedup by address), but every sibling
    # has its own FuncDef here and must not read as missing.
    src_text = src.read_text(errors="replace")
    decls = classify_source(src_text, src.name)
    defined_names = {fd.decl.name for fd in decls.func_defs if fd.decl.name}

    # STUBs (annotated, not yet decompiled) -- addresses via the symbol map.
    sym = json.loads(Path(symbols).read_text())
    addr2name = {s["address"]: s["name"]
                 for s in sym["symbols"] if s.get("is_code")}
    _func_addrs, stub_addrs = _parse_annotations(src)
    stub = sorted(
        ({"name": addr2name.get(a, hex(a)), "address": a} for a in stub_addrs),
        key=lambda r: r["name"],
    )
    done_names = defined_names | {r["name"] for r in stub}

    # Addresses already covered by exact/diffing/stub, as ints.
    # decomp-verify resolves functions by ADDRESS (via `// FUNCTION: C2
    # 0xNNNN` annotations), so a PS symbol whose address is already
    # covered is NOT missing even when the name text differs -- notably
    # __cdecl symbols, which Watcom mangles with a leading `_` (source
    # `mood_modfication` -> symbol `_mood_modfication`).  A pure
    # name-text match would mis-flag those as missing.
    covered_addrs: set[int] = set()
    for rows in (exact, diffing, stub):
        for r in rows:
            a = r.get("address")
            if a is None:
                continue
            try:
                covered_addrs.add(int(a, 16) if isinstance(a, str) else int(a))
            except (TypeError, ValueError):
                pass

    # MISSING -- non-static PS functions for this TU not yet present at all.
    ps_names = _ps_addr_by_tu(Path(symbols)).get(tu, {})
    missing = sorted(
        ({"name": n, "address": a} for n, a in ps_names.items()
         if n not in done_names and int(a) not in covered_addrs),
        key=lambda r: r["name"],
    )

    cats = {"exact": exact, "diffing": diffing, "stub": stub, "missing": missing}
    result = {
        "file": str(src),
        "found": True,
        "counts": {k: len(v) for k, v in cats.items()},
        "summary": data.get("summary"),
    }

    # ── Windows dual census (--win) ──────────────────────────────────────
    # PS-exact functions that ALSO match CAESAR2.EXE are dual-verified;
    # PS-exact but win-diff are the shape-recovery worklist (the /Od oracle
    # sees shape errors the optimised-Watcom byte oracle is blind to):
    if win:
        from c2 import win_verify_cache as _wvc
        cache, _ = _wvc.refresh()      # incremental; only changed TUs build
        by_name = {r["name"]: r for r in cache.get("functions", [])}
        for r in (*exact, *diffing):
            w = by_name.get(r["name"])
            r["win_status"] = w["status"] if w else "absent"
            if w:
                r["win_struct_diff"] = w.get("struct_diff")
        shape_recovery = [
            {"name": r["name"], "address": r.get("address"),
             "win_struct_diff": r.get("win_struct_diff", 0),
             "win_va": by_name.get(r["name"], {}).get("win_va")}
            for r in exact if r.get("win_status") == "diff"
        ]
        win_exact = sum(1 for r in exact if r.get("win_status") == "exact")
        result["shape_recovery"] = shape_recovery
        result["win_summary"] = {
            "ps_exact": len(exact),
            "win_exact": win_exact,            # dual-verified
            "win_diff": len(shape_recovery),   # PS-exact, win-diff
        }

    if status:
        result[status] = cats.get(status, [])
    else:
        result.update(cats)
    return result


# ── renderer ─────────────────────────────────────────────────────────────
def _pad(s, n: int) -> str:
    s = s or ""
    return s if len(s) >= n else s + " " * (n - len(s))


def _shape_cell(sd: dict) -> str:
    """Compact per-fn shape-distance cell (`ir{N}/{T}[·i{K}][+k]→fix_next`)
    for the diffing table -- the per-function judge metric, in place of a
    byte count.  ``i{K}`` = run-ledger island count (``i0`` =
    regalloc_pure; absent = ledger unavailable)."""
    if not sd:
        return ""
    ir = sd.get("ir", 0); irt = sd.get("ir_total", 0)
    extra = sum(1 for L in ("width", "spill", "seat") if sd.get(L, 0))
    base = f"ir{ir}/{irt}" if irt else f"ir{ir}"
    if sd.get("islands") is not None:
        base += f"·i{sd['islands']}"
    if extra:
        base += f"+{extra}"
    return f"{base}→{sd.get('fix_next', '?')}"


def _render(r: dict, status: Optional[str], limit: int) -> None:
    if r.get("found") is False:
        typer.secho(f"{r['file']}: {r.get('error') or 'not found'}.", fg="yellow")
        return
    c = r["counts"]
    total = c["exact"] + c["diffing"] + c["stub"] + c["missing"]
    head = (f"{r['file']} -- {total} fn: {c['exact']} exact \u2713, "
            f"{c['diffing']} diffing \u2717, {c['stub']} stub, "
            f"{c['missing']} missing")
    if "win_summary" in r:
        ws = r["win_summary"]
        head += (f"  [win: {ws['win_exact']} dual-exact, "
                 f"{ws['win_diff']} PS-exact/win-diff]")
    typer.secho(head, bold=True)

    def section(label: str, rows, with_diff: bool) -> None:
        if not rows:
            return
        typer.echo(f"{label} ({len(rows)}):")
        for x in rows[:limit]:
            a = x.get("address")
            if isinstance(a, int):
                addr = f"0x{(a & 0xffffffff):x}"
            elif a:
                addr = str(a)
            else:
                addr = ""
            if with_diff:
                # 'diffing' rows show the shape cell; 'shape-recovery' rows
                # show the win struct-diff count instead.
                if "win_struct_diff" in x:
                    diffcol = _pad(f"win {x.get('win_struct_diff', 0)} struct", 16)
                else:
                    diffcol = _pad(str(x.get("shape_cell") or ""), 16)
            else:
                diffcol = ""
            typer.echo(f"  {_pad(x.get('name'), 32)}{diffcol} {addr}")
        if len(rows) > limit:
            typer.echo(f"  ... +{len(rows) - limit} more (use --json for all)")

    if status:
        section(status, r.get(status), status == "diffing")
    else:
        section("diffing -- drive these to exact", r.get("diffing"), True)
        section("stub -- not yet decompiled", r.get("stub"), False)
        section("missing -- never touched", r.get("missing"), False)
        if r.get("shape_recovery"):
            section("shape-recovery -- PS-exact, win-diff (c2 win-verify -v)",
                    r.get("shape_recovery"), True)
        if c["diffing"] == 0 and c["stub"] == 0 and c["missing"] == 0 \
                and not r.get("shape_recovery"):
            typer.secho("all functions byte-exact \u2713", fg="green")


# ── typer command ────────────────────────────────────────────────────────
def functions(
    file: Annotated[
        str,
        typer.Argument(help="Source file: 'action', 'action.c', or "
                            "'decomp/src/action.c'."),
    ],
    status: Annotated[
        Optional[str],
        typer.Option("--status", "-s",
                     help="Filter to one category: exact | diffing | stub | "
                          "missing."),
    ] = None,
    limit: Annotated[
        int,
        typer.Option("--limit", "-n", help="Max rows per category (default 25)."),
    ] = 25,
    as_json: Annotated[bool, typer.Option("--json")] = False,
    win: Annotated[
        bool,
        typer.Option("--win",
                     help="Also load the Windows (CAESAR2.EXE / MSVC /Od) "
                          "census and report dual-verified vs PS-exact/"
                          "win-diff (the shape-recovery worklist). Populates "
                          ".c2-cache/win-verify.json incrementally.")
    ] = False,
) -> None:
    """Categorized inventory of one decomp source file (exact / diffing /
    stub / missing) -- the 'drive this file to byte-exact' view."""
    data = functions_data(file, status=status, win=win)
    if as_json:
        typer.echo(json.dumps(data, default=str, indent=2))
        return
    _render(data, status, limit)

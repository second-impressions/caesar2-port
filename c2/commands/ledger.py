"""`c2 ledger` -- the dual ``-d1`` run ledger for one function.

Statement-level, REGISTER-BLIND PS-vs-RC comparison where each side is
segmented by its OWN -d1 line marks (PS.EXE's debug directory vs our
compile's line table).  No cross-side attribution through the byte-diff
alignment -- so the per-statement report stays exact no matter how large
the function is or how far the byte alignment drifts (the failure mode
that made per-line work impossible beyond ~400 bytes).

Reading the output:

* ``verdict: regalloc_pure``  -- every instruction matches register-blind.
  The WHOLE byte diff is register seats / encoding.  Do NOT restructure
  the source; go to ``c2 regtrace`` (and the seat/slot machinery).
* ``verdict: shape_islands``  -- each island is a LOCAL statement-shape
  divergence with exact dual line attribution: ``PS L<n>`` is the
  original source's -d1 line (the witness), ``<file>:<n>`` is OUR source
  line (the edit target).  Work islands top-down; each island's family
  tag names the lever:
    - ``width`` / ``zext-idiom``  -> a local's TYPE differs (char vs int;
      movzx / and 0xff / clear-first) -- Rules 49/49b/151
    - ``signedness``              -> signed vs unsigned local -- jl/jb twins
    - ``loop-form``               -> rotated (for) vs head-tested (while)
      loop -- Rules 134/93
    - ``slot``                    -> same ops, different [esp+N] slot --
      Rule 107 (often downstream; do not chase first)
    - ``frame``                   -> frame size differs -- local SET differs
    - ``const``                   -> an immediate differs -- const-audit
    - ``ops``                     -> genuinely different instructions --
      statement shape (read PS's ops; that IS the target shape)

The mark counts are the PACKING witness: PS marks < RC marks means the
original source packed more statements per physical line (byte-neutral;
never chase it for bytes).
"""

from __future__ import annotations

import bisect as _bisect
import json as _json
from pathlib import Path
from typing import Annotated, Optional

import typer

_SYMBOLS = Path("data/out/symbols.json")
_PS_EXE = Path("data/PS.EXE")


# ── data core ────────────────────────────────────────────────────────────
def ledger_data(
    function: str,
    *,
    symbols_json: Path = _SYMBOLS,
    ps_exe: Path = _PS_EXE,
    image: Optional[str] = None,
    with_insns: bool = True,
) -> dict:
    """Compute the dual-marks run ledger for ``function``.

    Builds (or reuses the cached) decomp compile, slices both sides'
    bytes + own-line-marks + fixups, and returns the JSON-able ledger
    plus location metadata.  Raises ``ValueError`` with a readable
    message when the function can't be resolved on either side.
    """
    from c2.commands.decomp_verify import (
        _build_all, _disasm_for_diff, _load_le_code_and_fixups, _parse_map,
        _DEFAULT_IMAGE, PS_CFLAGS,
    )
    from c2.commands.oracle import _load_oracle_line_lookup
    from c2.runledger import ledger_from_raw

    d = _json.loads(symbols_json.read_text())

    # ── PS side ──────────────────────────────────────────────────────
    code_syms = sorted(
        (s for s in d["symbols"] if s.get("is_code") and s["segment"] == 1),
        key=lambda s: s["offset"])
    matches = [s for s in code_syms
               if s.get("name") == function or s.get("raw_name") == function]
    if not matches:
        raise ValueError(f"{function!r} not found in PS code symbols")
    ps_sym = matches[0]
    ps_off = ps_sym["offset"]
    offs = [s["offset"] for s in code_syms]
    i = _bisect.bisect_right(offs, ps_off)
    ps_size = (offs[i] if i < len(offs) else ps_off + 0x4000) - ps_off

    ps_code, ps_fix = _load_le_code_and_fixups(ps_exe)
    ps_bytes = ps_code[ps_off:ps_off + ps_size]
    ps_marks = {ln["offset"] - ps_off: ln["line"]
                for ln in d["line_numbers"]
                if ps_off <= ln["offset"] < ps_off + ps_size}
    ps_fix_rel = {f - ps_off for f in ps_fix if ps_off <= f < ps_off + ps_size}

    # ── RC side (cached build) ───────────────────────────────────────
    ok, build_output, work, out_exe, out_map = _build_all(
        Path("decomp/src"), Path("decomp/include"),
        image or _DEFAULT_IMAGE, PS_CFLAGS, use_cache=True,
    )
    if not ok:
        raise ValueError("build failed:\n" + build_output)
    rc_code, rc_fix = _load_le_code_and_fixups(out_exe)
    rc_map = _parse_map(out_map)
    raw = function if function.endswith("_") else function + "_"
    if raw not in rc_map and function not in rc_map:
        raise ValueError(
            f"{function!r} not in the recompile map (stub / not decompiled?)")
    rc_off = rc_map.get(raw, rc_map.get(function))
    rc_offs = sorted(set(rc_map.values()))
    j = _bisect.bisect_right(rc_offs, rc_off)
    rc_size = (rc_offs[j] if j < len(rc_offs) else rc_off + 0x4000) - rc_off
    rc_bytes = rc_code[rc_off:rc_off + rc_size]
    rc_line_map = _load_oracle_line_lookup(out_exe)
    rc_marks = {off - rc_off: ln for off, ln in rc_line_map.items()
                if rc_off <= off < rc_off + rc_size}
    rc_fix_rel = {f - rc_off for f in rc_fix if rc_off <= f < rc_off + rc_size}

    led = ledger_from_raw(
        _disasm_for_diff(ps_bytes), ps_marks, ps_fix_rel, ps_bytes,
        _disasm_for_diff(rc_bytes), rc_marks, rc_fix_rel, rc_bytes,
    )
    out = led.to_json(with_insns=with_insns)
    out["name"] = function
    out["ps_size"] = ps_size
    out["rc_size"] = rc_size
    return out


# ── CLI ──────────────────────────────────────────────────────────────────
def ledger(
    function: Annotated[str, typer.Argument(help="function name")],
    json_out: Annotated[bool, typer.Option("--json", help="JSON output")] = False,
    limit: Annotated[int, typer.Option("--limit", help="max islands to print (0 = all)")] = 40,
    context: Annotated[bool, typer.Option("--src/--no-src", help="show our source line text per island")] = True,
) -> None:
    """Dual -d1 run ledger: statement-level register-blind PS-vs-RC diff."""
    from rich.console import Console
    from rich.markup import escape

    try:
        data = ledger_data(function)
    except ValueError as e:
        typer.secho(f"[!] {e}", fg="red")
        raise typer.Exit(1)

    if json_out:
        typer.echo(_json.dumps(data, indent=2))
        return

    console = Console(highlight=False)
    src_lines: dict[int, str] | None = None
    src_file = ""
    if context:
        from c2.commands.decomp_verify import (
            _build_src_func_cache, _decomp_src_lines)
        src_lines = _decomp_src_lines(function)
        rec = _build_src_func_cache().get(function)
        if rec is not None:
            src_file = rec[0].name

    console.print(
        f"[bold]run-ledger[/] {function}"
        + (f"  ({src_file})" if src_file else ""))
    console.print(
        f"  PS {data['ps_total']} insns / {data['ps_marks']} marks   "
        f"RC {data['rc_total']} insns / {data['rc_marks']} marks   "
        f"(packing witness: PS marks < RC marks = original packed "
        f"more statements/line)"
        if data["ps_marks"] < data["rc_marks"] else
        f"  PS {data['ps_total']} insns / {data['ps_marks']} marks   "
        f"RC {data['rc_total']} insns / {data['rc_marks']} marks")
    console.print(
        f"  matched [bold]{data['matched']}/{data['ps_total']}[/] "
        f"register-blind  ·  islands {len(data['islands'])}  ·  "
        f"divergent PS runs {data['ps_runs_divergent']}/{data['ps_runs_total']}"
        + (f" (+{data['rc_only_runs']} RC-only)" if data["rc_only_runs"] else ""))
    if data["verdict"] == "regalloc_pure":
        console.print(
            "  [green]verdict: regalloc_pure[/] -- every instruction matches "
            "register-blind; the whole diff is register seats / slots / "
            "encoding.  Do NOT restructure the source: c2 regtrace "
            f"{function}")
        return
    console.print(
        "  [magenta]verdict: shape_islands[/] -- each island is a local "
        "statement-shape divergence (PS L<n> = original -d1 witness; "
        f"{src_file or 'src'}:<n> = your edit target)\n")

    islands = data["islands"]
    shown = islands if not limit else islands[:limit]
    for k, isl in enumerate(shown, 1):
        pls = ",".join(str(x) for x in isl["ps_lines"]) or "-"
        rls = ",".join(str(x) for x in isl["rc_lines"]) or "-"
        tags = escape(" ".join(f"[{t}]" for t in isl["tags"]))
        console.print(
            f"  [bold]== island {k}[/] [magenta]{tags}[/]  "
            f"[cyan]PS L{pls}[/] | [yellow]{src_file or 'RC'}:{rls}[/]")
        for side, color in (("ps", "cyan"), ("rc", "yellow")):
            for ins in isl.get(side, []):
                ln = ins.get("line")
                console.print(
                    f"     [{color}]{side.upper()} "
                    f"L{ln if ln is not None else '?':>5}[/] "
                    f"{ins['off']:4x}: {escape(ins['text'])}")
        if src_lines and isl["rc_lines"]:
            for rl in isl["rc_lines"][:3]:
                txt = (src_lines.get(rl) or "").strip()
                if txt:
                    console.print(
                        f"     [dim]{src_file}:{rl} | {escape(txt)}[/]")
        console.print("")
    if limit and len(islands) > limit:
        console.print(
            f"  … {len(islands) - limit} more island(s) "
            f"(--limit 0 for all)")

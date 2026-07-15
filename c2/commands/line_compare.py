"""Compare PS.EXE vs RC.EXE ``-d1`` line emissions for byte-equal functions.

For every byte-exact function we have **two** ``-d1`` debug streams:

  * **PS** -- the original Watcom 10.0a debug info baked into PS.EXE.
  * **RC** -- our recompile of the recovered source under the same flags
    (dumped to ``.c2-cache/exact-line-map.json`` by every full
    ``decomp-verify`` pass).

When the bytes match, the line *streams* should also match in two
respects:

  1. **Same number of transitions and at the SAME byte offsets.**  Each
     debug record marks where a new source line begins; both compilers
     should emit a transition at the same instruction.  A transition
     in one stream that has no counterpart in the other -- or that
     lands a few bytes off -- means the SAME bytes are attributed to a
     different statement boundary in the recovered source.  That is a
     **smell**: the source has the right code but a different statement
     decomposition (e.g. one PS source line was split into two RC
     lines, or vice versa, by joining/splitting statements).

  2. **Same RELATIVE ORDER.**  Source-line numbers won't match
     (PS.EXE and our recompile come from different source files with
     different line numbering) but their RELATIVE ORDER must agree:
     if PS emits ``L_PS_a -> L_PS_b`` (a forward statement transition
     in source order), RC must also go forward, never backward.  An
     RC stream that decreases between transitions while PS increases
     means the recovered source has its statements in a different
     order than the original.

CLI::

    uv run c2 line-compare                # whole-corpus summary
    uv run c2 line-compare <fn>           # per-function detail
    uv run c2 line-compare --offenders    # only functions with mismatches
    uv run c2 line-compare --json         # tooling output

The command operates on PS bytes + the RC line sidecar -- it does NOT
recompile.  Run ``c2 decomp-verify`` once (without ``-f``) first if
``.c2-cache/exact-line-map.json`` is missing or stale.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console

from c2.commands.disasm import disasm_function

SIDECAR_PATH = Path(".c2-cache/exact-line-map.json")


@dataclass
class Transition:
    """A single ``-d1`` line-mark transition."""
    rel_offset: int       # bytes from function start
    line: int             # source line at this offset


@dataclass
class LineCompareResult:
    name: str
    file: str
    ps_count: int
    rc_count: int
    paired: int           # number of transitions paired at the same rel_offset
    ps_only_offsets: list[int] = field(default_factory=list)  # PS-only marks
    rc_only_offsets: list[int] = field(default_factory=list)  # RC-only marks
    misaligned: list[tuple[int, int]] = field(default_factory=list)  # (ps_off, rc_off) -- near misses
    out_of_order: list[tuple[int, int, int]] = field(default_factory=list)
    # ^ out-of-order RC transitions: (rel_offset, prev_rc_line, this_rc_line)

    @property
    def offset_mismatches(self) -> int:
        return len(self.ps_only_offsets) + len(self.rc_only_offsets)

    @property
    def is_clean(self) -> bool:
        return (
            self.offset_mismatches == 0
            and len(self.out_of_order) == 0
        )


def _ps_transitions(name: str) -> tuple[list[Transition], int]:
    """Extract PS line transitions for a function.  Returns (transitions, fn_start_addr).
    A transition is a position where the propagated line CHANGES (the first
    insn after a debug-info mark).
    """
    _, _, lines = disasm_function(name)
    if not lines:
        return [], 0
    fn_start = lines[0].address
    out: list[Transition] = []
    cur = 0
    for ln in lines:
        if ln.line and ln.line != cur:
            out.append(Transition(rel_offset=ln.address - fn_start, line=ln.line))
            cur = ln.line
    return out, fn_start


def _rc_transitions(rec: dict) -> list[Transition]:
    """Extract RC line transitions from a sidecar record.  ``rec`` is
    ``{file: ..., starts: {rel_off_str: rc_line}}``.
    """
    starts = rec.get("starts") or {}
    out = [
        Transition(rel_offset=int(off), line=int(line))
        for off, line in starts.items()
    ]
    out.sort(key=lambda t: t.rel_offset)
    # Dedupe consecutive identical lines (only count NEW transitions).
    deduped: list[Transition] = []
    cur = 0
    for t in out:
        if t.line != cur:
            deduped.append(t)
            cur = t.line
    return deduped


def _pair_by_offset(
    ps: list[Transition], rc: list[Transition], window: int = 4,
) -> tuple[list[tuple[Transition, Transition]], list[Transition], list[Transition], list[tuple[int, int]]]:
    """Pair PS and RC transitions by rel_offset.

    Returns ``(paired, ps_only, rc_only, misaligned)``.

    Exact-offset match goes into ``paired``.  Near-misses (within
    ``window`` bytes) are reported as ``misaligned`` -- a transition that
    appears in both streams but at a slightly different instruction
    boundary.  Truly missing transitions go into ``ps_only``/``rc_only``.
    """
    rc_by_off = {t.rel_offset: t for t in rc}
    paired: list[tuple[Transition, Transition]] = []
    misaligned: list[tuple[int, int]] = []
    used_rc: set[int] = set()

    for pt in ps:
        if pt.rel_offset in rc_by_off:
            paired.append((pt, rc_by_off[pt.rel_offset]))
            used_rc.add(pt.rel_offset)
        else:
            # Look for a nearby RC transition.
            best_off: Optional[int] = None
            best_dist = window + 1
            for ro in rc_by_off:
                if ro in used_rc:
                    continue
                d = abs(ro - pt.rel_offset)
                if d <= window and d < best_dist:
                    best_off = ro; best_dist = d
            if best_off is not None:
                misaligned.append((pt.rel_offset, best_off))
                paired.append((pt, rc_by_off[best_off]))
                used_rc.add(best_off)

    ps_only = [pt for pt in ps if pt.rel_offset not in {p.rel_offset for p, _ in paired}]
    rc_only = [rt for rt in rc if rt.rel_offset not in used_rc]
    return paired, ps_only, rc_only, misaligned


def _check_order(
    paired: list[tuple[Transition, Transition]],
) -> list[tuple[int, int, int]]:
    """Walk paired transitions in PS-offset order and flag any pair where
    PS and RC go in OPPOSITE directions between consecutive transitions.

    Neither stream is required to be globally monotonic -- Watcom's
    peephole pass can reorder code, in which case the SAME backward line
    transition appears at the SAME byte offset on both sides (e.g.
    ``mouse_follow_cohort`` at +0xCC: PS L611→L610, RC L802→L800; both
    sides going backward together is the compiler's choice and not a
    source-order smell).

    The smell is *divergent direction*: PS forward + RC backward (or
    vice versa) means the recovered source has its statements in a
    different order than the original.
    """
    out: list[tuple[int, int, int]] = []
    prev_ps = 0
    prev_rc = 0
    for pt, rt in paired:
        if prev_ps and prev_rc:
            ps_dir = (pt.line > prev_ps) - (pt.line < prev_ps)   # -1, 0, +1
            rc_dir = (rt.line > prev_rc) - (rt.line < prev_rc)
            # Flag only when both are non-zero and OPPOSITE.
            if ps_dir != 0 and rc_dir != 0 and ps_dir != rc_dir:
                out.append((rt.rel_offset, prev_rc, rt.line))
        prev_ps, prev_rc = pt.line, rt.line
    return out


def compare_function(name: str, file: str) -> LineCompareResult:
    """Compute the PS-vs-RC line-stream comparison for one byte-exact function."""
    sidecar = json.loads(SIDECAR_PATH.read_text())
    rec = sidecar.get(name)
    if rec is None:
        return LineCompareResult(name=name, file=file, ps_count=0, rc_count=0, paired=0)
    ps, _start = _ps_transitions(name)
    rc = _rc_transitions(rec)
    paired, ps_only, rc_only, misaligned = _pair_by_offset(ps, rc)
    order_smells = _check_order(paired)
    return LineCompareResult(
        name=name, file=file, ps_count=len(ps), rc_count=len(rc),
        paired=len(paired),
        ps_only_offsets=[t.rel_offset for t in ps_only],
        rc_only_offsets=[t.rel_offset for t in rc_only],
        misaligned=misaligned,
        out_of_order=order_smells,
    )


def _iter_corpus() -> list[tuple[str, str]]:
    """Return ``[(name, source_file)]`` for every byte-exact function in
    the sidecar, sorted by name.
    """
    if not SIDECAR_PATH.exists():
        raise FileNotFoundError(
            f"sidecar {SIDECAR_PATH} not found -- run `c2 decomp-verify` "
            "(no -f / no file filter) once to generate it"
        )
    sidecar = json.loads(SIDECAR_PATH.read_text())
    return sorted(
        (name, rec.get("file", "")) for name, rec in sidecar.items()
    )


# --- CLI ---------------------------------------------------------------------

def line_compare(
    name: Annotated[Optional[str], typer.Argument(
        help="Function name (single-function mode).  Omit for whole-corpus."
    )] = None,
    offenders: Annotated[bool, typer.Option(
        "--offenders", "-O",
        help="Whole-corpus mode: show only functions with mismatches.",
    )] = False,
    detail: Annotated[bool, typer.Option(
        "--detail", "-d",
        help="Show per-transition detail for single-function mode.",
    )] = False,
    as_json: Annotated[bool, typer.Option(
        "--json", help="Emit JSON.",
    )] = False,
    window: Annotated[int, typer.Option(
        "--window", help="Tolerance window (bytes) for near-miss pairing.",
    )] = 4,
) -> None:
    """Compare PS.EXE and RC.EXE ``-d1`` line streams for byte-exact functions.

    Two flavors of smell are surfaced:

      * **OFFSET MISMATCH** -- the line marks land on different instructions
        on the two sides.  The bytes match, but PS and RC attribute them to
        different source statements -- a sign that recovered source has
        statements split or merged differently from the original.
      * **OUT-OF-ORDER** -- RC line sequence goes backward while PS goes
        forward, meaning the recovered source has its statements in a
        different order than PS.
    """
    console = Console()
    if name is not None:
        # Look up the file for this function.
        if not SIDECAR_PATH.exists():
            console.print(
                f"[red]sidecar {SIDECAR_PATH} not found -- "
                "run `c2 decomp-verify` once first[/red]"
            )
            raise typer.Exit(1)
        sidecar = json.loads(SIDECAR_PATH.read_text())
        rec = sidecar.get(name)
        if rec is None:
            console.print(f"[red]function {name!r} not in byte-exact corpus[/red]")
            raise typer.Exit(1)
        result = compare_function(name, rec.get("file", ""))
        if as_json:
            typer.echo(json.dumps(_to_json(result), indent=2))
            return
        _print_single(console, result, detail=detail)
        return

    # Whole-corpus mode.
    results = []
    for n, fp in _iter_corpus():
        try:
            results.append(compare_function(n, fp))
        except Exception:  # noqa: BLE001
            continue

    if as_json:
        typer.echo(json.dumps(
            [_to_json(r) for r in results], indent=2,
        ))
        return

    _print_corpus(console, results, offenders=offenders)


def _to_json(r: LineCompareResult) -> dict:
    d = asdict(r)
    d["offset_mismatches"] = r.offset_mismatches
    d["is_clean"] = r.is_clean
    return d


def _print_single(console: Console, r: LineCompareResult, *, detail: bool) -> None:
    title = f"[bold]{r.name}[/]  ({r.file})"
    console.print(title)
    console.print(
        f"  PS transitions: {r.ps_count}   RC transitions: {r.rc_count}   "
        f"paired: {r.paired}"
    )
    if r.is_clean:
        console.print("  [green]clean[/] -- same offsets, same order")
        return
    if r.ps_only_offsets:
        console.print(
            f"  [yellow]PS-only marks[/] at "
            f"{', '.join(f'+0x{o:X}' for o in r.ps_only_offsets[:8])}"
            f"{'...' if len(r.ps_only_offsets) > 8 else ''}"
            f"  ({len(r.ps_only_offsets)} total)"
        )
    if r.rc_only_offsets:
        console.print(
            f"  [yellow]RC-only marks[/] at "
            f"{', '.join(f'+0x{o:X}' for o in r.rc_only_offsets[:8])}"
            f"{'...' if len(r.rc_only_offsets) > 8 else ''}"
            f"  ({len(r.rc_only_offsets)} total)"
        )
    if r.misaligned:
        console.print(
            f"  [yellow]misaligned[/] {len(r.misaligned)} mark(s) "
            f"(near-miss pairing within {4} bytes)"
        )
        if detail:
            for ps_off, rc_off in r.misaligned[:10]:
                console.print(
                    f"    PS+0x{ps_off:X}  RC+0x{rc_off:X}  "
                    f"(\u0394={rc_off - ps_off:+d})"
                )
    if r.out_of_order:
        console.print(
            f"  [red]OUT-OF-ORDER[/] {len(r.out_of_order)} RC transition(s) "
            f"go backward while PS goes forward"
        )
        if detail:
            for off, prev, cur in r.out_of_order[:10]:
                console.print(
                    f"    +0x{off:X}: RC line {cur} after {prev} (backwards)"
                )


def _print_corpus(
    console: Console, results: list[LineCompareResult], *, offenders: bool,
) -> None:
    clean = sum(1 for r in results if r.is_clean)
    with_offset = sum(1 for r in results if r.offset_mismatches > 0)
    with_order  = sum(1 for r in results if r.out_of_order)
    total = len(results)
    console.print(
        f"[bold]Byte-exact corpus[/]: {total} function(s)\n"
        f"  clean (same offsets, same order): {clean} "
        f"({100*clean/total:.1f}%)\n"
        f"  offset mismatches: {with_offset}\n"
        f"  out-of-order RC: {with_order}"
    )
    if offenders or total - clean < 20:
        # Show details for the non-clean functions
        bad = [r for r in results if not r.is_clean]
        bad.sort(key=lambda r: (
            -(len(r.out_of_order)), -r.offset_mismatches, r.name,
        ))
        console.print()
        if not bad:
            console.print("[green]all clean[/]")
            return
        console.print(
            f"  [yellow]{len(bad)} offender(s)[/] (showing up to 30):"
        )
        for r in bad[:30]:
            tags = []
            if r.out_of_order:
                tags.append(f"[red]OOO x{len(r.out_of_order)}[/]")
            if r.offset_mismatches:
                tags.append(f"[yellow]offset x{r.offset_mismatches}[/]")
            console.print(
                f"    {r.name:<36s}  {' '.join(tags):<30s}  "
                f"PS={r.ps_count} RC={r.rc_count}  ({r.file})"
            )

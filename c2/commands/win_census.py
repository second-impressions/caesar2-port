"""``c2 win-census`` — named-local census from the CAESAR2.EXE /Od witness.

The W2 witness of `docs/root-cause-survey-2026-07-02.md`: MSVC 4.0 ``/Od``
gives **every named source local a distinct ``[ebp-N]`` frame slot**, so the
slot set of CAESAR2.EXE's copy of a function is a census of the ORIGINAL
source's local-variable set — the input that decides Watcom conflict
membership, savings rank, and the spill boundary.  Comparing it against our
own MSVC compile of the same source names invented / missing locals per
function — the class no decl-permutation or forge lever can reach.

Reliability:

* **Gate on mapping quality Q** (aligned-instruction match ratio).  The win
  func-map is fuzzy; Q >= 0.85 ⇒ ``usable``, 0.70–0.85 ⇒ ``caution``,
  < 0.70 ⇒ ``mapping-suspect`` (do not trust the census).
* Baseline: on PS-byte-exact functions the slot-count census agrees 78.5 %;
  the residual mismatch is port drift + low-Q mappings.  On the diffing
  corpus it agreed only 49 % (2026-07-02) — that gap IS the signal.
* Port drift is real (the Windows source is a later cut).  Treat every
  census delta as a *candidate*, adjudicated by the PS ``-d1`` line marks
  (W1) and the PS asm.  Read the win ASM, not the Ghidra decompile (which
  forward-propagates locals).

Interpretation of ``delta = theirs − ours``:

* ``delta > 0`` — the original declared MORE locals: find the unmatched
  slot's use profile below and NAME that value in our source
  (worked: ``evolve_water_table`` ``kind - 0xda`` int temp, ir 7→5).
* ``delta < 0`` — our source INVENTED locals (§13 over-decompiled mirror):
  inline them.
* ``delta == 0`` with differing widths — a local has the wrong TYPE.

Usage::

    c2 win-census evolve_water_table       # one function, full slot tables
    c2 win-census --corpus                 # every still-diffing function
    c2 win-census --corpus --all           # include byte-exact functions
    c2 win-census <fn> --json              # structured output

Every census also includes the **goto-topology witness**
(``docs/msvc-od-goto-signal.md``): MSVC /Od preserves every
``goto``/``break``/``continue`` as its own E9 ``jmp``, so comparing
CAESAR2.EXE's internal-jmp funnel profile against our own MSVC compile
names functions whose recovered source is MISSING a jump statement the
original had (``missing-goto``) or invented one it lacked
(``extra-goto``).  No flag needed — it rides along by default (same
compiled TU, negligible cost).
"""
from __future__ import annotations

import json as _json
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from typing_extensions import Annotated

console = Console()


def _fmt_slots(slots: dict) -> str:
    parts = []
    for disp in sorted(slots):
        rec = slots[disp]
        w = "".join(sorted(rec["widths"]))
        parts.append(f"-0x{disp:x}:{w}")
    return " ".join(parts)


def _render_one(v, verbose: bool) -> None:
    from rich.text import Text

    gate_style = {"usable": "green", "caution": "yellow",
                  "mapping-suspect": "red"}.get(v.gate, "dim")
    console.print(
        f"[bold]{v.name}[/bold] ({v.tu}.c) — census "
        + ("[red]UNAVAILABLE[/red]: " + v.note if not v.ok else "")
    )
    if not v.ok:
        return
    console.print(
        f"  mapping quality Q={v.quality:.2f} → [{gate_style}]{v.gate}[/{gate_style}]"
        + ("   ⚠ do NOT act on this census" if v.gate == "mapping-suspect" else "")
    )
    console.print(
        f"  frame: ours {v.frame_ours} vs win {v.frame_theirs}"
        f"   slots: ours {len(v.slots_ours)} vs win {len(v.slots_theirs)}"
        f"   Δ={v.delta:+d}"
    )
    if v.delta > 0:
        console.print(
            "  [yellow]original has MORE named locals[/yellow] — find the"
            " unmatched slot profile below and NAME that value in the source"
        )
    elif v.delta < 0:
        console.print(
            "  [yellow]our source has EXTRA locals[/yellow] — §13 invented-"
            "local candidates; consider inlining"
        )
    else:
        console.print("  slot COUNT matches — check widths / use profiles for type drift")
    if verbose or v.delta != 0:
        t = Table(title="win (CAESAR2.EXE) slot profile", show_lines=False)
        t.add_column("slot"); t.add_column("width"); t.add_column("uses",
                                                                  justify="right")
        t.add_column("first use")
        for disp in sorted(v.slots_theirs):
            rec = v.slots_theirs[disp]
            t.add_row(f"ebp-0x{disp:x}", "".join(sorted(rec["widths"])),
                      str(rec["n_uses"]), rec["first"].replace("[", "(").replace("]", ")"))
        console.print(t)
        console.print(f"  ours:   {_fmt_slots(v.slots_ours)}")
        console.print(f"  theirs: {_fmt_slots(v.slots_theirs)}")
    console.print(
        "  adjudicate with W1 (-d1 marks: `c2 disasm` L column) + PS asm "
        "before editing; see docs/root-cause-survey-2026-07-02.md"
    )


def _render_goto_one(v) -> None:
    """The goto-topology block appended to every single-function census."""
    if not v.ok:
        console.print(f"  goto-topology: unavailable ({v.note})")
        return
    vstyle = {"consistent": "green", "missing-goto": "red",
              "extra-goto": "yellow", "mixed": "magenta"}.get(v.verdict, "")
    src = v.src or {}
    console.print(
        f"  goto-topology: [{vstyle}]{v.verdict}[/{vstyle}] "
        f"(Q={v.quality:.2f} {v.gate}) — source has {src.get('gotos', '?')} "
        f"goto(s), {src.get('labels', '?')} label(s)"
        + (f" ({', '.join(src['label_names'])})"
           if src.get("label_names") else ""))
    for side, topo in (("win ", v.theirs), ("ours", v.ours)):
        fun = " ".join(f"+{f.target:#x}×{f.indeg}:{f.kind}"
                       for f in topo.funnels) or "none"
        console.print(f"    {side}: {topo.n_jmp} internal jmp(s), "
                      f"{topo.n_pairs} cond-jump-stmt pair(s), funnels: {fun}")
    for d in v.detail:
        console.print(f"    → {d}")
    if v.verdict != "consistent":
        console.print(
            "    [dim]a win-only non-epilogue funnel = a shared label / "
            "continue the original had; kind=loop-inc means continue (only "
            "backedge+continue can converge on an increment).  See "
            "docs/msvc-od-goto-signal.md.[/dim]")
    if v.ps_evidence:
        evs = ", ".join(f"+{e['offset']:#x}×{e['indeg']}"
                        for e in v.ps_evidence[:8])
        console.print(
            f"    ps corroboration: {len(v.ps_evidence)} detached multi-pred "
            f"block(s) in PS.EXE ({evs})")


_GOTO_ABBREV = {"missing-goto": ("MISS", "red"),
                "extra-goto": ("extra", "yellow"),
                "mixed": ("mixed", "magenta"),
                "consistent": ("ok", "green")}


def _goto_json(v) -> dict:
    if not v.ok:
        return {"ok": False, "note": v.note}
    return {"ok": True, "verdict": v.verdict, "gate": v.gate,
            "quality": round(v.quality, 3),
            "win_funnels": list(v.theirs.goto_profile),
            "our_funnels": list(v.ours.goto_profile),
            "win_jmps": v.theirs.n_jmp, "our_jmps": v.ours.n_jmp,
            "src_gotos": (v.src or {}).get("gotos"),
            "src_labels": (v.src or {}).get("labels"),
            "ps_evidence": len(v.ps_evidence)}


def win_census(
    function: Annotated[Optional[str], typer.Argument(
        help="function to census (omit with --corpus)")] = None,
    corpus: Annotated[bool, typer.Option(
        "--corpus", help="census every still-diffing function")] = False,
    include_exact: Annotated[bool, typer.Option(
        "--all", help="with --corpus: include byte-exact functions")] = False,
    verbose: Annotated[bool, typer.Option(
        "-v", "--verbose", help="always show the full slot tables")] = False,
    as_json: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Named-local census + goto-topology witness: our MSVC /Od build vs
    CAESAR2.EXE."""
    from c2 import win_bytes as wb
    from c2.goto_topology import win_goto_audit

    if function is None and not corpus:
        raise typer.BadParameter("give a FUNCTION or --corpus")

    if function is not None:
        v = wb.census_func(function)
        gv = win_goto_audit(function)
        if as_json:
            d = v.__dict__.copy()
            for k in ("slots_ours", "slots_theirs"):
                d[k] = {hex(disp): {"widths": sorted(rec["widths"]),
                                    "n_uses": rec["n_uses"],
                                    "first": rec["first"]}
                        for disp, rec in d[k].items()}
            d["goto"] = _goto_json(gv)
            typer.echo(_json.dumps(d, indent=1))
            return
        _render_one(v, verbose)
        _render_goto_one(gv)
        return

    # --corpus
    verify = None
    try:
        verify = _json.loads(open(".c2-cache/verify.json").read())
    except OSError:
        console.print("[red]no .c2-cache/verify.json — run c2 decomp-verify first[/red]")
        raise typer.Exit(1)
    rows = []
    for f in verify["functions"]:
        diffing = (f.get("diff_byte_count") or 0) > 0 or f.get("size_differs")
        if not diffing and not include_exact:
            continue
        v = wb.census_func(f["name"])
        gv = win_goto_audit(f["name"])
        rows.append((f["name"], f.get("diff_byte_count"), v, gv))
    if as_json:
        out = [{"name": n, "ps_diff": b, "ok": v.ok, "quality": round(v.quality, 3),
                "gate": v.gate, "delta": v.delta, "note": v.note,
                "goto": _goto_json(gv)}
               for n, b, v, gv in rows]
        typer.echo(_json.dumps(out, indent=1))
        return
    t = Table(title="win /Od census: named locals + goto topology "
                    "(diffing corpus)")
    for col in ("function", "PS diff", "Q", "gate", "slots o/t", "Δ",
                "goto", "funnels w/o", "note"):
        t.add_column(col)
    rows.sort(key=lambda r: (not r[2].ok, -(abs(r[2].delta)), -(r[2].quality)))
    for n, b, v, gv in rows:
        if not v.ok:
            t.add_row(n, str(b), "-", "-", "-", "-", "-", "-", v.note)
            continue
        style = {"usable": "green", "caution": "yellow",
                 "mapping-suspect": "red"}[v.gate]
        if gv.ok:
            ab, gcolor = _GOTO_ABBREV[gv.verdict]
            gcell = f"[{gcolor}]{ab}[/{gcolor}]"
            fcell = (f"{list(gv.theirs.goto_profile)}/"
                     f"{list(gv.ours.goto_profile)}"
                     if gv.verdict != "consistent" else "")
        else:
            gcell, fcell = "-", ""
        t.add_row(n, str(b), f"{v.quality:.2f}", f"[{style}]{v.gate}[/{style}]",
                  f"{len(v.slots_ours)}/{len(v.slots_theirs)}", f"{v.delta:+d}",
                  gcell, fcell, "")
    console.print(t)
    console.print(
        "act only on [green]usable[/green] rows; Δ≠0 names a local-set "
        "mismatch — the lever no permutation reaches "
        "(docs/root-cause-survey-2026-07-02.md §2).  "
        "goto [red]MISS[/red] = CAESAR2.EXE has jump-stmt structure "
        "(goto/continue/break funnel) our source lacks; drill in with "
        "c2 win-census <fn> (docs/msvc-od-goto-signal.md)"
    )

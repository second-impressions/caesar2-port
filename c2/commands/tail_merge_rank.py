"""tail-merge command: rank tail-merge donors by leverage.

Cross-references every diffing function (per ``c2 decomp-verify``)
against its tail-merge donor (Rule 42).  A donor whose RC body
ships byte-identical to PS makes ALL its tail-merge dependents
candidates for byte-exact flips, since the only thing that
distinguishes the dependents' rel32 jmp displacements from PS's
is the donor's address + body shape after linking.

The output groups dependents by donor and tags each donor as:

  * ``stub``        — donor not yet decompiled.  Highest leverage:
                       writing a body whose epilogue *shape* matches
                       PS often byte-flips dependents even before
                       the donor itself is fully exact (the
                       :rule-42: tail-merge case).
  * ``diffing``     — donor compiled but doesn't byte-match yet.
                       Fixing the donor's diffs unblocks dependents.
  * ``byte-exact``  — donor already perfect; the dependents' diffs
                       are body diffs in the dependent itself, not
                       a Rule 42 cause.  Listed for completeness,
                       deprioritised in the leverage view.

⚠ TRUE vs APPARENT leverage (validated 2026-06, ``docs/comtail-cascade-analysis.md``)
------------------------------------------------------------------------------------
Fixing a donor only *flips a dependent byte-exact* when that dependent's
entire diff is in the **shared tail** it merges away (PS emits ``jmp
donor`` where RC kept the epilogue inline).  Empirically that is RARE:
across the whole corpus only ~2 dependents are genuinely *tail-blocked*;
the other ~370 tail-merge dependents have their own **body** diffs that a
donor fix does NOT touch.  The strong donor-exact↔dependent-exact
correlation (≈92%) is **confounded by shared regional difficulty**, not
causation.  Therefore the leverage column to trust is ``#tb``
(tail-blocked dependents), NOT ``#dep``.  ``ComTail`` is deterministic
given identical IL (``bld/cg/c/optcom.c`` — ``FindCommon`` picks the
max-common-tail ``first`` as canonical), so a tail-merge byte-diff is
downstream of a body/IL diff in a cluster member, not an independent
"merge direction" knob you can turn from C.

Examples::

    # Top 20 donors, ranked by TRUE (tail-blocked) leverage first.
    uv run c2 tail-merge

    # Only the genuinely tail-merge-blocked dependents (the real cases).
    uv run c2 tail-merge --blocked

    # JSON form for tooling.
    uv run c2 tail-merge --json

    # Show every dependent for one donor.
    uv run c2 tail-merge --donor garden_an_area
"""

from __future__ import annotations

import json
import re

from collections import defaultdict
from pathlib import Path
from typing import Annotated, Optional

import typer

from c2.commands.disasm import disasm_function

_FUNCTION_RE = re.compile(
    r"^\s*//\s*FUNCTION:\s*\w+\s+0x([0-9A-Fa-f]+)", re.MULTILINE,
)
_STUB_RE = re.compile(
    r"^\s*//\s*STUB:\s*\w+\s+0x([0-9A-Fa-f]+)", re.MULTILINE,
)


def _scan_annotated(src_dir: Path) -> tuple[set[int], set[int]]:
    """Return (function_addrs, stub_addrs) over every decomp/src/*.c."""
    funcs: set[int] = set()
    stubs: set[int] = set()
    for p in sorted(src_dir.rglob("*.c")):
        text = p.read_text()
        for m in _FUNCTION_RE.finditer(text):
            funcs.add(int(m.group(1), 16))
        for m in _STUB_RE.finditer(text):
            stubs.add(int(m.group(1), 16))
    return funcs, stubs


def _run_verify_json(no_strict: bool = True) -> dict:
    """Return the full verify-json document.

    Routes through :func:`c2.commands.verify_json.get_verify_json` which
    serves from ``.c2-cache/verify.json`` when fresh (~80 ms) and falls
    back to an in-process incremental rebuild when stale.  Avoids the
    2-minute ``uv run c2 decomp-verify --json`` subprocess we used to
    shell out to on every invocation \u2014 that re-ran the full per-function
    shape/seat/width/spill analysis even when the cache had everything.
    """
    from c2.commands.verify_json import get_verify_json
    return get_verify_json()


# A dependent is genuinely *tail-merge-blocked* (a donor fix would flip it
# byte-exact) only when every one of its diff bytes lands in the shared
# tail it merges away — i.e. the last few bytes (PS emits ``jmp donor``
# where RC kept the epilogue/return inline).  Anything earlier is the
# dependent's own body diff, which a donor fix does NOT touch.  12 bytes
# comfortably covers an epilogue (``add esp,N; pop×k; ret``) plus the
# 5-byte merge jmp; validated against the 2 real corpus cases
# (put_danger_flag, show_this_tribune).
_TAIL_WINDOW = 12


def _is_tail_blocked(fn: dict) -> bool:
    """True iff every diff byte of ``fn`` is in its shared-tail window.

    Such a dependent's only divergence is the tail-merge itself, so making
    its donor's tail byte-exact (and letting ComTail re-merge) flips it.
    Returns False for exact functions and for functions with any body diff.
    """
    offs = fn.get("diff_byte_offsets") or []
    if not offs:
        return False
    size = fn.get("size") or 0
    return min(offs) >= max(0, size - _TAIL_WINDOW)


def tail_merge(
    donor: Annotated[
        Optional[str],
        typer.Option(
            "--donor", "-d",
            help="Show every dependent of one donor (defaults to all donors).",
        ),
    ] = None,
    limit: Annotated[
        int,
        typer.Option(
            "--limit", "-n",
            help="Show top N donors.",
        ),
    ] = 30,
    json_out: Annotated[
        bool,
        typer.Option("--json", help="Emit JSON instead of a table."),
    ] = False,
    blocked: Annotated[
        bool,
        typer.Option(
            "--blocked",
            help="Show ONLY the genuinely tail-merge-blocked dependents "
                 "(diff entirely in the shared tail) — the cases a donor "
                 "fix would actually flip byte-exact.",
        ),
    ] = False,
    src_dir: Annotated[
        Path,
        typer.Option("--src-dir", help="Decompiled-source directory."),
    ] = Path("decomp/src"),
    symbols_json: Annotated[
        Path,
        typer.Option("--symbols", help="Path to symbols.json."),
    ] = Path("data/out/symbols.json"),
) -> None:
    """Rank tail-merge donors by leverage."""

    # ── 1. Pull the diffing functions + their tail_merge fields ───────
    if not json_out:
        typer.echo("Loading verify cache …", err=True)
    verify = _run_verify_json()

    # ── 2. Enumerate annotated FUNCTION:/STUB: addresses ──────────────
    funcs_addrs, stubs_addrs = _scan_annotated(src_dir)

    # ── 3. Resolve donor names → addresses + classify ─────────────────
    sym = json.loads(symbols_json.read_text())
    addr_by_name = {s["name"]: s["address"] for s in sym["symbols"]}
    verify_by_name = {fn["name"]: fn for fn in verify["functions"]}

    def status(name: str) -> str:
        fn = verify_by_name.get(name)
        if fn is not None:
            return "diffing" if fn.get("diff_byte_count", 0) else "byte-exact"
        addr = addr_by_name.get(name)
        if addr is None:
            return "unknown-addr"
        if addr in stubs_addrs:
            return "stub"
        if addr in funcs_addrs:
            # Decomp-verify should normally include every FUNCTION: body.
            # If it doesn't, keep the classification conservative.
            return "decompiled-unverified"
        return "not-decomp"

    # ── 4. Group dependents by donor ──────────────────────────────────
    groups: dict[str, list[dict]] = defaultdict(list)
    for fn in verify["functions"]:
        tm = fn.get("tail_merge")
        if not tm:
            continue
        groups[tm["donor_name"]].append({
            "name":         fn["name"],
            "file":         fn["file"],
            "size":         fn["size"],
            "diff_total":   fn["diff_byte_count"],
            "merge_off":    tm["merge_offset_in_donor"],
            "tail_b":       len(bytes.fromhex(tm["tail_bytes"])),
            "tail_blocked": _is_tail_blocked(fn),
        })

    # ── 5. Augment with donor's address + size + status ───────────────
    donor_records: list[dict] = []
    for name, deps in groups.items():
        donor_addr = addr_by_name.get(name)
        donor_size: Optional[int] = None
        if donor_addr is not None:
            try:
                _addr, donor_size, _ = disasm_function(name)
            except Exception:
                donor_size = None
        donor_fn = verify_by_name.get(name)
        donor_diff = donor_fn.get("diff_byte_count", 0) if donor_fn else None
        donor_rule_hints = donor_fn.get("rule_hints", {}) if donor_fn else {}
        sigma_diff = sum(d["diff_total"] for d in deps)
        n_tail_blocked = sum(1 for d in deps if d["tail_blocked"])
        # TRUE leverage = number of tail-blocked dependents a donor fix would
        # actually flip.  This is the metric to rank by; the old #dep-based
        # ROI vastly over-counts (most dependents have own-body diffs).  We
        # still expose the heuristic ROI as a secondary tie-break.
        donor_cost = max(1, (donor_diff or 0) + (donor_size or 0) // 4)
        roi = (len(deps) * sigma_diff) / donor_cost
        donor_records.append({
            "donor":      name,
            "donor_addr": donor_addr,
            "donor_size": donor_size,
            "donor_diff": donor_diff,
            "donor_rule_hints": donor_rule_hints,
            "status":     status(name),
            "n_dep":      len(deps),
            "n_tail_blocked": n_tail_blocked,
            "sigma_diff": sigma_diff,
            "sigma_size": sum(d["size"] for d in deps),
            "roi":        roi,
            "dependents": deps,
        })

    # ── 6. Sort: stubs first, then diffing, then byte-exact;
    #            within each group sort by ROI DESC, then Σdiff DESC.
    _RANK = {"stub": 0, "diffing": 1, "byte-exact": 2,
             "decompiled-unverified": 3, "not-decomp": 4, "unknown-addr": 5}
    # TRUE-leverage first (n_tail_blocked), then status, then heuristic ROI.
    donor_records.sort(key=lambda r: (
        -r["n_tail_blocked"], _RANK.get(r["status"], 99),
        -r["roi"], -r["sigma_diff"], -r["n_dep"],
    ))

    # ── 5b. --blocked: show ONLY genuinely tail-merge-blocked dependents ──
    if blocked and not donor:
        rows = []
        for r in donor_records:
            for d in r["dependents"]:
                if d["tail_blocked"]:
                    rows.append((d, r))
        if json_out:
            typer.echo(json.dumps([
                {"dependent": d["name"], "file": d["file"],
                 "diff": d["diff_total"], "donor": r["donor"],
                 "donor_status": r["status"], "donor_diff": r["donor_diff"]}
                for d, r in rows
            ], indent=2, default=str))
            return
        typer.echo(
            f"\n  {len(rows)} genuinely tail-merge-blocked dependent(s) "
            f"(diff entirely in the shared tail — a donor-tail fix flips these):\n"
        )
        if not rows:
            typer.echo("  (none)\n")
            return
        typer.echo(f"  {'dependent':<28} {'Δ':>4}  {'donor':<28} {'donorΔ':>6}  status")
        for d, r in sorted(rows, key=lambda x: x[0]["diff_total"]):
            dd = "?" if r["donor_diff"] is None else str(r["donor_diff"])
            typer.echo(
                f"  {d['name']:<28} {d['diff_total']:>4}  "
                f"{r['donor']:<28} {dd:>6}  {r['status']}"
            )
        typer.echo(
            "\n  To flip these: make the donor's *shared tail* byte-exact "
            "(not necessarily its whole body), then ComTail re-merges.\n"
        )
        return

    if donor:
        donor_records = [r for r in donor_records if r["donor"] == donor]
        if not donor_records:
            typer.secho(f"No diffing dependents found for donor {donor!r}.",
                        fg="yellow", err=True)
            raise typer.Exit(1)

    # ── 7. Emit ───────────────────────────────────────────────────────
    if json_out:
        typer.echo(json.dumps({
            "summary": verify["summary"],
            "donors":  donor_records,
        }, indent=2, default=str))
        return

    n_total_dep = sum(len(g) for g in groups.values())
    typer.echo(
        f"\n  {len(donor_records)} donors with diffing dependents "
        f"({n_total_dep} dependent functions; "
        f"{sum(r['sigma_diff'] for r in donor_records)} Σ byte-diffs)\n"
    )

    if donor:
        # Detailed per-donor view.
        for r in donor_records:
            sz = f"{r['donor_size']} b" if r['donor_size'] else "?"
            hints = ", ".join(r["donor_rule_hints"].keys()) or "-"
            donor_delta = "?" if r["donor_diff"] is None else str(r["donor_diff"])
            typer.echo(
                f"  {r['donor']:<32}  0x{(r['donor_addr'] or 0):X}  "
                f"{sz:>6}  status={r['status']}  donorΔ={donor_delta}  "
                f"ROI={r['roi']:.1f}  hints={hints}"
            )
            typer.echo(
                f"    {'dependent':<28}  {'sz':>5}  {'Δ':>4}  "
                f"{'merge_off':>9}  blocked?"
            )
            for d in sorted(r["dependents"], key=lambda x: -x["diff_total"]):
                tb = "TAIL-BLOCKED" if d["tail_blocked"] else "own-body"
                typer.echo(
                    f"    {d['name']:<28}  {d['size']:>5}  "
                    f"{d['diff_total']:>4}  +0x{d['merge_off']:<6X}  {tb}"
                )
            typer.echo("")
        return

    # Leaderboard view.
    n_tb_total = sum(r["n_tail_blocked"] for r in donor_records)
    typer.echo(
        f"  {'donor':<32}  {'addr':>9}  {'size':>5}  {'Δd':>5}  "
        f"{'#tb':>3}  {'#dep':>4}  {'Σ Δ':>5}  {'ROI':>7}  {'status':<10}  hints / example deps"
    )
    typer.echo("  " + "-" * 132)
    for r in donor_records[:limit]:
        flag = "★" if r["status"] == "stub" else (
            "✓" if r["n_tail_blocked"] else " ")
        sz   = f"{r['donor_size']}" if r["donor_size"] else "?"
        addr = f"0x{r['donor_addr']:X}" if r["donor_addr"] else "?"
        deps = ", ".join(d["name"] for d in r["dependents"][:3])
        if r["n_dep"] > 3:
            deps += f" … (+{r['n_dep'] - 3})"
        hints = ",".join(r["donor_rule_hints"].keys()) or "-"
        donor_delta = "?" if r["donor_diff"] is None else str(r["donor_diff"])
        typer.echo(
            f"  {flag} {r['donor']:<30}  {addr:>9}  {sz:>5}  {donor_delta:>5}  "
            f"{r['n_tail_blocked']:>3}  {r['n_dep']:>4}  {r['sigma_diff']:>5}  "
            f"{r['roi']:>7.1f}  {r['status']:<10}  {hints}: {deps}"
        )

    typer.echo("")
    typer.echo(
        f"  ⚠ TRUE leverage = #tb (tail-blocked dependents): {n_tb_total} "
        f"corpus-wide.  A donor fix only flips dependents whose ENTIRE diff\n"
        f"    is in the shared tail (run `c2 tail-merge --blocked` to list them).  "
        f"#dep / ΣΔ / ROI count ALL dependents and are CONFOUNDED — most\n"
        f"    have own-body diffs a donor fix won't touch (see "
        f"docs/comtail-cascade-analysis.md).\n"
        "  Legend: ★ = stub donor; ✓ = donor with ≥1 genuinely tail-blocked "
        "dependent (real cascade leverage).\n"
    )

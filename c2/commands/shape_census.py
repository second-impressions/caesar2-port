"""``c2 shape-census`` -- sub-classify the diffing corpus into TRUE-SHAPE vs
SEATING/CONTEXT residues, using the run-ledger island FAMILY tags.

Why this exists
---------------
``c2 worklist`` / ``c2 regalloc-verdict`` route every non-byte-exact function
to a fix-order LAYER (L1 substrate / L2 shape-IR / L4 identity).  But the
``ir`` layer is coarse: it counts binir-divergent source lines, and binir's
reverse recovery is sparse, so it OVER-attributes to "shape".  Two functions
both land in "L2 shape":

  * ``take_census``           -- one ``ops`` island: a genuine statement-shape
                                 divergence you can fix by rewriting the C.
  * ``place_a_building_top``  -- one ``zext-idiom`` island: a byte-zext
                                 REALISATION difference (``xor;mov al`` vs
                                 ``mov al;and 0xff``) that is NOT a source
                                 shape at all -- its byte-exact twin
                                 ``place_a_building_base`` uses the identical
                                 construct.  Grinding its "shape" is wasted.

The DIFFERENCE is visible in the run-ledger island family tags, which come
from the RELIABLE register-blind PS-vs-RC asm comparison (``c2.runledger``),
NOT from sparse binir.  This command runs that census over the whole diffing
set and buckets each function:

  * **SHAPE**        -- has >=1 island tagged ``ops`` / ``const`` /
                        ``signedness`` / ``loop-form``: a real source-shape
                        lever.  Work these with the Mac/Win oracle + the rule
                        catalogue.  Ranked cleanest-first (pure-``ops``, fewest
                        islands = the sharpest targets).
  * **SEATING/CTX**  -- islands are ONLY ``slot`` / ``zext-idiom`` (+
                        ambiguous ``width`` / ``frame``): a regalloc
                        realisation / seating residue.  Do NOT rewrite the
                        source shape; these are near the regalloc floor.
  * **PURE-SEATING** -- ZERO islands (``regalloc_pure``): every instruction
                        matches register-blind; the whole diff is a
                        register-identity / encoding tie.  The ✓IR set.
                        Work with ``c2 regtrace`` seat levers, not source.

Validated: ``place_a_building_top`` lands in SEATING/CTX (matches its
byte-exact twin); the 7 ✓IR seat residues land in PURE-SEATING.  Unlike a
binir tree-diff, this census produces NO false positives (a byte-exact
function has zero islands and never appears).

Usage::

    uv run c2 shape-census                # the bucketed table
    uv run c2 shape-census --json         # machine-readable
    uv run c2 shape-census --targets      # just the cleanest SHAPE targets
"""
from __future__ import annotations

import json
from typing import Annotated, Optional

import typer

# Island family tags (from c2.runledger._tag_island) split by what they mean
# for the SOURCE author.
_SHAPE_TAGS = {"ops", "const", "signedness", "loop-form"}
_SEATING_TAGS = {"slot", "zext-idiom", "incr-realize", "const-realize"}
_AMBIG_TAGS = {"width", "frame"}


def _classify(n_islands: int, tags: dict) -> str:
    """Bucket a function from its island count + family-tag histogram."""
    if n_islands == 0 or not tags:
        return "pure-seating"
    tagset = set(tags)
    if tagset & _SHAPE_TAGS:
        return "shape"
    if tagset <= (_SEATING_TAGS | _AMBIG_TAGS):
        return "seating-ctx"
    return "shape"          # unknown tag -> assume worth a look


def _census(functions: list[str]) -> tuple[list[dict], list[str]]:
    """Run the run-ledger over each function; return (rows, errors)."""
    from c2.commands.ledger import ledger_data
    rows: list[dict] = []
    errors: list[str] = []
    for fn in functions:
        try:
            led = ledger_data(fn, with_insns=False)
        except Exception as exc:                       # noqa: BLE001
            errors.append(f"{fn}: {str(exc)[:100]}")
            continue
        tags: dict[str, int] = {}
        for isl in led.get("islands", []):
            for t in isl.get("tags", []):
                tags[t] = tags.get(t, 0) + 1
        n_isl = len(led.get("islands", []))
        shape_isl = sum(c for t, c in tags.items() if t in _SHAPE_TAGS)
        seating_isl = sum(c for t, c in tags.items() if t in _SEATING_TAGS)
        rows.append({
            "function": fn,
            "cls": _classify(n_isl, tags),
            "n_islands": n_isl,
            "shape_islands": shape_isl,
            "seating_islands": seating_isl,
            "pure_ops": set(tags) == {"ops"},
            "tags": tags,
            "verdict": led.get("verdict"),
        })
    return rows, errors


def _sort_key(r: dict) -> tuple:
    """SHAPE first (cleanest-first), then seating-ctx, then pure-seating."""
    cls_rank = {"shape": 0, "seating-ctx": 1, "pure-seating": 2}[r["cls"]]
    if r["cls"] == "shape":
        # cleanest shape target first: pure-`ops`, then fewest islands, then
        # most shape-dominant.
        return (cls_rank, 0 if r["pure_ops"] else 1, r["n_islands"],
                -r["shape_islands"], r["function"])
    return (cls_rank, r["n_islands"], r["function"])


def _diffing_functions() -> list[str]:
    from c2.commands.verify_json import get_verify_json
    v = get_verify_json(verbose=False, no_build=False)
    return [f["name"] for f in v.get("functions", [])
            if f.get("diff_byte_count", 0) > 0]


def shape_census(
    json_out: Annotated[bool, typer.Option(
        "--json", help="machine-readable output")] = False,
    targets: Annotated[bool, typer.Option(
        "--targets", help="print only the cleanest SHAPE targets")] = False,
):
    """Sub-classify diffing functions into true-shape vs seating/context
    residues via the run-ledger island family tags (the reliable
    register-blind asm signal -- no binir, no false positives)."""
    functions = _diffing_functions()
    rows, errors = _census(functions)
    rows.sort(key=_sort_key)

    if json_out:
        typer.echo(json.dumps({"rows": rows, "errors": errors}, indent=2))
        return

    from collections import Counter
    buckets = Counter(r["cls"] for r in rows)

    if targets:
        clean = [r for r in rows if r["cls"] == "shape" and r["pure_ops"]]
        typer.secho(f"\n{len(clean)} clean SHAPE targets "
                    "(pure-`ops` islands -- sharpest source-shape levers):",
                    fg="green", bold=True)
        for r in clean:
            typer.echo(f"  {r['function']:34} {r['n_islands']} island(s)")
        return

    typer.secho("\nshape-census -- diffing corpus by island family "
                f"({len(rows)} fns)", fg="green", bold=True)
    typer.secho(
        f"  SHAPE {buckets['shape']}  ·  SEATING/CTX {buckets['seating-ctx']}"
        f"  ·  PURE-SEATING {buckets['pure-seating']}", fg="cyan")
    typer.echo("  SHAPE = real source-shape lever (work these) · "
               "SEATING/CTX = regalloc realisation (don't rewrite shape) · "
               "PURE-SEATING = ✓IR register-identity tie (c2 regtrace)")
    typer.echo("")
    typer.echo(f"  {'class':13} {'function':34} {'isl':>3}  tags")
    typer.echo("  " + "-" * 78)
    last = None
    for r in rows:
        if r["cls"] != last:
            last = r["cls"]
        star = " ★" if (r["cls"] == "shape" and r["pure_ops"]) else "  "
        tagstr = " ".join(f"{t}:{c}" for t, c in sorted(r["tags"].items())) or "-"
        typer.echo(f"{star}{r['cls']:13} {r['function']:34} "
                   f"{r['n_islands']:>3}  {tagstr}")
    if errors:
        typer.secho(f"\n  {len(errors)} error(s):", fg="yellow")
        for e in errors[:10]:
            typer.echo(f"    {e}")
    typer.echo("\n  ★ = cleanest shape targets (pure-`ops`).  "
               "SEATING/CTX + PURE-SEATING are near the regalloc floor -- "
               "spend source-shape effort on SHAPE rows.")

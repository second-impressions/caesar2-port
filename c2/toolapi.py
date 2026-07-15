"""toolapi -- stable, structured-return facade for the pi `c2` extension.

The pi tools (TypeScript, in `.pi/extensions/c2/`) call these functions
in-process via a stateless `python -c "from c2.toolapi import <op>; ..."`
launcher and consume the returned **dict** directly.  This module is the
extension's ONLY import surface: it re-exports / lightly wraps the
per-command data functions and normalizes the headline fields so every
result carries a consistent ``{name, byte_diff, exact}`` projection.

Design contract (see .pi/extensions/c2/{DESIGN,C2-TWEAKS}.md):

* **No CLI command, no daemon.**  Just importable functions returning
  Python structures (JSON-serialisable with ``default=str``).
* **Canonical headline:** ``byte_diff: int`` and ``exact: bool`` on every
  result that can carry them, projected here so callers never have to
  reconcile ``byte_diff`` vs ``diff_byte_count`` spellings.
* **No printing.**  Functions return; they never write to stdout/stderr.
  (Some underlying commands only dump JSON to stdout today; we capture
  that here so the hackiness is contained in one place and the public
  contract stays clean even after the underlying split lands.)
"""

from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
from typing import Any, Optional

# Default data locations (match the c2 command defaults).
_SYMBOLS = Path("data/out/symbols.json")
_EXE = Path("data/PS.EXE")
_DECOMP = Path("decomp")


# ── headline projection ──────────────────────────────────────────────────
def _headline(rec: dict) -> dict:
    """Normalize a per-function verify record to the canonical headline.

    Accepts the rich ``decomp-verify --json`` per-function record (which
    spells the count ``diff_byte_count``) and returns the canonical
    ``{name, address, file, byte_diff, exact}`` plus the most useful
    diagnostic fields, leaving the full record under ``raw``.
    """
    byte_diff = rec.get("diff_byte_count")
    if byte_diff is None:
        byte_diff = rec.get("byte_diff", 0)
    return {
        "name": rec.get("name"),
        "address": rec.get("address"),
        "file": rec.get("file"),
        "byte_diff": byte_diff,
        "exact": byte_diff == 0,
        "size": rec.get("size"),
        "recomp_size": rec.get("recomp_size"),
        "diff_row_count": rec.get("diff_row_count"),
        "binir_shape": _compact_binir(rec.get("binir_shape_hint")),
        "run_ledger": _compact_ledger(rec.get("run_ledger")),
        "shape_distance": rec.get("shape_distance"),
        "rule_hints": rec.get("rule_hints"),
        "tail_merge": rec.get("tail_merge"),
        "const_audit": rec.get("const_audit"),
        "frame_hint": rec.get("frame_hint"),
    }


def _compact_ledger(rl: Optional[dict]) -> Optional[dict]:
    """Headline projection of the dual-marks run ledger: the verdict +
    the register-blind match counts.  ``regalloc_pure`` = every insn
    matches register-blind (whole diff is seats/slots/encoding -- do NOT
    restructure); ``shape_islands`` = statement-shape work, islands listed
    under ``raw.run_ledger.islands`` / ``c2 ledger <fn>``."""
    if not rl:
        return None
    return {
        "verdict": rl.get("verdict"),
        "matched": rl.get("matched"),
        "ps_total": rl.get("ps_total"),
        "islands": len(rl.get("islands") or []),
        "ps_runs_divergent": rl.get("ps_runs_divergent"),
        "ps_runs_total": rl.get("ps_runs_total"),
    }


def _compact_binir(bs: Optional[dict]) -> Optional[dict]:
    """Headline projection of the binir-shape hint: the residue-class
    verdict + counts.  The full per-line divergences stay under ``raw``.
    ``lines_divergent == 0`` is the 'all N/N identical' (pure-regalloc)
    residue class."""
    if not bs:
        return None
    return {
        "verdict": bs.get("verdict"),
        "lines_compared": bs.get("lines_compared"),
        "lines_identical": bs.get("lines_identical"),
        "lines_divergent": bs.get("lines_divergent"),
    }


def _run_verify(**kwargs) -> dict:
    """Call ``decomp_verify`` in-process and return its structured result
    dict directly (the function returns it; no stdout round-trip).  The
    CLI echo + progress chatter are suppressed.  Defaults: json_out=True,
    non-strict."""
    import typer
    from c2.commands.decomp_verify import decomp_verify

    kwargs.setdefault("json_out", True)
    kwargs.setdefault("strict", False)
    kwargs.setdefault("strict_warnings", False)
    with contextlib.redirect_stdout(io.StringIO()), \
            contextlib.redirect_stderr(io.StringIO()):
        try:
            return decomp_verify(**kwargs) or {}
        except typer.Exit as exc:
            if exc.exit_code not in (0, None):
                raise
            return {}


# ── verify (the atom) ────────────────────────────────────────────────────
def _window_diff(rows: list, ctx: int = 2) -> list:
    """Windowed PS-vs-RC diff: the non-equal rows plus ``ctx`` lines of
    context, with long byte-identical runs collapsed to an elision marker
    (mirrors ``decomp-verify -v``)."""
    keep = [False] * len(rows)
    for i, r in enumerate(rows):
        if r.get("kind") != "equal":
            for j in range(max(0, i - ctx), min(len(rows), i + ctx + 1)):
                keep[j] = True
    out: list = []
    eliding = 0
    for i, r in enumerate(rows):
        if keep[i]:
            if eliding:
                out.append({"elided": eliding})
                eliding = 0
            out.append({"off": r.get("off"), "ln": r.get("ln"),
                        "kind": r.get("kind"),
                        "ps": (r.get("ps") or {}).get("asm"),
                        "rc": (r.get("rc") or {}).get("asm")})
        else:
            eliding += 1
    if eliding:
        out.append({"elided": eliding})
    return out


def verify(
    function: str,
    *,
    file: Optional[str] = None,
    symbols: Path = _SYMBOLS,
    exe: Path = _EXE,
    decomp: Path = _DECOMP,
    full: bool = False,
    diff: bool = False,
) -> dict:
    """Byte-diff verdict for one function (the most-run micro-query).

    Returns the canonical headline plus ``diff_byte_offsets`` and the
    full per-function record under ``raw``.  With ``diff=True`` also
    returns ``diff_view`` -- the windowed PS-vs-RC asm diff (Hard Rules
    #3/#5).  ``found`` is False when the function is not a compared
    FUNCTION in the build.
    """
    data = _run_verify(
        c_files=[Path(file)] if file else None,
        symbols_json=Path(symbols),
        exe_path=Path(exe),
        decomp_dir=Path(decomp),
        full=full,
        function=[function],
    )
    for rec in data.get("functions", []):
        if rec.get("name") == function:
            head = _headline(rec)
            head["found"] = True
            head["diff_byte_offsets"] = rec.get("diff_byte_offsets")
            head["win"] = _win_hint_for(function, rec.get("file"))
            if diff:
                head["diff_view"] = _window_diff(rec.get("rows") or [])
            head["raw"] = rec
            return head
    return {"name": function, "found": False, "byte_diff": None, "exact": False}


def _win_hint_for(function: str, file: Optional[str]) -> dict:
    """CAESAR2.EXE mapping hint for a function (cheap, no compile).  Surfaced
    in verify / diagnose / dossier so the agent knows the second byte oracle
    (``c2 win-verify`` / ``c2 win-decompile``) is available for it."""
    try:
        from c2.win_bytes import win_hint, tu_of
        tu = (Path(file).stem if file else None) or tu_of(function)
        return win_hint(function, tu)
    except Exception:
        return {"available": False, "win_va": None, "confidence": None}


# ── functions (per-file inventory) ──
def _resolve_src(file: str, decomp: Path) -> Path:
    """Accept 'action', 'action.c', or 'decomp/src/action.c'."""
    p = Path(file)
    if p.exists() and p.suffix == ".c":
        return p
    name = p.name
    if not name.endswith(".c"):
        name += ".c"
    return Path(decomp) / "src" / name


def functions(
    file: str,
    *,
    status: Optional[str] = None,
    symbols: Path = _SYMBOLS,
    exe: Path = _EXE,
    decomp: Path = _DECOMP,
) -> dict:
    """Categorized inventory of one decomp source file (exact / diffing /
    stub / missing).  Delegates to ``c2.commands.functions.functions_data``
    (so `c2 functions <file>` and this facade share one implementation)."""
    from c2.commands.functions import functions_data
    return functions_data(file, status=status, symbols=symbols, exe=exe,
                          decomp=decomp)


# ── const-audit (regalloc-invariant constant bugs) ──
def const_audit(function: str) -> dict:
    """Audit the immediate-constant multiset vs PS, regalloc-independent.
    Surfaces wrong literals / struct strides / off-by-one comparison
    boundaries / out-of-order __watcall args -- layer-1 shape bugs to fix
    before chasing regalloc."""
    from c2.commands.const_audit import _load_all, _audit_named

    ctx = _load_all()
    res = _audit_named(function, ctx)
    if res is None:
        return {"name": function, "found": False}
    out = {
        "name": function,
        "found": True,
        "n_div": res.get("n_div", 0),
        "clean": res.get("n_div", 0) == 0 and not res.get("arg_swap"),
        "arg_swap": res.get("arg_swap") or [],
        "channels": {},
    }
    for ch in ("cmp_threshold", "eq", "plain"):
        if ch not in res:
            continue
        ps = res[ch]["ps_only"]
        rc = res[ch]["rc_only"]
        d = {"ps_only": {hex(k): v for k, v in ps.items()},
             "rc_only": {hex(k): v for k, v in rc.items()}}
        if ch == "cmp_threshold":
            pset, rset = set(ps), set(rc)
            d["off_by_one"] = [hex(k) for k in sorted(pset)
                               if (k + 1 in rset or k - 1 in rset)]
        out["channels"][ch] = d
    return out


# ── diagnose (fused per-function Phase-3 triage) ──
# The logic now lives in the CLI command module `c2.commands.diagnose`
# (so `c2 diagnose <fn>` and this facade share one implementation).
def diagnose(
    function: str,
    *,
    file: Optional[str] = None,
    mac: bool = False,
    full: bool = False,
) -> dict:
    """The canonical per-function loop in one call: byte-diff verdict +
    shape concordance + regalloc-invariant constant audit, with a routed
    next-step.  ``mac`` defaults False (the Mac/JVM witness is slow).
    Delegates to ``c2.commands.diagnose.diagnose_data``."""
    from c2.commands.diagnose import diagnose_data
    return diagnose_data(function, file=file, mac=mac, full=full)


def _divergent_lines(rec: dict) -> list[dict]:
    """Aggregate the LOCATED shape divergences by PS -d1 source line -- the
    fix is constrained to these lines (correlate with c2 disasm L<n>).  Joins
    the ir layer (preferring the dual-marks run-ledger islands, which are
    attribution-exact at any function size; falling back to the byte-diff-
    aligned binir per-line comparison), width (signedness + byte<->dword)
    and seat (first divergent register) layers."""
    by_line: dict[int, list[dict]] = {}

    def add(ln, layer, detail):
        if ln is None:
            return
        by_line.setdefault(int(ln), []).append(
            {"layer": layer, "detail": detail})
    rl = rec.get("run_ledger") or {}
    islands = rl.get("islands") or []
    if islands:
        # attribution-exact ir divergences: one entry per island, anchored
        # at its first PS line (rc_lines named in the detail -- the edit
        # target in OUR source)
        for isl in islands:
            pls = isl.get("ps_lines") or []
            rls = isl.get("rc_lines") or []
            tags = "/".join(isl.get("tags") or [])
            rc_ref = ("our src " + ",".join(str(x) for x in rls)
                      if rls else "no RC counterpart")
            if pls:
                add(pls[0], "ir", f"[{tags}] island vs {rc_ref}"
                    + (f" (PS L{pls[0]}..L{pls[-1]})" if len(pls) > 1 else ""))
            elif rls:
                # RC-only island: no PS line to anchor -- use a sentinel row
                by_line.setdefault(-1, []).append(
                    {"layer": "ir",
                     "detail": f"[{tags}] RC-only island at {rc_ref} "
                               f"(our source adds statements PS lacks)"})
    else:
        for d in ((rec.get("binir_shape_hint") or {}).get("divergences") or []):
            add(d.get("line"), "ir", d.get("summary"))
    wr = rec.get("width_recon") or {}
    for sgroup in wr.get("signedness", []):
        for ex in sgroup.get("examples", [])[:2]:
            add(ex.get("ln"), "width",
                f"PS {ex['ps_form']} vs RC {ex['rc_form']} "
                + ("(signed in PS)" if ex.get("ps_signed") else "(unsigned in PS)"))
    for w in wr.get("width", [])[:4]:
        add(w.get("ln"), "width",
            f"byte<->dword PS {w['ps_width']}b/our {w['rc_width']}b")
    fd = (rec.get("seat_recon") or {}).get("first_divergence")
    if fd:
        add(fd.get("ln"), "seat", f"RC {fd['rc']} vs PS {fd['ps']}")
    return [{"line": ln, "issues": by_line[ln]} for ln in sorted(by_line)]


def _const_signal(c: dict) -> str:
    """Classify a const-audit result by how trustworthy 'not clean' is as a
    LAYER-1 source bug:
      * ``high``  -- cmp-boundary / equality / out-of-order-arg divergence:
        a real regalloc-INVARIANT bug; fix it first.
      * ``plain`` -- only the plain-immediate channel fired: regalloc
        register-reuse can masquerade as a missing literal here, so it is
        a low-confidence signal that must be confirmed against the diff.
      * ``clean`` -- no constant divergence.
    """
    if c.get("clean"):
        return "clean"
    if c.get("arg_swap"):
        return "high"
    ch = c.get("channels", {})
    if ch.get("cmp_threshold", {}).get("ps_only") or \
            ch.get("cmp_threshold", {}).get("rc_only"):
        return "high"
    if ch.get("eq", {}).get("ps_only") or ch.get("eq", {}).get("rc_only"):
        return "high"
    return "plain"


# ── worklist (dispatcher) ────────────────────────────────────────────────
def worklist(
    function: Optional[str] = None,
    *,
    status: Optional[str] = None,
    file: Optional[str] = None,
    win: Optional[str] = None,
    limit: int = 12,
    refresh: bool = True,
    new_rule: bool = False,
) -> dict:
    """Fused GO/PARK/lever verdict (corpus or single function).

    ``win='mapped'`` keeps only functions with a CAESAR2.EXE location (the
    second byte oracle is usable); ``win='unmapped'`` keeps only those
    without.  Each row carries a ``win`` hint regardless."""
    from c2.commands.worklist import worklist_data

    data = worklist_data(refresh=refresh, file=file)
    if win in ("mapped", "unmapped"):
        want = win == "mapped"
        data = {**data, "rows": [r for r in data["rows"]
                                 if bool((r.get("win") or {}).get("available")) == want]}
    if function is not None:
        # single-function verdict: keep the corpus envelope shape, filter rows
        data = {**data, "single": True,
                "rows": [r for r in data["rows"] if r.get("name") == function]}
    elif status:
        data = {**data,
                "rows": [r for r in data["rows"] if r.get("status") == status]}
    # Canonical `byte_diff` headline (worklist's native spelling is diff_bytes).
    for row in data["rows"]:
        if "byte_diff" not in row and "diff_bytes" in row:
            row["byte_diff"] = row["diff_bytes"]
    return data


# ── forge (targeted codegen-experiment harness) ──
def forge(
    function: str,
    file: str,
    *,
    presets: Optional[list] = None,
    depth: int = 1,
    jobs: int = 1,
    max_variants: int = 500,
    apply: bool = False,
    top: int = 10,
    stop_at_exact: bool = True,
    slug: Optional[str] = None,
) -> dict:
    """Run a forge experiment programmatically.

    Args:
        function: target function name (must exist in ``decomp/src/<file>``).
        file: source TU basename (e.g. ``controls.c``).
        presets: candidate-generator presets to register
            (default ``["tie_group"]``).  See `c2 forge ls-presets`.
        depth: cartesian-product depth (1=singletons, 2=pairs, ...).
        jobs: parallel workers.
        max_variants: hard cap on plans tried.
        apply: when the run finds a winner, also write it to the
            live source file as a text-preserving minimal patch.
        top: how many winning plans to report.
        stop_at_exact: stop the search on the first byte-exact plan.
        slug: optional name for the .c2-cache/forge-winners/<slug>/
            directory where minimal patches are saved (default: function
            name).

    Returns a JSON-friendly dict with the baseline scores, the top-N
    winning plans (each with a patch_path that can be applied via
    ``patch -p1``), and the saved-patch paths.
    """
    from c2.forge import Forge
    from c2.commands.forge import _emit_winners

    f = Forge(function, file=file)
    for p in (presets or ["tie_group"]):
        try:
            f.preset(p)
        except KeyError:
            return {"function": function, "error":
                    f"unknown preset {p!r}"}

    with contextlib.redirect_stdout(io.StringIO()), \
            contextlib.redirect_stderr(io.StringIO()):
        summary = f.run(mode=depth, jobs=jobs,
                        max_variants=max_variants,
                        progress=False, stop_at_exact=stop_at_exact)

    winners = summary.winners()
    winners.sort(key=lambda p: (p.score.shape_total, p.score.bytes))
    paths = _emit_winners(summary, slug or function, top)
    best = winners[0] if winners else None
    if apply and best is not None:
        f.apply(best.plan)
    return {
        "function": function, "file": file,
        "baseline": {
            "bytes": summary.baseline.bytes,
            "shape": summary.baseline.shape,
            "shape_total": summary.baseline.shape_total,
            "fix_next": summary.baseline.fix_next,
        },
        "candidates": summary.candidates_total,
        "plans_tried": len(summary.plans),
        "build_failures": summary.build_failures,
        "duplicates": summary.duplicates,
        "elapsed_s": round(summary.elapsed_s, 1),
        "top": [
            {
                "plan": pr.plan.name,
                "fingerprint": pr.plan.fingerprint,
                "shape_total": pr.score.shape_total,
                "bytes": pr.score.bytes,
                "shape_delta": pr.shape_delta,
                "bytes_delta": pr.bytes_delta,
                "byte_exact": pr.score.bytes == 0,
                "candidate_count": len(pr.plan.candidates),
            }
            for pr in winners[:top]
        ],
        "winner": (
            {
                "plan": best.plan.name,
                "fingerprint": best.plan.fingerprint,
                "shape_total": best.score.shape_total,
                "bytes": best.score.bytes,
                "shape_delta": best.shape_delta,
                "bytes_delta": best.bytes_delta,
                "byte_exact": best.score.bytes == 0,
                "patch_path": str(paths[0]) if paths else None,
            } if best else None
        ),
        "saved_paths": [str(p) for p in paths],
        "applied": bool(apply and best is not None),
    }


# ── disasm (already structured) ──────────────────────────────────────────
def disasm(
    function: str,
    *,
    size: Optional[int] = None,
    symbols: Path = _SYMBOLS,
    exe: Path = _EXE,
) -> dict:
    """PS.EXE disassembly rows for one function, with the ``-d1`` line
    column (``L``) preserved -- the witness of source structure."""
    from c2.commands.disasm import disasm_function

    start, sz, lines = disasm_function(
        function, size=size, symbols_json=Path(symbols), exe_path=Path(exe)
    )
    rows = [
        {
            "address": ln.address,
            "L": ln.line or None,
            "bytes": ln.bytes_.hex(),
            "mnemonic": ln.mnemonic,
            "ops": ln.op_str,
            "target": ln.target,
            "data_ref": ln.data_ref,
        }
        for ln in lines
    ]
    return {"name": function, "address": start, "size": sz, "rows": rows}


# ── shape-recon (already structured) ─────────────────────────────────────
def shape(
    function: str,
    *,
    mac: bool = False,
    rc: bool = True,
    symbols: Path = _SYMBOLS,
) -> dict:
    """Witness-reconciliation shape verdict.  ``mac`` defaults False (the
    Mac/JVM witness is the slow part); concordance + coverage are the
    headline correctness signal."""
    from c2.commands.shape_recon import build_skeleton, _skeleton_to_dict

    sk = build_skeleton(function, use_mac=mac, use_rc=rc, symbols_json=Path(symbols))
    if sk is None:
        return {"name": function, "found": False}
    d = _skeleton_to_dict(sk)
    return {
        "name": function,
        "found": True,
        "concordance": d.get("concordance"),
        "coverage": d.get("coverage"),
        "n_high": d.get("n_high"),
        "n_medium": d.get("n_medium"),
        "n_low": d.get("n_low"),
        "mac_aligned": d.get("mac_aligned"),
        "mac_total": d.get("mac_total"),
        "raw": d,
    }


# ── regtrace (ground-truth regalloc lens) ──
def regtrace_explain(
    function: str,
    *,
    file: Optional[str] = None,
) -> dict:
    """Trace the real Watcom 10.0a allocator and correlate it with the
    live decomp-verify diff, returning the named lever + verdict bucket
    (the messiest grep surface, structured).  SLOW: builds/queries the
    container -trace image.  Short-circuits if the function is already
    byte-exact."""
    from c2.commands.regtrace import regtrace as _regtrace, _extract_verdict

    out = io.StringIO()
    err = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            _regtrace(
                name=function, file=file, native=False, keep=False,
                json_out=False, table=False, explain=True, save_baseline=False,
                vs=False, il=False,
            )
        except SystemExit:
            pass
        except Exception as exc:  # noqa: BLE001
            return {"name": function, "found": False, "error": str(exc)}
    transcript = out.getvalue() + "\n" + err.getvalue()
    verdict = _extract_verdict(transcript)
    # the correlation section is the actionable part
    lines = transcript.splitlines()
    corr = []
    grab = False
    for ln in lines:
        if "diff x trace correlation" in ln:
            grab = True
        if grab and ln.strip():
            corr.append(ln.rstrip())
    # value-aligned PS<->RC seat diff (tooling gap #1): name the swapped
    # value(s) + the steerable lever.  The trace was just warmed above, so
    # _container_rows here hits the content-hash disk cache (offline).
    seat = None
    try:
        from c2.commands.regtrace import _container_rows, vs_ps_data
        src_file, start, end, rows, _n, _sm = _container_rows(function, file)
        seat = vs_ps_data(function, src_file, rows, start, end)
    except Exception:  # noqa: BLE001
        seat = None
    return {
        "name": function,
        "found": True,
        "bucket": verdict.get("bucket"),
        "flags": {k: verdict[k] for k in
                  ("type_width", "reg_swap", "swap_named", "outside")
                  if k in verdict},
        "regalloc": verdict.get("regalloc"),
        "seat_diff": seat,
        "correlation": corr,
        "transcript": transcript,
    }


# ── forge experiment catalogue ──
def _forge_exp_dir() -> Path:
    return Path("docs/codegen-experiments")


def _exp_docstring(path: Path) -> str:
    """Module docstring of an experiment file, without executing it."""
    import ast
    try:
        return ast.get_docstring(ast.parse(path.read_text())) or ""
    except Exception:  # noqa: BLE001
        return ""


def forge_list() -> dict:
    """Catalogue of forge experiments with one-line summaries.  See
    ``c2 forge ls`` for the CLI equivalent."""
    d = _forge_exp_dir()
    rows = []
    for p in sorted(d.glob("*.py")):
        if p.stem.startswith("_"):
            continue
        doc = _exp_docstring(p)
        summary = next((l.strip() for l in doc.splitlines() if l.strip()), "")
        rows.append({"slug": p.stem, "summary": summary})
    return {"count": len(rows), "experiments": rows}


def forge_presets() -> dict:
    """List built-in forge presets (the bulk candidate generators).

    Each preset walks the AST + source index and emits one Candidate
    per legal site of its transformation.  Combine multiple presets +
    targeted DSL hypotheses, then run at depth>=2 for the cartesian
    product.  See ``.pi/skills/forge/SKILL.md`` for the recipe.
    """
    from c2.forge import PRESETS
    return {"presets": sorted(PRESETS.keys())}


def forge_skill() -> dict:
    """Return the path to the forge pi-skill (the user guide)."""
    from c2.forge import skill_path
    return {"path": str(skill_path())}


# ── sibling (nearest byte-exact template / structural twin) ──
def sibling(
    function: str,
    *,
    mode: str = "asm",
    top: int = 10,
    cross_family: bool = False,
    status: str = "exact",
) -> dict:
    """Find the decompiled functions most like ``function`` — the proven
    byte-exact templates to copy the recovered shape from.

    * ``mode='asm'`` (default): fuzzy ASM siblings ranked by shingle
      overlap — the nearest already-byte-exact function(s).
    * ``mode='structure'``: structural twins sharing the prologue
      signature (pushes / frame / argc), ranked by opening-shape depth.
    * ``status``: which siblings count — ``exact`` (default, byte-exact
      templates), ``any`` (also diffing/written — use when there is no
      byte-exact relative), ``diff``, or ``written``.
    """
    from c2.commands.sibling import find_siblings, find_structure_twins

    fs = ({"exact", "diff", "written"} if status == "any"
          else {s.strip() for s in status.split(",") if s.strip()})

    if mode == "structure":
        twins = find_structure_twins(function, top_n=top,
                                     cross_family_only=cross_family,
                                     filter_status=fs)
        return {
            "name": function, "mode": "structure",
            "twins": [{"name": t.name, "status": t.status, "file": t.src_file,
                       "frame": t.frame, "argc": t.argc, "n_insns": t.n_insns,
                       "opening_prefix": t.opening_prefix,
                       "cross_family": t.cross_family} for t in twins],
        }
    hits = find_siblings(function, top_n=top, filter_status=fs)
    return {
        "name": function, "mode": "asm", "status": status,
        "siblings": [{"name": h.name, "score": round(h.score, 3),
                      "common": h.common, "status": h.status,
                      "file": h.src_file, "n_insns": h.n_insns} for h in hits],
    }


# ── dossier (the all-streams-at-once synthesis pane) ──
def dossier(
    function: str,
    *,
    mac: bool = False,
    win: bool = False,
    ghidra: bool = False,
    source: bool = True,
    width: int = 56,
) -> dict:
    """The richest single-function VIEW: PS asm + RC asm + RC source +
    binir IR aligned by offset, with a verdict header (mark alignment /
    IR-multiset / classification / const-audit), byte-exact siblings, and
    (with ``mac``) the Mac PPC decompile.  Returns the rendered pane as
    text — the 'all info streams at once' orientation.  The Mac
    source-shape oracle is shown BY DEFAULT when the per-fn decompile is
    cached (~instant); ``mac=True`` forces it even when uncached (~25s JVM
    warmup, then cached).
    """
    import typer
    from c2.commands.dossier import dossier as _dossier

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), \
            contextlib.redirect_stderr(io.StringIO()):
        try:
            # Mac is the source-shape oracle: show it by default when cached
            # (~instant); `mac=True` forces the decompile even when uncached
            # (~25s JVM).  Matches the CLI default.
            _dossier(name=function, no_mac=False, force_mac=mac,
                     no_win=False, force_win=win,
                     no_ghidra=not ghidra, no_source=not source, width=width)
        except typer.Exit as exc:
            if exc.exit_code not in (0, None):
                return {"name": function,
                        "error": f"dossier exited {exc.exit_code} "
                                 "(function not found?)"}
        except Exception as exc:  # noqa: BLE001
            return {"name": function, "error": str(exc)}
    return {"name": function, "text": buf.getvalue(),
            "win": _win_hint_for(function, None)}


# ── decompile (Ghidra C of the ACTUAL PS.EXE target) ──
def decompile(
    function: str,
    *,
    with_vars: bool = False,
    with_params: bool = False,
) -> dict:
    """Ghidra's C decompilation of a PS.EXE function — the C reconstruction
    of the ACTUAL target binary (the Watcom build we're matching), with
    PS's real global/function names from the 7,092-symbol DB.  The PS-side
    analogue of c2_mac (which decompiles the Mac build).  Runs through the
    live ghidra-cli bridge (read-only; never re-analyzes).  SLOW only on
    the first call (bridge warmup).
    """
    import subprocess

    argv = ["ghidra-cli", "decompile", function]
    if with_vars:
        argv.append("--with-vars")
    if with_params:
        argv.append("--with-params")
    try:
        r = subprocess.run(argv, capture_output=True, text=True, timeout=180)
    except FileNotFoundError:
        return {"name": function, "found": False,
                "error": "ghidra-cli not on PATH"}
    except subprocess.TimeoutExpired:
        return {"name": function, "found": False, "error": "ghidra-cli timed out"}
    out = r.stdout or ""
    # The cold-call bridge bootstrap may prepend non-JSON lines; locate the
    # JSON array.
    i = out.find("[")
    if i < 0:
        return {"name": function, "found": False,
                "error": (r.stderr or out or "no output")[-300:]}
    try:
        recs = json.loads(out[i:])
    except Exception:  # noqa: BLE001
        return {"name": function, "found": False,
                "error": "could not parse ghidra-cli output"}
    rec = next((x for x in recs if x.get("name") == function),
               recs[0] if recs else None)
    if not rec:
        return {"name": function, "found": False,
                "error": "function not in the PS.EXE Ghidra DB"}
    return {"name": function, "found": True, "address": rec.get("address"),
            "signature": rec.get("signature"), "code": rec.get("code")}


# ── mac-decompile (source-shape oracle) ──
def mac(function: str, *, raw: bool = False, timeout: int = 60) -> dict:
    """Ghidra decompile of a function from the Mac PPC build (compiled from
    the SAME source by CodeWarrior) -- the source-shape oracle (nesting,
    types, control flow) independent of Watcom codegen.  SLOW on first use
    (starts the JVM ~25s)."""
    import mac as macmod

    if macmod.prog is None:
        macmod.open()
    if macmod.func(function) is None:
        return {"name": function, "found": False,
                "error": "not present in the Mac PPC build "
                         "(inlined or build-specific)"}
    text = (macmod.decompile(function, timeout) if raw
            else macmod.decompile_clean(function, timeout))
    return {"name": function, "found": True, "source": text}


# ── win-decompile (x86 /Od source-shape oracle) ──
def win(function: str, *, timeout: int = 60) -> dict:
    """Ghidra decompile of a function from the Windows CAESAR2.EXE build
    (MSVC 4.0 /Od of the SAME engine source as the DOS Watcom PS.EXE).  Being
    x86 and unoptimized, it is often the MOST legible source-shape oracle:
    params named+typed, globals named, every statement explicit.  SLOW on
    first use (JVM + project build ~60s); disk-cached per function after."""
    import c2win

    text = c2win.decompile_cached(function, timeout)
    if text is None:
        return {"name": function, "found": False,
                "error": "not present / not mapped in the Windows build"}
    return {"name": function, "found": True, "source": text}


# ── win-verify (the CAESAR2.EXE byte oracle) ──
def win_verify(function: Optional[str] = None, *, file: Optional[str] = None,
               diff: bool = False) -> dict:
    """Byte-verify decompiled function(s) against the Windows CAESAR2.EXE
    build (MSVC 4.0 /Od of the SAME source as PS.EXE) -- the second,
    independent byte oracle.  Two figures: ``byte_diff`` (the oracle; 0 =>
    byte-exact) and ``struct_diff`` (difflib instruction-edit distance over
    reloc/imm-normalised mnemonics -- the workable figure, /Od-slot-shuffle
    insensitive).  Exactness is decided by a map-independent masked search,
    so a stale func-map never yields a false diff.  Pass ``diff:true`` for the
    aligned MSVC-vs-CAESAR2 asm rows (kind=equal|slot|struct).  Omit
    ``function`` (optionally with ``file``) for a summary.
    """
    from c2 import win_bytes as wb

    if not wb.WIN_EXE.exists():
        return {"error": f"CAESAR2.EXE not found at {wb.WIN_EXE}"}
    win = wb.load_win_image()

    def _vrow(v) -> dict:
        return {"name": v.name, "tu": v.tu, "status": v.status, "size": v.size,
                "byte_diff": v.byte_diff, "struct_diff": v.struct_diff,
                "insn_total": v.insn_total,
                "win_va": (f"0x{v.win_va:08x}" if v.win_va else None),
                "located_va": (f"0x{v.located_va:08x}" if v.located_va else None),
                "confidence": v.confidence}

    if function:
        tu = wb.tu_of(function)
        if tu is None:
            return {"name": function, "found": False,
                    "error": "no definition found in decomp/src"}
        ctu = wb.compile_tu(tu)
        if ctu.errors:
            return {"name": function, "found": False,
                    "error": f"{tu}.c failed to compile under MSVC",
                    "errors": ctu.errors[:6]}
        v = wb.verify_func(function, tu, win=win, ctu=ctu)
        out = {"found": True, **_vrow(v)}
        if diff and v.status == "diff":
            out["diff_rows"] = wb.aligned_diff(v)
        return out

    # file / whole-tree summary
    import glob as _glob
    if file:
        tus = [Path(file).stem]
    else:
        tus = sorted(Path(p).stem for p in _glob.glob(str(wb.SRC_DIR / "*.c"))
                     if not Path(p).stem.startswith("_"))
    counts = {"exact": 0, "diff": 0, "nomap": 0, "failed_tu": 0}
    diffs: list[dict] = []
    for tu in tus:
        ctu = wb.compile_tu(tu)
        if ctu.errors:
            counts["failed_tu"] += 1
            continue
        for name, _s, _e in ctu.funcs:
            v = wb.verify_func(name, tu, win=win, ctu=ctu)
            if v.status in counts:
                counts[v.status] += 1
            if v.status == "diff":
                diffs.append(_vrow(v))
    diffs.sort(key=lambda r: r["struct_diff"])
    return {"found": True, "file": file, "summary": counts, "diffs": diffs}


# ── line-compare (post-byte-exact-win shape check) ──
def line_compare(function: str) -> dict:
    """Compare PS vs RC ``-d1`` line streams for a BYTE-EXACT function
    (Hard Rule #8): byte-exact is necessary but not sufficient; this
    surfaces statement-order / split-merge divergence.  Only byte-exact
    functions have a line map."""
    from c2.commands.line_compare import compare_function, _to_json, SIDECAR_PATH

    if not SIDECAR_PATH.exists():
        return {"name": function, "found": False,
                "error": "no line-map sidecar -- run c2 decomp-verify once first"}
    sidecar = json.loads(SIDECAR_PATH.read_text())
    rec = sidecar.get(function)
    if rec is None:
        return {"name": function, "found": False,
                "error": "not in the byte-exact corpus (only byte-exact "
                         "functions carry a -d1 line map)"}
    result = compare_function(function, rec.get("file", ""))
    return {"name": function, "found": True, **_to_json(result)}


# ── CLI dispatch for the launcher: `python -m c2.toolapi <op> <json-args>`
def _main(argv: list[str]) -> int:
    if not argv:
        print(json.dumps({"error": "usage: toolapi <op> '<json-args>'"}))
        return 2
    op = argv[0]
    args = json.loads(argv[1]) if len(argv) > 1 and argv[1] else {}
    fn = {
        "verify": verify,
        "diagnose": diagnose,
        "const_audit": const_audit,
        "functions": functions,
        "worklist": worklist,
        "disasm": disasm,
        "shape": shape,
        "forge": forge,
        "forge_list": forge_list,
        "forge_presets": forge_presets,
        "forge_skill": forge_skill,
        "sibling": sibling,
        "dossier": dossier,
        "decompile": decompile,
        "mac": mac,
        "win": win,
        "win_verify": win_verify,
        "line_compare": line_compare,
        "regtrace_explain": regtrace_explain,
    }.get(op)
    if fn is None:
        print(json.dumps({"error": f"unknown op {op!r}"}))
        return 2
    try:
        result = fn(**args)
    except Exception as exc:  # noqa: BLE001 -- surface as structured error
        import traceback

        print(json.dumps({"error": str(exc), "type": type(exc).__name__,
                          "trace": traceback.format_exc()}))
        return 1
    print(json.dumps(result, default=str))
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(_main(sys.argv[1:]))

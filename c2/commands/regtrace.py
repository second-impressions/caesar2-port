"""c2 regtrace — trace the *real* Watcom 10.0a register allocator.

Compiles the whole real translation unit containing a decompiled function under
the container ``-trace`` image (`localhost/watcom-10.0a-wibo-trace`,
tools/patch_trace.py) -- exactly what decomp-verify compiles, so the target's
codegen is byte-identical -- and reads the ``~WV1`` register-allocation trace it
emits on stdout: every allocation decision with its savings, candidate class,
interference set, CountRegMoves ins-walk, AND the actual chosen register
(GiveBestReg's pick, captured at the `call FixInstructions` commit site as the
`rg` tag).  Decisions span the TU; the target is one function in it.
Lets a regalloc divergence be diagnosed from ground truth (the live allocator's
decisions) instead of guessed at with the permuter.  For PS.EXE's actual
register use of the same function, run `c2 disasm <name>` separately.

The QEMU/FreeDOS harness this used to run under was retired: the container trace
is a strict superset (it already carries the chosen register and the FindRegister
rover trace) and runs in dosemu2 without booting a guest.
See `docs/wcc386-re/wcc386-10.0a-regalloc-symbols.md`.

Usage:
    uv run c2 regtrace move_army
    uv run c2 regtrace move_army --file int_c2.c   # disambiguate
"""
from __future__ import annotations

import json
import re
import subprocess
import tempfile
from pathlib import Path

import typer

REPO = Path(__file__).resolve().parents[2]
SRC_DIR = REPO / "decomp" / "src"
INCLUDE_DIR = REPO / "decomp" / "include"

_ANNOT = re.compile(r"//\s*(FUNCTION|STUB):")


def _container_rows(name: str, file: str | None):
    """Run the real allocator on the TU containing ``name`` via the container
    ``-trace`` image (tools/patch_trace.py, ``~WV1`` on stdout) and adapt its
    per-conflict ``alloc`` entries to the row schema the report / --explain /
    --il path consumes.  Replaces the retired QEMU/FreeDOS harness:
    the container trace is a strict superset (it already carries the chosen
    register via ``rg``, savings/class via ``al``, interference via ``wr`` and
    the CountRegMoves ins-walk via ``gi``).

    Returns ``(src_file, start, end, rows, n_funcs, sortmeta)`` where
    ``sortmeta = {"presort": [...], "postsort": [...]}`` is the routine's
    SortConflicts ground truth (sl = ConfList LIFO before SortList, sa = the
    exact order GiveRegister iterates after).  The ``nm`` hook resolves
    each named conflict's source variable string in-compiler (SymGetPtr), so
    ``var`` is the real name (params/locals); anonymous temps stay ``None``.
    """
    from c2 import regalloc
    from c2.regalloc import reglists
    from c2.regalloc.trace import savecalc_savings
    src_file, start, end, _preamble = _find_function(name, file)
    n_funcs = len(_ANNOT.findall(src_file.read_text(errors="replace")))
    # content-hash disk-cached per-file trace (regalloc.file_trace): repeat
    # regtrace runs on an unchanged TU are OFFLINE.  (Previously this called
    # trace_compile directly -- a full container compile on EVERY invocation.)
    td = regalloc.file_trace(src_file, INCLUDE_DIR)
    routine = td["by_func"].get(name) or td["by_func"].get(name.rstrip("_"))
    rows = []
    for a in (routine or {}).get("alloc", []):
        dln = a.get("defline", 0) or 0
        named = a.get("nameclass") == 1   # N_MEMORY == has a user symbol
        rows.append({
            "fn": "GiveBestReg",
            "conf": int(a["conf"], 16) if isinstance(a["conf"], str) else a["conf"],
            "savings": a.get("savings", 0),
            "class": a.get("regclass"),
            "def_line_num": dln, "line_lo": dln, "line_hi": dln, "def_line": 0,
            "cand": reglists.order(a.get("regclass")),
            "chosen": a.get("reg_name"),
            "withregs": a.get("withregs", 0),
            "given_regs": a.get("given_regs", 0),
            # real source name from the nm hook; fall back to a @L<line> marker
            # for a named conflict the resolver couldn't name.
            "var": a.get("var") or (f"@L{dln}" if named and dln else None),
            "handle": 0,
            "range_len": None,
            "ins_walk": a.get("ins_walk", []),
            "tree_temp": 0, "tree_alt": 0,
            # memory-exile verdict (trace.py finalize, v29): masked /
            # worthprolog -- the row never committed and is stack-homed.
            "memory_exiled": a.get("memory_exiled"),
            "wp": a.get("wp"),
            "reg_name": a.get("reg_name"),
            # ce/cq ground truth (>= 2026-06 image): the per-candidate
            # CountRegMoves saves the REAL allocator computed at this pick,
            # and its final register.  Recorded, not re-derived -- these
            # supersede the legacy ins_walk model (_give_best_reg).
            "cand_scores": a.get("cand_scores"),
            # cv stream: CalcSavings per-block raw unit sums (Rule 126
            # lever) + the offline reconstruction (cross-check vs savings).
            "savecalc": (routine or {}).get("savecalc", {}).get(a["conf"], []),
        })
    base = td.get("loop_base")
    for r in rows:
        if r["savecalc"]:
            r["savecalc_savings"] = savecalc_savings(r["savecalc"], base)
    sortmeta = {"presort": (routine or {}).get("presort", []),
                "postsort": (routine or {}).get("postsort", [])}
    return src_file, start, end, rows, n_funcs, sortmeta


def _extract_verdict(txt: str) -> dict:
    """Classify a `regtrace --explain` transcript into a triage bucket by the
    correlation-section phrasings the explainer actually emits."""
    low = txt.lower()
    # A REAL width bug requires an actual truncation/extension divergence ROW
    # (one side masks/extends, the other doesn't).  Merely *listing* byte-class
    # "type-width conflict" candidates is NOT a width bug -- those values are
    # often register-half-swap or ComTail victims whose divergence is
    # elsewhere.  Worked false-positives (2026-06): try_this_citymap_square had
    # 0 truncation rows yet bucketed type-width (real residue = ComTail tail-
    # merge); get_population's byte counts were correctly typed (real residue =
    # frame).  Gate on the row line, not the candidate listing.
    type_width = "truncation/extension diverg" in low
    byte_class_only = (not type_width
                       and ("type-width conflict" in low or "rule 8/23/49" in low))
    reg_swap = "register-identity swap" in low
    outside = ("no register-class divergence" in low
               or "outside the regalloc model" in low
               or "register layout matches" in low
               or "instruction-selection" in low or "instruction selection" in low)
    # named-local swap (reorder-reachable) vs temp-only swap (hard).  The swap
    # detail lines read `our <reg> holds: <value>[sav=..]` -- a value that is
    # not '(temp)' is a named local.
    swap_named = False
    if reg_swap:
        for m in re.finditer(r"holds:\s*(.+)", txt):
            for tok in re.findall(r"([A-Za-z_]\w*)\[sav=", m.group(1)):
                if tok != "temp":
                    swap_named = True
                    break
    flags = {"type_width": type_width, "reg_swap": reg_swap,
             "swap_named": swap_named, "outside": outside,
             "byte_class_only": byte_class_only}
    # primary bucket, most-actionable first
    if type_width:
        bucket = "steerable: type-width (Rule 8/23/49)"
    elif reg_swap and swap_named:
        bucket = "steerable: reg-swap named"
    elif reg_swap:
        bucket = "hard: reg-swap (temps)"
    elif outside:
        bucket = "outside-regalloc (rules/instr-sel)"
    elif byte_class_only:
        bucket = ("outside-regalloc (byte-class values correctly typed, NO "
                  "truncation rows -- residue is layout/ComTail/frame, not width)")
    else:
        bucket = "unclassified"
    rline = next((l.strip()[:300] for l in txt.splitlines()
                  if l.strip().startswith("Regalloc:")), None)
    return {"bucket": bucket, "regalloc": rline, **flags}


def _diffing_functions() -> list[str]:
    """Names of all functions that currently byte-diff (via decomp-verify --json)."""
    p = subprocess.run(["uv", "run", "c2", "decomp-verify", "--json", "--no-strict"],
                       cwd=REPO, capture_output=True, text=True, timeout=600)
    data = json.loads(p.stdout)
    fns = [f for f in data.get("functions", []) if f.get("diff_byte_count", 0) > 0]
    fns.sort(key=lambda f: f.get("diff_byte_count", 0))   # easiest first
    return [f["name"] for f in fns]


def regtrace_sweep(
    functions: list[str] = typer.Argument(
        None, help="explicit function list; default = all diffing functions"),
    workers: int = typer.Option(
        0, "--workers", "-j",
        help="parallel workers (default = nproc-1); each is one KVM guest"),
    limit: int = typer.Option(0, "--limit", help="cap functions (0 = all)"),
    out: str = typer.Option("data/out/regtrace-triage.json", "--out",
                            help="summary JSON output path"),
):
    """Run `regtrace --explain` across many functions IN PARALLEL (reentrant-safe
    workers; each guest powers itself off so completion is process-exit, not a
    timer).  Persists a per-function triage verdict (steerable / manual /
    outside-regalloc) so we get the TRUE workable worklist instead of guessing
    from diff-row heuristics."""
    import os, time
    from concurrent.futures import ThreadPoolExecutor, as_completed
    nproc = os.cpu_count() or 4
    workers = workers or max(1, nproc - 1)
    fns = list(functions) if functions else _diffing_functions()
    if limit:
        fns = fns[:limit]
    typer.secho(f"[*] regtrace sweep: {len(fns)} functions, {workers} workers",
                fg="cyan", err=True)
    logdir = REPO / "data" / "out" / "regtrace-sweep-logs"
    logdir.mkdir(parents=True, exist_ok=True)

    def run_one(fn: str) -> dict:
        t0 = time.time()
        try:
            p = subprocess.run(
                ["uv", "run", "c2", "regtrace", fn, "--explain"],
                cwd=REPO, capture_output=True, text=True, timeout=600)
            txt = p.stdout + "\n=== stderr ===\n" + p.stderr
            (logdir / f"{fn}.log").write_text(txt)
            v = _extract_verdict(p.stdout + "\n" + p.stderr)
            v.update(fn=fn, secs=round(time.time() - t0, 1), rc=p.returncode)
            return v
        except subprocess.TimeoutExpired:
            return {"fn": fn, "secs": round(time.time() - t0, 1), "rc": -1,
                    "bucket": "timeout"}

    results, done = [], 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(run_one, fn): fn for fn in fns}
        for fut in as_completed(futs):
            r = fut.result()
            results.append(r)
            done += 1
            typer.secho(f"  [{done}/{len(fns)}] {r['fn']:32} {r.get('bucket','?'):34}"
                        f" {r.get('secs','?')}s", err=True)
            # persist incrementally so a crash mid-sweep keeps progress
            Path(REPO / out).write_text(json.dumps(results, indent=1))

    import collections
    buckets = collections.Counter(r.get("bucket", "?") for r in results)
    typer.secho("\n=== triage summary ===", fg="green", bold=True, err=True)
    for b, c in buckets.most_common():
        typer.secho(f"  {c:4}  {b}", err=True)
    typer.secho(f"\nwrote {out}  (+ per-fn logs in {logdir})", fg="green", err=True)
    Path(REPO / out).write_text(json.dumps(results, indent=1))

# hw_reg_set encodings (10.0a) -> register name; used to compute the chosen reg.
_REG_ENC = {
    "EAX": 0x1000003, "EDX": 0x80000c0, "EBX": 0x200000c, "ECX": 0x4000030,
    "ESI": 0x10000100, "EDI": 0x20000200, "EBP": 0x400, "ESP": 0x800,
    # word views (low word of the dword encodings)
    "AX": 0x3, "DX": 0xc0, "BX": 0xc, "CX": 0x30, "SI": 0x100, "DI": 0x200,
    # byte regs (OW v1 cgi86reg.h bit order)
    "AH": 0x1, "AL": 0x2, "BH": 0x4, "BL": 0x8,
    "CH": 0x10, "CL": 0x20, "DH": 0x40, "DL": 0x80,
}


def _chosen_reg(cand: list[str], withregs: int) -> str:
    """Greedy GiveBestReg pick (CountRegMoves==0 case): first candidate in the
    captured DoubleRegs priority order whose register is free in `with.regs`."""
    for c in cand:
        enc = _REG_ENC.get(c)
        if enc is not None and (enc & withregs) == 0:
            return c
    return cand[0] if cand else "?"


_CALLEE_SAVED = ("EBX", "ESI", "EDI", "EBP")


def build_holder_map(committed) -> dict[int, tuple[str, int]]:
    """committed: iterable of (reg_name, var, savings). Returns enc -> (var,sav)
    keeping the highest-savings holder per register bit-group."""
    holder: dict[int, tuple[str, int]] = {}
    for rn, var, sav in committed:
        enc = _REG_ENC.get(rn)
        if enc is None:
            continue
        if enc not in holder or sav > holder[enc][1]:
            holder[enc] = (var, sav)
    return holder


def spill_chain_hint(cand: list[str], sav_self: int,
                     holder: dict[int, tuple[str, int]]) -> str:
    """Explain WHY a memory-exiled value spilled and the displacement LEVER.

    A spilled value found no free register, so each candidate was held by an
    earlier (higher-savings) overlapping value -- read from the holder map.
    If a caller-saved reg is free yet the value still spilled, it spans calls
    (couldn't grab the free caller-saved reg) -> only callee-saved holders are
    real displacement targets.
    """
    held = []
    seen = set()
    for cnm in ("EAX", "ECX", "EDX", "EBX", "ESI", "EDI", "EBP"):
        if cnm not in cand:
            continue
        enc = _REG_ENC[cnm]
        hv = None
        for henc, (hvar, hsav) in holder.items():
            if henc & enc:
                hv = (hvar, hsav)
                break
        key = hv[0] if hv else cnm
        if key in seen:
            continue
        seen.add(key)
        held.append((cnm, hv))
    cross = any(hv is None and c not in _CALLEE_SAVED for c, hv in held)
    disp = [(c, hv) for c, hv in held
            if hv and (not cross or c in _CALLEE_SAVED)]
    parts = [f"{c}={hv[0]}({hv[1]})" for c, hv in held if hv]
    if not parts:
        return ""
    scope = "callee-saved " if cross else ""
    # A callee-saved reg with no NAMED holder, yet the value spilled, means that
    # reg is occupied by short-lived SCRATCH across the call(s) -- the real,
    # direct blocker (scratch isn't tracked as a conflict).
    free_callee = [c for c, hv in held if hv is None and c in _CALLEE_SAVED]
    cheap = min(disp, key=lambda x: x[1][1]) if disp else None
    if cross and free_callee:
        extra = (f", or shorten the cheapest holder {cheap[1][0]}({cheap[1][1]})'s"
                 f" range so it yields {cheap[0]}") if cheap else ""
        tail = (f"  LEVER: {'/'.join(free_callee)} is unheld but scratch-clobbered"
                f" across the call(s) -- so it spilled anyway. Free it: cut cross-call"
                f" scratch (CSE/reorder so no temp lives across the call){extra}")
    elif cheap is not None and sav_self >= cheap[1][1]:
        # The value OUT-RANKS a holder yet still spilled -> not a savings-rank
        # problem: its candidates were all masked at its def point. Its own
        # live range crosses everything (long-range / retval-funnel class).
        tail = (f"  LEVER: out-ranks holder {cheap[1][0]}({cheap[1][1]}) yet spilled"
                f" -> interference, NOT rank: every candidate is masked at its def."
                f" Shorten/split THIS value's live range (it crosses all candidates).")
    elif cheap is not None:
        # below all holders: reduce the cross-call register pressure.
        tail = (f"  LEVER: all {scope}holders out-rank sav={sav_self}; this value is the"
                f" lowest cross-call competitor, so it spills. Free a {scope}reg by"
                f" shortening the cheapest holder {cheap[1][0]}({cheap[1][1]})'s"
                f" call-spanning range (-> memory temp), reducing the count below the"
                f" {scope}reg budget")
    else:
        return ""
    return "        spilled because: " + " ".join(parts) + tail


# CountRegMoves opcodes (10.0a encoding; see regalloc-symbols.md).
# CG opcodes for the 1994 wcc386 binary, behaviorally decoded via isolated
# one-operation probe functions (see docs/wcc386-re § "CG opcode enum").  The
# low integer ops match the OW source enum exactly; MOV/compares are shifted
# down (the 1994 build has fewer float/intrinsic ops than the OW source).
_OP_MOV = 0x26
# commutative arithmetic/logic ops (CountRegMoves' "OP Rn,x => Rn" bonus):
# ADD, MUL, AND, OR, XOR (+ EXT_ADD/EXT_MUL extended forms).  Behaviorally
# confirmed; supersedes the earlier {0x04,0x05,0x08,0x0d,0x0e,0x0f} which was
# derived from a wrong opcode assumption (those are EXT_SUB/MUL/MOD/LSHIFT/...).
_OP_COMMUTATIVE = {0x01, 0x02, 0x05, 0x06, 0x09, 0x0a, 0x0b}


def _infer_conflict_value(walk: list[dict]) -> int:
    """Identify the value-pointer the conflict represents.

    The trace's ``gi`` records capture the ins_walk for the SELECTION-time
    CountRegMoves call, but the value-pointer field that OW v1 keys on
    (``conf->tree->name`` -- ``tree_temp`` / ``tree_alt`` in our schema) is
    not (yet) emitted by ``patch_trace.py`` so the captured value is 0.
    Without it, ``_count_reg_moves`` cannot identify which value the walk
    is scoring and every per-reg score collapses to 0.

    Recover the value-pointer heuristically: it is the name that appears
    MOST often as both a non-MOV result and a non-MOV operand within the
    walk -- compound RMW patterns (``r += x``, ``r <<= 16``, ``r = r + x``)
    cycle the conflict's value through both sides, while temps and
    constants appear on only one side.  Empirically (validated on
    ``get_buffer_ofset``, ``put_danger_flag``, ``floop_end`` traces) this
    matches the user-visible conflict variable in every byte-exact and
    diff function checked.

    Returns the inferred value pointer, or 0 if the walk is empty.
    """
    from collections import Counter
    score = Counter()
    for ins in walk:
        if ins["opcode"] in (_OP_MOV,):
            continue
        for k in ("op0", "op1", "result"):
            v = ins.get(k, 0)
            if v:
                score[v] += 1
    return score.most_common(1)[0][0] if score else 0


def _count_reg_moves(row: dict, reg_enc: int) -> int:
    """CountRegMoves(conf, reg) over the captured ins_walk: register-register
    moves assigning `reg_enc` to this conflict's value would eliminate.  Mirrors
    cg/c/regalloc.c::CountRegMoves (386 path).  MOV->+2, commutative OP->+1.

    The conflict value-pointer is recovered via ``_infer_conflict_value``
    when ``tree_temp`` / ``tree_alt`` are zero (the common case today --
    see that function's docstring).  The result-reg / operand-reg masks
    are ANDed with ``reg_enc`` because the captured `gi` records use
    ``hw_reg_set`` bitmasks (a single register is encoded as the bit, so
    EAX=0x1, EBX=0x4 etc.; the 0x01000000 high bit on result-reg of the
    return-MOV marks a calling-convention placement).
    """
    walk = row.get("ins_walk")
    if not walk:
        return 0
    V = {row.get("tree_temp", 0), row.get("tree_alt", 0)} - {0}
    if not V:
        inferred = _infer_conflict_value(walk)
        if inferred:
            V = {inferred}
    if not V:
        return 0
    count = 0
    for ins in walk:
        op, res, rr = ins["opcode"], ins["result"], ins["result_reg"]
        o0, o0r, o1, o1r = ins["op0"], ins["op0_reg"], ins["op1"], ins["op1_reg"]
        if op == _OP_MOV:
            # Use mask-AND not equality: result_reg in gi records is a
            # hw_reg_set bitmask, sometimes with the 0x01000000 calling-
            # convention bit set on top.  Mask equality (``rr == enc``) is
            # WRONG when the high bit is set (the previous implementation
            # silently returned 0 in those cases -- the very cases that
            # bias toward EAX as the return register).
            if (o0 in V and (rr & reg_enc)) or (res in V and (o0r & reg_enc)):
                count += 2
        elif op in _OP_COMMUTATIVE:
            if (rr & reg_enc) and (o0 in V or o1 in V):
                count += 1
            elif res in V and ((o0r & reg_enc) or (o1r & reg_enc)):
                count += 1
    return count


def _give_best_reg(row: dict) -> tuple[str, dict[str, int]]:
    """Full GiveBestReg model: among candidates free in with.regs, max
    CountRegMoves (ties -> candidate order).  Returns (reg, {reg: crm>0})."""
    wr = row.get("withregs", 0)
    best, best_saves, scores = "MEM", -1, {}
    for c in row.get("cand", []):
        e = _REG_ENC.get(c)
        if e is None or (e & wr):
            continue
        s = _count_reg_moves(row, e)
        if s:
            scores[c] = s
        if s > best_saves:
            best, best_saves = c, s
    return best, scores


def _gb_pick_scores(row: dict) -> tuple[str, str, dict[str, int]]:
    """Ground-truth GiveBestReg pick + per-candidate CountRegMoves scores.

    The trace records what the REAL 10.0a allocator did: ``reg_name`` is the
    register GiveBestReg actually returned, and ``cand_scores`` is the
    per-candidate CountRegMoves saves it computed at that pick (ce/cq probes).
    These are recorded ground truth, so they SUPERSEDE the legacy ins_walk
    re-derivation (``_give_best_reg``), which predates the cand_scores probe
    and mis-scores move-elimination picks -- e.g. an arg-N value coalesced
    into arg-N's register (put_x3_area's tgfx_b -> ECX scored ECX:22, but the
    legacy walk model returned EBX:8, contradicting both the recorded reg_name
    AND the certified crm10a_v2 chain).  This bug fed the conflict table's CRM
    column and the ``our <reg> holds:`` diff correlation a wrong seat.

    Returns ``(greedy, pick, scores)``:
        greedy -- naive first-free candidate (the CountRegMoves==0 pick)
        pick   -- the register actually chosen (reg_name) when recorded
        scores -- ``{cand: saves}`` from the recorded cand_scores
    Falls back to the legacy ins_walk model only for pre-cand_scores images.
    """
    greedy = _chosen_reg(list(row.get("cand", [])), row.get("withregs", 0))
    cs = row.get("cand_scores")
    pick = row.get("reg_name")
    if cs and pick in _REG_ENC:
        scores = {e["cand"]: e["saves"] for e in cs if e.get("saves")}
        return greedy, pick, scores
    # legacy fallback: old trace image without the ce/cq cand_scores probe
    crm_pick, lscores = _give_best_reg(row)
    lpick = crm_pick if (lscores and crm_pick != greedy) else greedy
    return greedy, lpick, lscores


# CG opcode -> name for the 1994 wcc386 binary, behaviorally decoded via
# isolated one-operation probe functions (docs/wcc386-re § "CG opcode enum").
# Low integer ops 0x01-0x0d match the OW source enum exactly; NEG/COMPLEMENT,
# CONVERT, MOV and the compare block (0x30-0x35) are confirmed by probes.
# 0x4b is a pure block-boundary marker (no operands); 0x2c is a result-only def
# (load/leaf) that appears once per value.  Unconfirmed values show op0xNN.
# Enum reconstructed for the 10.0a build by anchoring on values confirmed in
# the binary (MOV=0x26 and BLOCK=0x4b from CountRegMoves @0x60080's `cmp dl`
# tests; ADD..LSHIFT=0x01..0x0d; compares 0x30..0x35) and walking the OW
# opcode-enum *structure* across the gaps.  NOTE: 10.0a's enum differs from
# OpenWatcom V1's (V1 added Alpha byte-ops + extra math IFUNCs later, which
# shift everything past MOV), so V1's numeric values are NOT usable directly.
# The math IFUNC slots (0x0e-0x10 binary, 0x13-0x20 unary) essentially never
# appear in this integer-only codebase; the rare 0x10/0x18/0x1c seen in traces
# are those (P5DIV/FABS/COSH) and are harmless. CALL=0x36 sits right after the
# compare block (OW OP_CALL = LAST_OP_WITH_LABEL) and returns in EAX, matching
# the `op0x36 EAX <- EAX,..` IL renders. The call/parm region 0x27-0x2f
# (CALL_INDIRECT/PUSH/POP/PARM_DEF/SELECT + 2 ops 10.0a has that V1 dropped)
# still needs behavioural probing; 0x2c is the once-per-value leaf/load def.
_OPCODES = {
    0x00: "NOP",
    0x01: "ADD", 0x02: "EXT_ADD", 0x03: "SUB", 0x04: "EXT_SUB", 0x05: "MUL",
    0x06: "EXT_MUL", 0x07: "DIV", 0x08: "MOD", 0x09: "AND", 0x0a: "OR",
    0x0b: "XOR", 0x0c: "RSHIFT", 0x0d: "LSHIFT",
    0x10: "IFUNC", 0x11: "NEG", 0x12: "CMPL", 0x18: "FABS", 0x1c: "COSH",
    0x24: "CONVERT", 0x26: "MOV", 0x2c: "LEAF",
    0x30: "CMP_EQ", 0x31: "CMP_NE", 0x32: "CMP_GT", 0x33: "CMP_LE",
    0x34: "CMP_LT", 0x35: "CMP_GE", 0x36: "CALL", 0x4b: "BLOCK",
}
_ENC_NAME = {v: k for k, v in _REG_ENC.items()}
# byte/word-class hw_reg_set encodings (low bits) -> name
# Byte-pair bit order per OW v1 cgi86reg.h (H = LOW bit); corrected 2026-06-10.
_ENC_NAME.update({0x1: "AH", 0x2: "AL", 0x4: "BH", 0x8: "BL", 0x10: "CH",
                  0x20: "CL", 0x40: "DH", 0x80: "DL",
                  0x3: "AX", 0xc: "BX", 0x30: "CX", 0xc0: "DX",
                  0x100: "SI", 0x200: "DI"})


# operand arity per opcode: how many value operands the instruction really has.
# Renders only that many, so a unary MOV/CONVERT/NEG doesn't print a phantom
# op1 left over from the range walk reading a stale slot.
_OP_ARITY = {0x4b: 0, 0x00: 0,                         # BLOCK NOP
             0x2c: 0, 0x36: 0,                         # LEAF (result-only) CALL
             0x11: 1, 0x12: 1, 0x24: 1, 0x26: 1}        # NEG CMPL CONVERT MOV
# everything else (arithmetic / logic / shifts / compares) is binary -> 2.


def _il_operand(handle: int, reg: int) -> str:
    """Render a CG operand: its register name if N_REGISTER, else the value
    handle.  An unknown reg encoding is a stale/past-range read -> '?'."""
    if reg:
        return _ENC_NAME.get(reg, "?")
    if handle:
        return f"t{handle:#x}"
    return "-"


def _emit_il(rows: list[dict], start: int, end: int, name: str) -> None:
    """Dump the captured CG instruction list (the 'frontend IL' the allocator
    works on) for the target function's values: per conflict, its def+use
    instructions decoded (opcode, result, operands, source line)."""
    import typer as _t
    table = _conflict_table(rows, start, end)
    # map conf id -> raw row (for ins_walk, which the table doesn't carry)
    byid = {}
    for r in rows:
        if r.get("fn") == "GiveBestReg" and r["conf"] not in byid:
            byid[r["conf"]] = r
    _t.secho(f"\n  --- CG IL dump: {name} ({len(table)} values) ---",
             fg="green", bold=True)
    _t.secho("  (per value: line  OPCODE  result <- operands.  Operands: a "
             "physical register name when already assigned, else tN = an "
             "anonymous CG temporary (no source name); '?' = stale slot.)",
             fg="bright_black")
    for c in table:
        raw = byid.get(c.get("conf"))
        var = c.get("var") or "(temp)"
        ln = c.get("def_line_num") or c.get("def_line") or "-"
        _t.echo(f"  value {var:<14} line {ln!s:<4} savings={c['savings']:<5} "
                f"chosen={c['chosen']}  class={(c['cand'][:1] or ['?'])[0]}")
        walk = raw.get("ins_walk", []) if raw else []
        seen = set()
        uniq = []
        for ins in walk:
            op = ins.get("opcode", 0)
            # valid CG opcodes are a small enum (< 0x80); larger = the walk read
            # past the (capped) range into non-instruction memory -> skip garbage.
            if op == 0 or op >= 0x80:
                continue
            opn = _OPCODES.get(op, f"op{op:#x}")
            arity = _OP_ARITY.get(op, 2)
            res = _il_operand(ins.get("result", 0), ins.get("result_reg", 0))
            o0 = _il_operand(ins.get("op0", 0), ins.get("op0_reg", 0)) if arity >= 1 else "-"
            o1 = _il_operand(ins.get("op1", 0), ins.get("op1_reg", 0)) if arity >= 2 else "-"
            key = (opn, res, o0, o1)
            if key in seen:           # collapse loop-walk cycles to unique insns
                continue
            seen.add(key)
            uniq.append(key)
        for opn, res, o0, o1 in uniq[:12]:
            rhs = ", ".join(x for x in (o0, o1) if x != "-") or "-"
            _t.echo(f"      {opn:<8} {res} <- {rhs}")
        if len(uniq) > 12:
            _t.secho(f"      ... (+{len(uniq) - 12} more unique)", fg="bright_black")


def _attribution_reliable(rows: list[dict], start: int, end: int) -> tuple[bool, int]:
    """Is the target function actually represented in the trace's line info?
    The compiler's per-instruction line_num caps out in large TUs (e.g. map.c
    tops out ~line 4438), so functions beyond that have NO correct attribution
    and the line_lo/hi fallback silently pulls in other functions' conflicts.
    Returns (reliable, max_line_seen).  Unreliable when the function's start is
    above every line the trace recorded."""
    gbr = [r for r in rows if r.get("fn") == "GiveBestReg"]
    if not gbr:
        return False, 0
    max_line = max(max(r.get("def_line_num", 0), r.get("line_lo", 0),
                       r.get("line_hi", 0)) for r in gbr)
    # reliable if at least one conflict's def line lands inside the function,
    # or the function's lines are within the trace's recorded line span.
    in_fn = any(start <= r.get("def_line_num", 0) <= end for r in gbr)
    return (in_fn or start <= max_line), max_line


def _conflict_table(rows: list[dict], start: int, end: int) -> list[dict]:
    """Build the enriched, allocation-ordered conflict table for the target
    function: one entry per distinct conflict (FIRST sighting) with the model's
    chosen register.  Shared by the report, --explain, --baseline and --vs."""
    gbr = [r for r in rows if r.get("fn") == "GiveBestReg"]

    def _intarget(r):
        # precise: the conflict's def-instruction source line (when captured)
        # must fall inside the function; fall back to the coarse LINE_LO/HI
        # bracket only when the def instruction had no line info.
        dln = r.get("def_line_num", 0)
        if dln:
            return start <= dln <= end
        lo = min(r.get("line_lo", 0), r.get("line_hi", 0))
        hi = max(r.get("line_lo", 0), r.get("line_hi", 0))
        return lo <= end and hi >= start
    tgt = [r for r in gbr if _intarget(r)]
    show = tgt if tgt else gbr
    byconf, order, maxsav = {}, {}, {}
    for r in show:
        c = r["conf"]
        if c not in order:
            order[c] = len(order)
        maxsav[c] = max(maxsav.get(c, 0), r.get("savings", 0))
        if c not in byconf:        # FIRST sighting sticks (validated)
            byconf[c] = r
    table = []
    for r in sorted(byconf.values(), key=lambda r: order[r["conf"]]):
        cand = list(r["cand"])
        greedy, pick, scores = _gb_pick_scores(r)
        var = r.get("var") or (f"t{r['handle']:#x}" if r.get("handle") else None)
        table.append({
            "conf": r["conf"],
            "order": order[r["conf"]],
            "var": var,
            "def_line": r.get("def_line") or 0,
            "def_line_num": r.get("def_line_num") or 0,
            "savings": maxsav.get(r["conf"], r.get("savings", 0)),
            "range_len": r.get("range_len"),
            "cand": cand,
            "greedy": greedy,
            "chosen": pick,          # model pick (validated 3/3)
            "crm_scores": scores,
            "withregs": r.get("withregs", 0),
            # carried for the model inversion (CountRegMoves needs the walk)
            "ins_walk": r.get("ins_walk", []),
            "tree_temp": r.get("tree_temp", 0),
            "tree_alt": r.get("tree_alt", 0),
            # cv stream (when the rows came from the container trace):
            # CalcSavings per-block breakdown, for the --vs savings-delta view.
            "savecalc": r.get("savecalc") or [],
            # bt ground truth (>= 2026-06-11 image): GivenRegisters at THIS
            # conflict's GiveBestReg entry.  0/absent on older traces.
            "given_regs": r.get("given_regs", 0),
        })
    return table


def _mask_regs(mask: int) -> str:
    """Render an hw_reg_set mask as the largest covering register names."""
    names = []
    for nm in ("EAX", "EDX", "EBX", "ECX", "ESI", "EDI", "EBP", "ESP",
               "AX", "DX", "BX", "CX", "SI", "DI",
               "AH", "AL", "BH", "BL", "CH", "CL", "DH", "DL"):
        enc = _REG_ENC[nm]
        if mask & enc == enc:
            names.append(nm)
            mask &= ~enc
    if mask:
        names.append(f"{mask:#x}")
    return "+".join(names) or "-"


def given_regs_drift(table: list[dict]) -> list[str]:
    """Cross-check the bt ground-truth GivenRegisters snapshots against the
    union-of-earlier-picks inference (allocation order over ``table``).

    ``table`` MUST be the RAW alloc stream in TRACE ORDER (one row per al
    record, re-presentations included).  Running it over the deduped /
    line-filtered ``_conflict_table`` produces FALSE POSITIVES: dedup drops
    re-presentation picks and permutes positions, so the inference misses
    registers the stream actually committed (learned on sa12_army_sail_home:
    table-level "drift" at allocs #6/#7, stream-level clean).

    Agreement is the precondition for simple order reasoning: every register
    in GivenRegisters at conflict N's allocation must be explained by the
    picks of conflicts 0..N-1 (plus the pre-existing seed at conflict 0 --
    parm-reg rq commits fire before the first GiveBestReg).  DISAGREEMENT is
    the signature of RegAlloc retry rounds (CONFLICT_ON_HOLD reseats /
    MoreConflicts re-bitting): allocation ran in more rounds than the single
    al-order walk, so tie-group / seeder reasoning over this table is
    unreliable -- run the H2 layer-1 check (offline-sort vs postsort)
    before trusting Rule 28a/115 levers.

    Returns warning lines (empty = clean or no ground truth in the trace)."""
    rows = [r for r in sorted(table, key=lambda r: r.get("order", 0))]
    if not any(r.get("given_regs") for r in rows):
        return []
    # seed = the FIRST conflict's snapshot (parm-reg rq commits fire before
    # the first GiveBestReg, so a nonzero start is normal, not drift).
    seed = rows[0].get("given_regs", 0)
    out: list[str] = []
    expected = seed
    first = True
    for r in rows:
        gt = r.get("given_regs", 0)
        # gt == 0 is indistinguishable from "no bt data for this row" (rq
        # rows carry none); only nonzero snapshots are checked.
        if gt and not first:
            extra = gt & ~expected
            missing = expected & ~gt
            if extra or missing:
                var = r.get("var") or "(temp)"
                bits = []
                if extra:
                    bits.append(f"unexplained {_mask_regs(extra)}")
                if missing:
                    bits.append(f"missing {_mask_regs(missing)}")
                out.append(
                    f"  given_regs DRIFT at alloc #{r.get('order')} ({var}): "
                    + ", ".join(bits)
                    + f"  [gt={gt:#x} inferred={expected:#x}]")
        first = False
        enc = _REG_ENC.get((r.get("chosen") or "").upper(), 0)
        expected |= enc
        if gt:
            expected |= gt    # resync: never re-report the same drift bit
    if out:
        out.append(
            "  ^ GivenRegisters ground truth disagrees with the "
            "union-of-earlier-picks model -> RegAlloc retry rounds "
            "(ON_HOLD reseats) are active in this function; tie-group / "
            "seeder order reasoning is NOT reliable here (H2 layer-1 "
            "check first).")
    return out


def _savecalc_brief(sc: list[dict]) -> str:
    """Compact CalcSavings breakdown: one `save[-cost]@d<depth>` term per
    contributing block, in CalcSavings walk order (the cv stream).  Empty
    string when the trace carries no cv data for this conflict."""
    parts = [f"{x['save']}-{x['cost']}@d{x['depth']}"
             if x["cost"] else f"{x['save']}@d{x['depth']}"
             for x in sc if x["save"] or x["cost"]]
    return "[" + " + ".join(parts) + "]" if parts else ""


def _conflict_key(c: dict) -> str:
    """Stable identity for a conflict across two trace runs.  Named source
    variables key on (var, def_line); temps key on a structural signature
    (allocation order + candidate-class + range) since their heap ids differ."""
    if c.get("var"):
        return f"v:{c['var']}@{c['def_line']}"
    # temps have no stable identity across runs (heap ids differ); key on a
    # position-INDEPENDENT structural signature so identical temps don't churn
    # when a named conflict is inserted/removed.  Collisions merge (acceptable;
    # the chosen-register histogram is the reliable temp-level signal).
    cls = (c["cand"][0] if c["cand"] else "?")
    return f"t:{cls}/r{c['range_len']}/s{c['savings']}"


def _diff_tables(base: list[dict], cur: list[dict]) -> list[str]:
    """Conflict-level delta between two traces (baseline -> current)."""
    from collections import Counter
    out = []
    bk = {_conflict_key(c): c for c in base}
    ck = {_conflict_key(c): c for c in cur}
    # named-conflict changes first (the actionable part)
    keys = sorted(set(bk) | set(ck),
                  key=lambda k: (not k.startswith("v:"), k))
    changed = added = removed = 0
    for k in keys:
        b, c = bk.get(k), ck.get(k)
        label = (b or c).get("var") or k
        if b and not c:
            out.append(f"  - {label:<16} REMOVED (was savings={b['savings']} "
                       f"chosen={b['chosen']})")
            removed += 1
        elif c and not b:
            out.append(f"  + {label:<16} ADDED (savings={c['savings']} "
                       f"chosen={c['chosen']})")
            added += 1
        else:
            is_temp = not (b.get("var") or c.get("var"))
            deltas = []
            savecalc_line = None
            if b["savings"] != c["savings"]:
                deltas.append(f"savings {b['savings']}->{c['savings']}")
                # pin the delta to a BLOCK: per-block CalcSavings breakdown
                # (cv stream).  A changed term names the block (by walk
                # position) and its loop depth = ONE statement whose
                # use/def/index unit count differs (Rule 126 workflow).
                bb = _savecalc_brief(b.get("savecalc") or [])
                cc = _savecalc_brief(c.get("savecalc") or [])
                if (bb or cc) and bb != cc:
                    savecalc_line = (f"      savecalc {bb or '[]'} -> "
                                     f"{cc or '[]'}")
            if b["chosen"] != c["chosen"]:
                deltas.append(f"chosen {b['chosen']}->{c['chosen']}")
            # alloc-order shift is noise for temps (absolute position moves when
            # a named conflict is inserted elsewhere); only meaningful for vars.
            if b["order"] != c["order"] and not is_temp:
                deltas.append(f"alloc-order #{b['order']}->#{c['order']}")
            if b["cand"][:1] != c["cand"][:1]:
                deltas.append(f"class {b['cand'][:1]}->{c['cand'][:1]}")
            if deltas:
                out.append(f"  ~ {label:<16} " + "  ".join(deltas))
                if savecalc_line:
                    out.append(savecalc_line)
                changed += 1
    # whole-function chosen-register histogram delta (catches temp shifts)
    hb = Counter(c["chosen"] for c in base)
    hc = Counter(c["chosen"] for c in cur)
    hist = []
    for reg in sorted(set(hb) | set(hc)):
        if hb[reg] != hc[reg]:
            hist.append(f"{reg} {hb[reg]}->{hc[reg]}")
    out.append("")
    out.append(f"  summary: {changed} changed, {added} added, {removed} removed; "
               f"conflicts {len(base)}->{len(cur)}")
    if hist:
        out.append("  chosen-register histogram delta: " + "  ".join(hist))
    if not (changed or added or removed):
        out.append("  (no conflict-level change -- the edit was regalloc-neutral "
                   "for this function)")
    return out


def _find_function(name: str, file_hint: str | None) -> tuple[Path, int, int, str]:
    """Locate `name`'s definition.  Returns (file, start_line, end_line, preamble).

    AST-based (cached pycparser front-end, `c_source.parse_c`): the function is
    a FuncDef node whose decl name matches, so extern/forward declarations in
    other TUs can never shadow the real definition (the old regex scan matched
    `extern void get_pseudo_map(int n);` in c2.c and traced the wrong TU).
    `start` is the definition's decl line, `end` the line before the next
    top-level node (or EOF); `preamble` is everything before the first
    function definition (includes + file-level externs/statics).
    """
    from c2.commands.c_source import parse_c
    from pycparser import c_ast

    files = sorted(SRC_DIR.glob("*.c"))
    if file_hint:
        files = [f for f in files if f.name == file_hint or f.stem == file_hint]
    for f in files:
        text = f.read_text(errors="replace")
        lines = text.splitlines()
        try:
            ast = parse_c(text, f.name)
        except Exception:
            continue                     # unparseable TU -- skip
        ext = list(ast.ext)
        first_def_line = next((n.coord.line for n in ext
                               if isinstance(n, c_ast.FuncDef) and n.coord), None)
        if first_def_line is None:
            continue
        for idx, node in enumerate(ext):
            if not (isinstance(node, c_ast.FuncDef) and node.decl.name == name):
                continue
            start = node.decl.coord.line
            # Preamble: everything before the first function definition, PLUS
            # any top-level declarations that sit BETWEEN functions before the
            # target (e.g. a mid-file `extern void get_pseudo_map(int n);`).
            # The single-function trace snippet (regtrace --native) compiles
            # preamble+body, so dropping those would change CallZap (Rule 37).
            pre_chunks = ["\n".join(lines[: first_def_line - 1])]
            for j, d in enumerate(ext):
                if (isinstance(d, c_ast.Decl) and d.coord
                        and first_def_line <= d.coord.line < start):
                    d_end = next((n2.coord.line - 1 for n2 in ext[j + 1:]
                                  if n2.coord and n2.coord.line > d.coord.line),
                                 len(lines))
                    pre_chunks.append("\n".join(lines[d.coord.line - 1: min(d_end, start - 1)]))
            preamble = "\n".join(pre_chunks)
            # end: line before the next top-level node that starts after the
            # body (comments between functions are attributed to the gap; the
            # closing brace is always before the next node's coord).
            end = len(lines)
            for nxt in ext[idx + 1:]:
                if nxt.coord and nxt.coord.line > start:
                    end = nxt.coord.line - 1
                    break
            return f, start, end, preamble
    raise typer.BadParameter(
        f"function {name!r} not found in decomp/src/"
        + (f" (file {file_hint})" if file_hint else ""))


def _param_names(name: str, src_file: Path) -> set:
    """Parameter identifiers of the function's DEFINITION (ABI-fixed order --
    __watcall seats params in eax/edx/ebx/ecx, so their decl order CANNOT be
    swapped as a tie lever).  Empty on any parse failure."""
    try:
        txt = src_file.read_text(errors="replace")
    except Exception:                              # noqa: BLE001
        return set()
    m = re.search(rf"^\w[\w \*]*\b{re.escape(name)}\s*\(([^;{{]*)\)\s*$",
                  txt, re.M)
    if not m:
        return set()
    out: set = set()
    for p in m.group(1).split(","):
        toks = re.findall(r"[A-Za-z_]\w*", p)
        if toks and toks[-1] != "void":
            out.add(toks[-1])
    return out


def vs_ps_data(name: str, src_file: Path, rows: list[dict],
               start: int, end: int) -> dict:
    """Structured value-aligned PS<->RC seat diff (tooling gap #1).

    RC side: regtrace's value->register table (the real allocator on our
    source).  PS side: the register permutation reconstructed from PS.EXE's
    own asm via the aligned decomp-verify diff (c2.regalloc.seat_recon).
    Returns a dict naming each swapped *value* with the steerable lever
    (equal-savings ConfBefore tie vs savings/shape).  Pure -- shared by the
    CLI report and the toolapi op."""
    from c2.regalloc.seat_recon import (seat_diff, type_width_diff, spill_diff,
                                        shape_distance_from, reg_to_fam)

    fn_rec = _fetch_fn_rec(name, src_file)
    diff_rows = (fn_rec or {}).get("rows") or []
    bdiff = (fn_rec or {}).get("diff_byte_count", 0)
    sr = (fn_rec or {}).get("seat_recon") or (seat_diff(diff_rows) if diff_rows
                                              else {"verdict": "empty"})
    wr = (fn_rec or {}).get("width_recon") or (
        type_width_diff(diff_rows) if diff_rows else {"count": 0})
    spl = (fn_rec or {}).get("spill_recon") or (
        spill_diff(diff_rows) if diff_rows else {})
    # fn_rec.shape_distance carries the IR layer (computed on internal rows in
    # the verify bundle); the fallback (no fn_rec) degrades to ir=0.
    dist = (fn_rec or {}).get("shape_distance") or shape_distance_from(
        sr, wr, spl, bdiff, 0)

    # RC value->register (+ savings) from the conflict table; tie = equal savings.
    table = _conflict_table(rows, start, end)
    rc_by_fam: dict[str, dict] = {}
    for t in table:
        var = t.get("var")
        reg = t.get("chosen") or t.get("greedy")
        if not var or not reg or var.startswith(("t", "(")):
            continue
        rc_by_fam.setdefault(reg_to_fam(reg), {"var": var,
                                               "savings": t.get("savings", 0)})
    sav_groups: dict[int, int] = {}
    for info in rc_by_fam.values():
        sav_groups[info["savings"]] = sav_groups.get(info["savings"], 0) + 1

    params = _param_names(name, src_file)
    named_swaps = []
    for sw in sr.get("swaps", []):
        info = rc_by_fam.get(reg_to_fam(sw["rc"]), {})
        sav = info.get("savings", 0)
        tied = sav > 0 and sav_groups.get(sav, 0) > 1
        val = info.get("var", "(temp)")
        is_param = val in params
        # Shape-aware lever: a tie is reachable in the ABSTRACT allocation
        # order, but source-reachability is NOT guaranteed (Direction-C
        # finding).  PARAM ties are ABI-fixed (decl order can't change);
        # use-order reorders that flip the abstract order often break the IR
        # (proven sub-source: city_test_for_road).
        if tied and is_param:
            lever = ("equal-savings tie on a PARAMETER -> decl-order is "
                     "ABI-FIXED (__watcall eax/edx/ebx/ecx); only use-order "
                     "(Rule 28a) can move it, and that often BREAKS the IR "
                     "shape -> frequently SUB-SOURCE (verify -- counter-"
                     "example: city_test_for_road)")
        elif tied:
            lever = ("equal-savings tie -> ConfBefore (Rule 28a use-order / "
                     "Rule 115 decl-order); reachable in the ABSTRACT order -- "
                     "confirm the reorder does NOT break the IR (decomp-verify)")
        else:
            lever = "savings/shape (live-range / type-width lever)"
        named_swaps.append({
            "value": val, "rc": sw["rc"], "ps": sw["ps"], "savings": sav,
            "tie": tied, "is_param": is_param, "lever": lever,
        })
    # Certified full-chain flip verdict per swap (2026-07-11): recomputed
    # masks + scores + pick (c2.regalloc.seatchain) name the lever CLASS
    # authoritatively -- supersedes the savings-tie heuristic above when
    # they disagree.  Evidence drill-in: `c2 seats <fn>`.
    try:
        import c2.regalloc as _regalloc
        from c2.regalloc.replay import REG_ENC as _RE
        from c2.regalloc.seatchain import certify_chain as _cc, \
            flip_analysis as _fa
        _td = _regalloc.file_trace(src_file, Path("decomp/include"))
        _rt = (_td.get("by_func") or {}).get(name)
        if _rt is not None:
            _cert = _cc(_rt)
            _alloc = [a for a in _rt.get("alloc") or []
                      if a.get("reg_name") in _RE]
            for sw in named_swaps:
                _cands = sorted(
                    (a for a in _alloc if a.get("reg_name") == sw["rc"]),
                    key=lambda a: (a.get("var") != sw["value"],
                                   -(a.get("savings") or 0)))
                if _cands:
                    _f = _fa(_cands[0], sw["ps"])
                    sw["chain_verdict"] = _f.get("verdict")
                    sw["chain_evidence"] = {
                        "mask_rows": len(_f.get("contributors") or []),
                        "winner_credits": len(_f.get("winner_credits") or []),
                    }
                else:
                    sw["chain_verdict"] = "no-alloc-row (rover/scratch)"
    except Exception:
        _cert = None
    return {
        "chain_identity": (f"{_cert['agree']}/{_cert['rows']}"
                           if _cert else None),
        "name": name, "verdict": sr.get("verdict", "?"),
        "coverage": sr.get("coverage", 0), "swaps": named_swaps,
        "type_width": wr, "spill": spl, "shape_distance": dist,
        "first_divergence": sr.get("first_divergence"),
    }


def _vs_ps_report(name: str, src_file: Path, rows: list[dict],
                  start: int, end: int, json_out: bool) -> None:
    """Print the value-aligned PS<->RC seat diff (tooling gap #1)."""
    data = vs_ps_data(name, src_file, rows, start, end)

    if json_out:
        typer.echo(json.dumps(data, indent=2))
        return

    typer.secho(f"\n=== PS<->RC seat diff: {name} ({src_file.name}) ===",
                fg="green", bold=True)
    tw = data.get("type_width") or {"count": 0}
    sp = data.get("spill") or {}
    dist = data.get("shape_distance") or {}
    frame_div = bool(sp) and sp.get("ps_frame") != sp.get("rc_frame")
    typer.secho(f"  verdict: {data['verdict']}   "
                f"(coverage {data['coverage']} reg-operands)", fg="cyan")
    if dist:
        from c2.regalloc.seat_recon import fmt_shape_layers as _flyr
        if dist.get("shape") == 0:
            typer.secho(f"  shape vs PS: MATCHES (ir/width/spill/seat all 0)  "
                        f"— residue is regalloc/encoding",
                        fg="green")
        else:
            typer.secho(f"  shape vs PS: {_flyr(dist)}  "
                        f"→ fix-next: {dist.get('fix_next', '?')}", fg="cyan")
    if (data["verdict"] in ("clean", "empty") and not data["swaps"]
            and not data["first_divergence"] and not tw.get("count")
            and not frame_div):
        typer.secho("  seats + types + frame agree with PS — no register / "
                    "width / spill divergence.", fg="green")
        return

    if data["swaps"]:
        header = f"  {'value':14} {'RC':5} {'PS':5} {'savings':>8}  verdict"
        typer.secho(header, fg="bright_black")
        typer.echo("  " + "-" * (len(header) - 2))
        for sw in data["swaps"]:
            typer.secho(f"  {sw['value']:14} {sw['rc']:5} {sw['ps']:5} "
                        f"{sw['savings']:8}  SWAP — {sw['lever']}", fg="yellow")
            if sw.get("chain_verdict"):
                ev = sw.get("chain_evidence") or {}
                extra = (f" ({ev['mask_rows']} mask rows)"
                         if ev.get("mask_rows") else
                         f" ({ev['winner_credits']} named credits)"
                         if ev.get("winner_credits") else "")
                typer.secho(f"  {'':14} chain verdict: {sw['chain_verdict']}"
                            f"{extra}  — c2 seats {data['name']}",
                            fg="cyan")
        if data.get("chain_identity"):
            typer.secho(f"  (full-chain identity {data['chain_identity']} — "
                        f"recomputed masks+scores+pick)", fg="bright_black")
    fd = data["first_divergence"]
    if fd:
        kind = ("first divergent seat" if data["swaps"]
                else "localized seat difference (not systematic)")
        typer.secho(f"\n  {kind} @ +{fd['off']:#06x}"
                    + (f" (L{fd['ln']})" if fd.get("ln") else "")
                    + f": value in RC {fd['rc']} is in PS {fd['ps']}",
                    fg="cyan")
        typer.secho(f"      PS: {fd['ps_asm']}", fg="bright_black")
        typer.secho(f"      RC: {fd['rc_asm']}", fg="bright_black")

    # type/width divergences (gap #3): a signed/byte local PS made differently
    if tw.get("count"):
        typer.secho("\n  --- type/width (signedness + byte<->dword) ---",
                    fg="green", bold=True)
        for s in tw.get("signedness", []):
            d = s["delta"]
            who = ("PS SIGNED, ours UNSIGNED -> make the local signed"
                   if d > 0 else
                   "PS UNSIGNED, ours SIGNED -> make the local unsigned")
            typer.secho(f"  {s['label']}: {abs(d)}x  ({who})", fg="yellow")
            for ex in s.get("examples", [])[:1]:
                loc = f" L{ex['ln']}" if ex.get("ln") else ""
                typer.secho(f"      e.g.{loc}  PS[{ex['ps_form']}] "
                            f"RC[{ex['rc_form']}]", fg="bright_black")
        for w in tw.get("width", [])[:3]:
            loc = f" L{w['ln']}" if w.get("ln") else ""
            typer.secho(f"  byte<->dword{loc}: PS {w['ps_width']}b vs our "
                        f"{w['rc_width']}b -- our local is wider  "
                        f"[PS: {w['ps_asm']}]", fg="yellow")

    # frame / spill divergence (gap #4): PS keeps more/fewer values on stack
    if frame_div:
        d = sp.get("slot_delta", 0)
        typer.secho("\n  --- frame / spill (live-set divergence) ---",
                    fg="green", bold=True)
        typer.secho(f"  PS frame {sp['ps_frame']}b ({sp['ps_byte_slots']} byte "
                    f"slots) vs our {sp['rc_frame']}b ({sp['rc_byte_slots']} "
                    "byte slots)", fg="yellow")
        if d > 0:
            typer.secho(f"  PS spills ~{d} MORE -- it holds byte intermediates "
                        "as named stack locals we keep in registers (larger "
                        "PS live-set).  Give those locals PS's width (above) + "
                        "keep them named/live; do not de-invent.", fg="yellow")
        elif d < 0:
            typer.secho(f"  WE spill ~{-d} more than PS -- shorten our "
                        "live-ranges (de-invent / reorder so a value dies "
                        "before the call).", fg="yellow")
    typer.secho("\n  (RC side = regtrace value->reg; PS side = seats "
                "reconstructed from PS.EXE asm. A tie verdict means the swap is "
                "reachable in the ABSTRACT tie-group order -- NOT necessarily "
                "via SOURCE: param ties are ABI-fixed, and a same-block-order "
                "equal-savings tie can be sub-source (the reorder that flips "
                "the abstract order may break the IR -- always confirm with "
                "decomp-verify).)", fg="bright_black")


def _fetch_fn_rec(name: str, src_file: Path) -> dict | None:
    """decomp-verify --json record for one function (diff + rows), or None."""
    try:
        res = subprocess.run(
            ["uv", "run", "c2", "decomp-verify", str(src_file), "-f", name,
             "--json", "--no-strict"],
            cwd=REPO, capture_output=True, text=True, timeout=300)
        data = json.loads(res.stdout)
        return next((x for x in data.get("functions", [])
                     if x.get("name") == name), None)
    except Exception:  # noqa: BLE001
        return None


def _emit_sort_panel(sortmeta: dict, rows: list[dict]) -> None:
    """SortConflicts ground truth: the sa stream (post-ShellSort ConfList =
    the EXACT order GiveRegister iterates) with equal-savings TIE GROUPS
    marked.  Members of one tie group are ordered solely by the ConfBefore
    name-pointer comparison -- the Rule 28a (use-order) / Rule 115
    (decl-order) source levers apply to exactly these neighbours and to
    nothing else.  presort (sl = AddConflictNode LIFO) is shown only when it
    disagrees with the offline ShellSort model (H2 cross-check)."""
    post = sortmeta.get("postsort") or []
    if not post:
        return
    # conf address -> var/chosen from the alloc rows
    info = {}
    for r in rows:
        info.setdefault(r["conf"], r)
    typer.secho("\n  --- SortConflicts order (sa = allocation queue, "
                "ground truth) ---", fg="green", bold=True)
    def _node(e):                      # sl/sa nodes are hex strings
        n = e["node"]
        return int(n, 16) if isinstance(n, str) else n
    groups: list[list[dict]] = []
    for e in post:
        if groups and groups[-1][0]["savings"] == e["savings"]:
            groups[-1].append(e)
        else:
            groups.append([e])
    pos = 0
    for g in groups:
        tie = len(g) > 1
        for e in g:
            r = info.get(_node(e), {})
            var = r.get("var") or "(temp)"
            chosen = r.get("chosen") or "-"
            mark = " <- TIE" if tie else ""
            # cv breakdown: which blocks (and loop depths) the savings
            # came from -- a PS-vs-recompile savings delta pins to one
            # block = one statement (Rule 126).
            bd = _savecalc_brief(r.get("savecalc") or [])
            bd = "  " + bd if bd else ""
            typer.echo(f"   {pos:<3} sav={e['savings']:<6} {var:<16} "
                       f"-> {chosen}{mark}{bd}")
            pos += 1
        if tie:
            names = ", ".join((info.get(_node(e), {}).get("var") or "(temp)")
                              for e in g)
            typer.secho(f"       ^ tie group ({names}): order decided by the "
                        "ConfBefore name-pointer -- Rule 28a/115 levers act "
                        "ONLY inside this group", fg="bright_black")


def _emit_explain(name: str, src_file: Path, conflicts: list[dict],
                  fn: dict | None, attribution_ok: bool = True,
                  max_line: int = 0, start: int = 0) -> None:
    """Correlate the function's decomp-verify diff with the allocator trace and
    print the per-divergence lever."""
    from c2.commands import regtrace_explain
    typer.secho("\n  --- diff x trace correlation (hard-case lever) ---",
                fg="green", bold=True)
    if not attribution_ok:
        typer.secho(
            f"  ⚠ UNRELIABLE: this function starts at line {start} but the "
            f"trace's line info only reaches line {max_line} (large-TU line-num "
            "cap).  The conflicts below are MIS-ATTRIBUTED from other functions; "
            "the levers are NOT trustworthy here.  (Works on small/medium TUs.)",
            fg="red")
    if not fn:
        typer.secho("  (function not found in decomp-verify output)", fg="yellow")
        return
    dbc = fn.get("diff_byte_count", 0)
    if dbc == 0:
        typer.secho("  function is already byte-exact -- nothing to explain.",
                    fg="bright_black")
        return
    typer.echo(f"  diff: {dbc} byte(s), {fn.get('diff_row_count', '?')} row(s)")
    for line in regtrace_explain.explain(conflicts, fn.get("rows", [])):
        typer.echo("  " + line)


_DECL_RE = re.compile(
    r"^([ \t]+)(int|unsigned int|short|unsigned short|char|unsigned char|long|"
    r"unsigned char\s*\*|char\s*\*)\s+([A-Za-z_]\w*)\s*(=[^;]*)?;\s*$")




def regtrace(
    name: str = typer.Argument(..., help="function to trace"),
    file: str = typer.Option(None, "--file", help="source file to disambiguate"),
    native: bool = typer.Option(
        False, "--native",
        help="use the podman -trace image engine instead of QEMU: prints the "
             "ACTUAL assigned register + savings + an H2 self-check (fast, no "
             "breakpoint). Complements the default rich view (--il needs the "
             "QEMU input capture: candidates, with.regs, IL, var names)."),
    keep: bool = typer.Option(False, "--keep", help="keep the staged work dir"),
    json_out: bool = typer.Option(False, "--json", help="emit raw JSON only"),
    table: bool = typer.Option(
        False, "--table",
        help="fast bare mode: show ONLY the conflict table (skip the diff "
             "correlation + PS<->RC seat diff, so no verify-diff fetch)."),
    explain: bool = typer.Option(
        False, "--explain",
        help="deprecated alias -- the diff correlation + PS<->RC seat diff is "
             "the DEFAULT now; pass nothing for it, or --table to skip it."),
    save_baseline: bool = typer.Option(
        False, "--baseline",
        help="save this trace's conflict table as the baseline for --vs"),
    vs: bool = typer.Option(
        False, "--vs",
        help="diff this trace's conflict table against the saved baseline "
             "(shows which conflicts' savings/chosen/alloc-order your edit moved)"),
    il: bool = typer.Option(
        False, "--il",
        help="dump the captured CG instruction list (frontend IL the allocator "
             "works on) for the target function's values"),
):
    """Trace the real 10.0a register allocator for a single function.

    By DEFAULT this prints the conflict table AND correlates it with the live
    decomp-verify diff: the named regalloc lever + the value-aligned PS<->RC
    seat diff (which value is seated in a different register than PS, plus the
    steerable verdict).  ``--table`` is the fast bare mode (table only, no
    verify-diff fetch).

    Data comes from the container ``-trace`` image (tools/patch_trace.py, ``~WV1``
    on stdout) -- the QEMU/FreeDOS harness has been retired.  ``--native`` is the
    same engine with the raw per-allocation dump."""
    if native:
        from c2.commands.regtrace_native import run_native
        run_native(name, file=file, json_out=json_out)
        raise typer.Exit()
    # Compile the WHOLE real TU under the trace image -- exactly what
    # decomp-verify compiles, so the target's codegen is byte-identical.  The
    # ~WV1 trace already carries every allocation decision incl. the chosen
    # register (`rg`); _container_rows adapts it to the row schema below.
    src_file, start, end, rows, n_funcs, sortmeta = _container_rows(name, file)
    typer.secho(f"[*] traced whole TU {src_file.name} ({n_funcs} functions; "
                f"{name} at lines {start}-{end}) via the -trace image",
                fg="cyan", err=True)

    if json_out:
        typer.echo(json.dumps(rows, indent=2))
        return

    # ---- report -----------------------------------------------------------
    typer.secho(f"\n=== register-allocation trace: {src_file.name} "
                f"(TU-wide, target {name}) ===", fg="green", bold=True)
    if not rows:
        typer.secho(f"  no decisions captured for {name} -- the function may be "
                    "trivial (no register conflicts), or the trace image did not "
                    "attribute it.  Check `c2 regtrace " + name + " --native`.",
                    fg="yellow")
    else:
        gbr = [r for r in rows if r.get("fn") == "GiveBestReg"]
        # Attribute by the per-function source-line globals the hook samples
        # (LINE_LO/LINE_HI bracket each function).  A conflict belongs to the
        # target iff [line_lo, line_hi] overlaps the target's source range.
        def _intarget(r):
            lo = min(r.get("line_lo", 0), r.get("line_hi", 0))
            hi = max(r.get("line_lo", 0), r.get("line_hi", 0))
            return lo <= end and hi >= start
        tgt = [r for r in gbr if _intarget(r)]
        show, scope = (tgt, name) if tgt else (gbr, "whole TU")
        # one row per distinct conflict (highest-savings sighting).  The records
        # are in GiveBestReg call order = the actual allocation order
        # (SortConflicts: savings desc, then ConfBefore name-pointer for ties),
        # so the first-seen index is the allocation sequence -- this is what
        # makes the equal-savings tie-break visible (the layer-3 lever).
        byconf = {}
        order = {}
        maxsav = {}
        for r in show:
            c = r["conf"]
            if c not in order:
                order[c] = len(order)
            maxsav[c] = max(maxsav.get(c, 0), r.get("savings", 0))
            # RegAlloc loops (ExpandOps/FixChoices/AssignConflicts) re-present a
            # conflict across passes.  Keep the FIRST sighting -- the initial
            # savings-desc assignment is the one that sticks.  Proven by the
            # end-to-end check (regalloc-predict-live.py): col's actual reg EDX
            # matches its first sighting (only EAX taken), NOT the later
            # higher-savings re-presentation (EAX+EDX taken -> EBX).
            if c not in byconf:
                byconf[c] = r
            # MEMORY-exile aggregation: the FIRST sighting's gb scores can
            # belong to an earlier RegAlloc pass; the conflict's HOME is
            # memory iff NO presentation ever committed.  Propagate the
            # final presentation's verdict onto the displayed row so the
            # greedy/CRM columns don't lie for stack-homed locals.
            if r.get("memory_exiled") and not any(
                    rr.get("reg_name") for rr in show if rr["conf"] == c):
                byconf[c]["memory_exiled"] = r["memory_exiled"]
                if r.get("wp"):
                    byconf[c]["wp"] = r["wp"]
        typer.echo(f"  {len(gbr)} GiveBestReg decisions in the TU; "
                   f"{len(byconf)} distinct conflicts in {scope}.")
        if not tgt:
            typer.secho("  (nothing attributed to the target by source line -- "
                        "showing whole TU)", fg="yellow")
        typer.secho("   #   variable      line  savings rng greedy CRM   candidates "
                    "(DoubleRegs order) | CountRegMoves scores",
                    fg="bright_black")
        # register -> (value, savings) holder map, from committed allocations.
        # Used to explain WHY a memory-exiled value spilled: which higher-
        # priority value holds each of its candidate registers (the
        # displacement target -- makes the spill quantitatively predictable).
        _committed = ((_r.get("reg_name") or _r.get("chosen"),
                       _r.get("var") or (f"t{_r['handle']:#x}" if _r.get("handle") else "(temp)"),
                       maxsav.get(_r["conf"], _r.get("savings", 0)))
                      for _r in byconf.values() if not _r.get("memory_exiled"))
        _holder = build_holder_map(_committed)

        def _spill_chain(row: dict) -> str:
            return spill_chain_hint(
                row.get("cand", []),
                maxsav.get(row["conf"], row.get("savings", 0)),
                _holder)

        # sort by allocation order (the sequence GiveBestReg actually ran);
        # within that, savings is non-increasing except across equal-savings
        # ties, where the ConfBefore name-pointer tie-break decides -- the
        # layer-3 lever (Rule 28a use-order / Rule 115 decl-order) is now
        # directly readable.
        for r in sorted(byconf.values(), key=lambda r: order[r["conf"]]):
            cand = r["cand"]
            # ground truth: reg_name + recorded cand_scores (ce/cq probes),
            # NOT the legacy ins_walk re-derivation which mis-scores
            # move-elimination picks.  greedy = naive first-free; the '*'
            # flag then marks a genuine move-elimination/tie-break.
            greedy, pick, scores = _gb_pick_scores(r)
            var = r.get("var") or (f"t{r['handle']:#x}" if r.get("handle")
                                    else "(temp)")
            # named decl line, else the def-instruction line (temps get one too)
            ln = r.get("def_line") or r.get("def_line_num") or 0
            sav = maxsav.get(r["conf"], r.get("savings", 0))
            rng = r.get("range_len", "-")
            sc = (" ".join(f"{k}:{v}" for k, v in scores.items())) if scores else ""
            flag = " *" if pick != greedy else ""
            # MEMORY exile (never committed): masked = every candidate
            # with.regs/except-excluded (live range crosses everything --
            # Rule 136 retval-funnel class); worthprolog = the gb winner
            # was declined (wp budget < cost).  Without this marker the
            # greedy/CRM columns LIE for stack-homed rows.
            mem = r.get("memory_exiled")
            if mem:
                wp = r.get("wp") or []
                det = next((f"budget {w['budget']} < cost {w['cost']}"
                            for w in wp if not w["ok"]), "all candidates masked")
                typer.echo(f"   {order[r['conf']]:<3} {var:<13} {ln or '-':<5} "
                           f"{sav:<7} {rng!s:<3} MEMORY({mem}: {det})")
                _chain = _spill_chain(r)
                if _chain:
                    typer.secho(_chain, fg="bright_black")
                continue
            typer.echo(f"   {order[r['conf']]:<3} {var:<13} {ln or '-':<5} "
                       f"{sav:<7} {rng!s:<3} {greedy:<6} {pick:<5}{flag} "
                       f"{','.join(cand)}{('  | ' + sc) if sc else ''}")
        typer.secho("  # = allocation order (SortConflicts: savings desc, then "
                    "ConfBefore name-pointer ties — use-order/decl-order are "
                    "the source levers, Rule 28a/115).  rng = ins-range length (loop-spanning "
                    "values cap at 64).  greedy = first free candidate "
                    "(CountRegMoves==0 pick); CRM = full GiveBestReg pick (max "
                    "CountRegMoves, '*' where it overrides greedy -- those are "
                    "the move-elimination tie-breaks).  Equal-savings + same "
                    "pick => layer-3 tie-break (Rule 28a commute the use, or "
                    "Rule 115 swap two locals' decl order); unequal savings => "
                    "live-range/source-shape lever.",
                    fg="bright_black")

        # ---- correlate the trace with the live diff (the DEFAULT rich view) -
        if not table:
            # use _conflict_table for PRECISE def_line_num attribution (the
            # report's byconf uses the coarse line_lo/hi bracket, which pulls in
            # out-of-function conflicts).  The table's `chosen` is the model pick
            # (live chosen hook off, but validated 3/3 vs the compiled disasm).
            target_conflicts = _conflict_table(rows, start, end)
            ok, maxln = _attribution_reliable(rows, start, end)
            fn_rec = _fetch_fn_rec(name, src_file)
            _emit_sort_panel(sortmeta, rows)
            # drift check over the RAW stream (NOT target_conflicts --
            # the deduped table false-positives; see given_regs_drift).
            _stream = [{"order": i, "var": rr.get("var"),
                        "chosen": rr.get("chosen"),
                        "given_regs": rr.get("given_regs", 0)}
                       for i, rr in enumerate(rows)]
            for warn in given_regs_drift(_stream):
                typer.secho(warn, fg="yellow")
            _emit_explain(name, src_file, target_conflicts, fn_rec,
                          ok, maxln, start)
            # value-aligned PS<->RC seat diff: names the swapped VALUE + the
            # steerable lever; shares the diff fetch + trace with _emit_explain.
            _vs_ps_report(name, src_file, rows, start, end, json_out=False)

        # ---- CG IL dump (--il) ----------------------------------------------
        if il:
            _emit_il(rows, start, end, name)

        # ---- differential trace (--baseline / --vs) -------------------------
        if save_baseline or vs:
            _btable = _conflict_table(rows, start, end)
            bdir = REPO / ".c2-cache"
            bdir.mkdir(exist_ok=True)
            bpath = bdir / f"regtrace-baseline-{name}.json"
            if save_baseline:
                bpath.write_text(json.dumps(_btable))
                typer.secho(f"\n  [baseline saved] {len(_btable)} conflicts -> "
                            f"{bpath.relative_to(REPO)}", fg="green")
            if vs:
                typer.secho("\n  --- conflict-level diff vs baseline ---",
                            fg="green", bold=True)
                if not bpath.exists():
                    typer.secho(f"  no baseline saved for {name} -- run with "
                                "--baseline first.", fg="yellow")
                else:
                    base = json.loads(bpath.read_text())
                    for line in _diff_tables(base, _btable):
                        typer.echo(line)

    typer.secho("  (for PS.EXE's actual register use, run: c2 disasm " + name + ")",
                fg="bright_black")

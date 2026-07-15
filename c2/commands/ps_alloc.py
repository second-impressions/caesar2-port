"""PS-side allocation verdict: can ANY conflict-creation-order change
reproduce PS's register bindings, and if so, which source lever reaches it?

The forward trace gives the full allocation table (conflict creation order
via ``cn``, pre-sort list via ``sl``, allocation walk via ``al``).  PS.EXE
gives the *bindings* ground truth: when the aligned diff shows a pure
register-identity swap (RuleHint "Reg swap"), the swapped register pair
tells us how PS bound the same conflicts.

This module replays SortConflicts' exact (unstable) ShellSort on the
pre-sort list with the tied pair's creation slots exchanged and reports:

  * REACHABLE  -- the creation-order swap transports the registers; the
    verdict names the two creations (slot index, defline, var/temp tag)
    and maps them to the known source lever:
      - same-instruction births (both conflicts die at the same ins ->
        op0/op1 sighting order): operand-order lever -- BUT for an (R,R)
        compare the emitted cmp operand order moves WITH the source order
        (G_RR2, Rule 103), so the swap costs a mirrored cmp.
      - two named locals: Rule 115 (decl order) / Rule 28a (use order).
  * NOT-TRANSPORTED -- exchanging the creations does NOT exchange the
    walk positions under the replayed ShellSort: the pair's relative
    order is pinned by the rest of the conflict list -> compiler-delta
    class (Rule 103 disposition).
  * MODEL-MISMATCH -- the ShellSort replay does not reproduce the actual
    allocation walk (H2 guard failed); the verdict would be a guess, so
    none is given.

Assumption (stated in the output): both conflicts pick registers by
DoubleRegs-first-free (empty CountRegMoves score).  When either has a
non-empty CRM table the transport is not guaranteed symmetric; the line
flags it so the agent re-checks with ``cgex.crm_scores``.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


_PAIR_RE = re.compile(r"([a-z]{2,3})\u2194([a-z]{2,3})")

# DoubleRegs order (dword class).  Byte-class ties are out of scope for v1
# (the Byte-reg swap classifier handles those separately).
_DWORD = ("EAX", "EDX", "EBX", "ECX", "ESI", "EDI", "EBP")


def _param_ids(src_file, func: str) -> set:
    """Parameter identifiers of ``func``'s DEFINITION (ABI-fixed order --
    __watcall seats params in eax/edx/ebx/ecx, so their decl order cannot be
    swapped as a Rule 115 tie lever).  Empty on any failure."""
    if not src_file:
        return set()
    from pathlib import Path
    try:
        txt = Path(src_file).read_text(errors="replace")
    except Exception:                              # noqa: BLE001
        return set()
    m = re.search(rf"^\w[\w \*]*\b{re.escape(func)}\s*\(([^;{{]*)\)\s*$",
                  txt, re.M)
    if not m:
        return set()
    out: set = set()
    for p in m.group(1).split(","):
        toks = re.findall(r"[A-Za-z_]\w*", p)
        if toks and toks[-1] != "void":
            out.add(toks[-1])
    return out


def swap_pairs_from_hints(hints, rows=None):
    """Extract unordered register pairs from per-row "Reg swap" RuleHints
    (summary text like ``register identity swap (ebx\u2194edx, edx\u2194ebx)``).

    Returns ``(binding_pairs, cmp_only_pairs)``: pairs seen on at least one
    non-``cmp`` row vs pairs seen ONLY on ``cmp`` rows.  A swap that appears
    exclusively on a mirrored ``cmp`` is the documented Rule 103 mislabel
    (registers actually match PS; only the (R,R) operand order differs) and
    must not be treated as a binding difference."""
    binding: set[frozenset[str]] = set()
    cmp_only: set[frozenset[str]] = set()
    for i, h in enumerate(hints):
        if h is None or getattr(h, "rule", None) != "Reg swap":
            continue
        if "register identity swap" not in getattr(h, "summary", ""):
            continue
        is_cmp = False
        if rows is not None and i < len(rows):
            # Internal row shape: "o"/"r" are InsnT tuples (off, size,
            # bytes, asm); JSON row shape: "ps"/"rc" dicts with "asm".
            row = rows[i]
            o = row.get("o")
            ps_asm = (o[3] if o else
                      ((row.get("ps") or {}).get("asm") or ""))
            is_cmp = ps_asm.lstrip().startswith(("cmp", "test"))
        for a, b in _PAIR_RE.findall(h.summary):
            p = frozenset((a.upper(), b.upper()))
            if len(p) != 2:
                continue
            (cmp_only if is_cmp else binding).add(p)
    return binding, cmp_only - binding


def _shell_sort(arr, before):
    """sortlist.c ShellSort, verbatim semantics (UNSTABLE; gap = len/2+adjust
    with the toggling adjust; bubble passes per gap until no swap)."""
    a = list(arr)
    n = len(a)
    if n < 2:
        return a
    gap = n
    adjust = 1
    while True:
        adjust = 0 if adjust else 1
        gap = gap // 2 + adjust
        while True:
            swapped = False
            for i in range(n - gap):
                if before(a[i + gap], a[i]):
                    a[i], a[i + gap] = a[i + gap], a[i]
                    swapped = True
            if not swapped:
                break
        if gap == 1:
            break
    return a


@dataclass
class PsAllocVerdict:
    func: str
    lines: list[str] = field(default_factory=list)


def detect(func: str, hints, rows=None, *,
           file: str | None = None,
           rover_pairs: set[frozenset] | None = None) -> PsAllocVerdict | None:
    """Build the PS-alloc verdict for ``func`` given the per-row RuleHints.

    ``rover_pairs``: register pairs the RISCify rover detector claims (its
    pick lists diverge on them).  Those diff rows are FindRegister SCRATCH
    seats (const stores / call-arg loads), not allocator bindings -- an
    allocator tie that happens to hold the same two registers is a
    DIFFERENT instruction set, and swapping its creation slots does NOT
    move the diff rows (proven on font_format_split: the s4010
    buf_idx/x_count tie already matched PS; the EBX<->ECX rows were the
    `x_is = 0` rover scratch).  Such pairs get a DEFER line instead of a
    REACHABLE verdict."""
    pairs, cmp_only = swap_pairs_from_hints(hints, rows)
    if not pairs and not cmp_only:
        return None
    if not pairs:
        ra, rb = sorted(next(iter(cmp_only)))
        return PsAllocVerdict(func, [
            f"PS-alloc: {ra}↔{rb} swap appears ONLY on a mirrored cmp/test "
            "row -- registers match PS; this is the (R,R) operand-order "
            "weld (G_RR2, Rule 103), NOT a binding swap.  Swapping the "
            "source compare flips the cmp but also the creation-slot tie "
            "(verify with the cn line)."])
    try:
        from c2.commands.regalloc_hints import _lookup
    except ImportError:
        return None
    r, _cost, _base = _lookup(func, file)
    if not r or not r.get("alloc") or not r.get("confs") or not r.get("presort"):
        return None

    alloc = r["alloc"]
    confs = r["confs"]
    presort = [(d["node"], d["savings"]) for d in r["presort"]]
    params = _param_ids(r.get("src_file"), func)

    # H2 guard: the replayed ShellSort must reproduce the actual walk.
    replay = [n for n, _ in _shell_sort(presort, lambda x, y: x[1] > y[1])]
    actual = [a["conf"] for a in alloc][: len(replay)]
    out: list[str] = []
    if replay != actual:
        return PsAllocVerdict(func, [
            "PS-alloc: MODEL-MISMATCH -- ShellSort replay does not reproduce "
            "the allocation walk (H2 guard); no verdict."])

    def _tag(a) -> str:
        return a.get("var") or f"t.{a['conf'][-4:]}"

    def _src_quote(*members) -> str:
        """Quote the source line(s) at the members' deflines.

        deflines refer to the COMPILED file == the stripped copy in
        .c2-cache/build/<basename> (function bodies are byte-identical
        to decomp/src there, only stub bodies differ).
        """
        sf = r.get("src_file")
        if not sf:
            return ""
        from pathlib import Path
        p = Path(".c2-cache/build") / Path(sf).name
        if not p.exists():
            return ""
        try:
            src = p.read_text(errors="replace").splitlines()
        except OSError:
            return ""
        seen, qs = set(), []
        for m in members:
            ln = m.get("defline")
            if not ln or ln in seen or ln > len(src):
                continue
            seen.add(ln)
            qs.append(f"L{ln}: `{src[ln - 1].strip()[:70]}`")
        return ("  " + "; ".join(qs)) if qs else ""

    for pair in sorted(pairs, key=sorted):
        ra, rb = sorted(pair)
        if ra not in _DWORD or rb not in _DWORD:
            continue
        if rover_pairs and pair in rover_pairs:
            out.append(
                f"PS-alloc: {ra}\u2194{rb} -- DEFER to the Rover lever: the "
                "RISCify rover's pick lists diverge on exactly this pair, so "
                "the diff rows are FindRegister scratch seats, not allocator "
                "bindings.  Any same-savings allocator tie holding these "
                "registers is a different instruction set; a creation-order "
                "swap will NOT move the diff rows.")
            continue
        # The tied pair: equal savings, same regclass, chosen regs == pair.
        cands = [a for a in alloc if a["reg_name"] in (ra, rb)]
        tied = [
            (x, y)
            for i, x in enumerate(cands)
            for y in cands[i + 1:]
            if x["savings"] == y["savings"]
            and x["regclass_name"] == y["regclass_name"]
            and {x["reg_name"], y["reg_name"]} == {ra, rb}
        ]
        if not tied:
            continue
        if len(tied) > 1:
            # Rank: a pair dying at the same instruction (op0/op1 birth) is
            # the canonical tie; then same defline; then any named member.
            def _rank(p):
                x, y = p
                return (
                    0 if (x.get("last") and x["last"] == y.get("last")) else
                    1 if (x.get("defline") and x["defline"] == y.get("defline")) else
                    2 if (x.get("var") or y.get("var")) else 3)
            tied.sort(key=_rank)
            if _rank(tied[0]) == _rank(tied[1]) and _rank(tied[0]) >= 2:
                cand_s = ", ".join(f"{_tag(x)}↔{_tag(y)}" for x, y in tied[:4])
                out.append(f"PS-alloc: ambiguous {ra}↔{rb} tie "
                           f"(candidates: {cand_s}) -- match the diff row's "
                           "line against the per-line view to pick the pair.")
                continue
        a, b = tied[0]        # a = earlier walk position
        wa, wb = alloc.index(a), alloc.index(b)
        try:
            ca = next(i for i, c in enumerate(confs) if c["conf"] == a["conf"])
            cb = next(i for i, c in enumerate(confs) if c["conf"] == b["conf"])
        except StopIteration:
            continue
        # Counterfactual: exchange the two creations (presort is the
        # REVERSED creation list; exchange the two nodes there).
        ia = next(i for i, (n, _) in enumerate(presort) if n == a["conf"])
        ib = next(i for i, (n, _) in enumerate(presort) if n == b["conf"])
        cf = list(presort)
        cf[ia], cf[ib] = cf[ib], cf[ia]
        cf_replay = [n for n, _ in _shell_sort(cf, lambda x, y: x[1] > y[1])]
        transported = (cf_replay.index(b["conf"]) < cf_replay.index(a["conf"]))

        crm_caveat = ""
        if any(w.get("op0_reg") or w.get("op1_reg") or w.get("result_reg")
               for w in (a.get("ins_walk") or []) + (b.get("ins_walk") or [])):
            crm_caveat = ("  [CRM non-empty on a member: first-free symmetry "
                          "not guaranteed -- re-check with cgex.crm_scores]")

        head = (f"PS-alloc: tie s{a['savings']} "
                f"{_tag(a)}->{a['reg_name']}(walk{wa},cn{ca})"
                f" \u2194 {_tag(b)}->{b['reg_name']}(walk{wb},cn{cb})"
                f"; PS binds {_tag(a)}->{b['reg_name']}")
        if not transported:
            out.append(head + " -- NOT-TRANSPORTED: exchanging the two "
                       "creations does not exchange their walk order under "
                       "the replayed ShellSort; pair order is pinned by the "
                       "rest of the conflict list -> compiler-delta class "
                       "(Rule 103 disposition)." + crm_caveat)
            continue
        # Lever mapping for the reachable case.
        same_ins = (a.get("last") and a["last"] == b.get("last"))
        if same_ins:
            out.append(head + " -- REACHABLE by swapping the op0/op1 "
                       f"sighting at their shared death ins (L{a['defline']}"
                       f"/L{b['defline']}): cn slots are the operand order "
                       "there.  CAVEAT: for an (R,R) compare the emitted cmp "
                       "operand order moves WITH the source order (G_RR2, "
                       "Rule 103) -- the register swap costs a mirrored cmp."
                       + _src_quote(a, b) + crm_caveat)
        elif a.get("var") and b.get("var") and (a["var"] in params
                                                 or b["var"] in params):
            # SHAPE-CONSTRAINT: a PARAMETER's decl order is ABI-FIXED
            # (__watcall eax/edx/ebx/ecx), so Rule 115 (decl-swap) is NOT
            # available.  Only use-order (Rule 28a) can move it, and that
            # reorders statements -> often BREAKS the already-matching IR ->
            # frequently SUB-SOURCE (proven: city_test_for_road).
            out.append(head + f" -- REACHABLE in the ABSTRACT ShellSort, but "
                       f"({a['var']}, {b['var']}) includes a PARAMETER: "
                       "decl-order is ABI-FIXED, so Rule 115 is UNAVAILABLE; "
                       "only use-order (Rule 28a) moves it, and that reorders "
                       "statements -> often breaks the IR that already "
                       "matches PS -> frequently SUB-SOURCE.  Confirm with "
                       "decomp-verify (counter-example: city_test_for_road)."
                       + _src_quote(a, b) + crm_caveat)
        elif a.get("var") and b.get("var"):
            out.append(head + f" -- REACHABLE by creation-order swap; both "
                       f"are named NON-PARAM locals ({a['var']}, {b['var']}): "
                       "Rule 115 (decl order) is IR-NEUTRAL -- swap their decl "
                       "lines (or Rule 28a use order).  Verify with the cn line."
                       + _src_quote(a, b) + crm_caveat)
        else:
            out.append(head + " -- REACHABLE by creation-order swap, but at "
                       "least one member is an anonymous temp: the only "
                       "handle is the IL shape that creates it (operand "
                       "order / statement split).  Check the cn line for "
                       "its neighbours." + _src_quote(a, b) + crm_caveat)
    if not out:
        return None
    return PsAllocVerdict(func, out)


def render_lines(v: PsAllocVerdict) -> list[str]:
    return v.lines

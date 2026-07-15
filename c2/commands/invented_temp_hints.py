"""Invented-temp / redundant-copy detector (style guide §10, de-inventing temps).

Signature of a source that introduces a register-to-register copy the
original did NOT have -- e.g. a redundant ``ptr = sptr;`` seeding a second
walker for a value PS keeps in ONE register and modifies in place
(``clear_sized_to_rubble``, 416b -> 0):

  1. **Dominant single-pair identity swap.**  The "invented" local lives in
     a different register than PS uses for the same value, so EVERY use of it
     swaps the SAME way.  One register pair therefore accounts for most of the
     diff (clear_sized_to_rubble: 39 ``ebx<->ecx`` rows = the whole diff).

  2. **An extra RC-only intra-pair reg-to-reg ``mov rDST, rSRC``** that PS
     lacks, where BOTH operands are the swapped pair -- the temp's seed copy
     (``local = other``).  PS never emits it because it walks the source value
     in place.

  3. **Duplication (the K+1 live-copy proof).**  The seed's SOURCE value must
     also flow to a SECOND home near the copy -- a snapshot store
     (``mov [mem], rSRC``) or a sibling copy (``mov rX, rSRC``).  That is the
     byte-level evidence that the value is genuinely duplicated: PS keeps it in
     K homes (one register + one snapshot), the invented temp makes it K+1.
     Without this gate a plain register-identity tie (which-var-gets-which-
     register, e.g. ``try_a_regionmap_square``: PS dir->ECX vs RC dir->EAX)
     would false-positive -- it shows the same single-pair swap but copies the
     source ONCE and reuses the register, so the value is never duplicated.

The fix is to DE-INVENT the temp -- delete the ``x = y;`` copy and use ``y``
directly (it can be modified in place; the separate ``start = y;`` snapshot is
the genuine saved copy PS keeps).

This classifier is intentionally conservative -- all three gates must hold.
Validated 2026-06-16: fires on the buggy ``clear_sized_to_rubble`` (the
416b->0 win) and on **0** of the 1521 corpus functions as a false positive
(the dup-gate removes the three register-tie near-misses).
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

# GPR sub-form -> canonical 32-bit name (mirrors rule_hints._ALL_GPR_FORMS).
_GPR_FORMS: dict[str, tuple[str, ...]] = {
    "eax": ("eax", "ax", "al", "ah"),
    "ebx": ("ebx", "bx", "bl", "bh"),
    "ecx": ("ecx", "cx", "cl", "ch"),
    "edx": ("edx", "dx", "dl", "dh"),
    "esi": ("esi", "si"),
    "edi": ("edi", "di"),
    "ebp": ("ebp", "bp"),
}
_FORM_TO_FULL = {f: full for full, fs in _GPR_FORMS.items() for f in fs}

# `mov <reg>, <reg>` with both operands plain registers (no memory, no imm).
_R2R_RE = re.compile(r"^mov (\w+), (\w+)$")
# `mov [<mem>], <reg>` -- a store of a register to memory (the snapshot form).
_STORE_RE = re.compile(r"^mov (?:(?:byte|word|dword) ptr )?\[[^\]]+\], (\w+)$")
_PAIR_RE = re.compile(r"(\w+)\u2194(\w+)")

# How far from the seed copy to look for the value's SECOND consumer (the
# snapshot store or sibling copy).  The canonical shape is two consecutive
# assignments from the same value (`start = sptr; ptr = sptr;`), so a small
# window suffices.
_DUP_WINDOW = 3

# Thresholds.  A swap must be both numerous and dominant to count as "one
# value consistently misplaced".  Tuned so the byte-exact corpus is silent and
# only whole-body single-register misassignments fire.
_MIN_SWAP_ROWS = 5
_DOMINANCE = 0.60


def _r2r(asm: str) -> tuple[str, str] | None:
    """(dst, src) full-register names for a reg-to-reg ``mov``, else None."""
    m = _R2R_RE.match(asm.strip())
    if not m:
        return None
    d, s = _FORM_TO_FULL.get(m.group(1)), _FORM_TO_FULL.get(m.group(2))
    if d is None or s is None or d == s:
        return None
    return d, s


def _r2r_multiset(insns) -> Counter:
    out: Counter = Counter()
    for i in insns:
        cp = _r2r(i[3])
        if cp is not None:
            out[cp] += 1
    return out


def _stores_reg(asm: str, full: str) -> bool:
    """True if ``asm`` is ``mov [mem], <sub-form-of full>`` (snapshot store)."""
    m = _STORE_RE.match(asm.strip())
    return bool(m and _FORM_TO_FULL.get(m.group(1)) == full)


def _value_duplicated(rc_insns, seed_dst: str, seed_src: str) -> bool:
    """The seed copy ``mov seed_dst, seed_src`` is a genuine DUPLICATION iff
    the source value (``seed_src``) flows to a SECOND home near the copy -- a
    memory store (``mov [mem], seed_src``, the snapshot) or another
    reg-to-reg copy (``mov rX, seed_src``).  This is the byte-level evidence
    for K+1 live copies: PS keeps the value in one register and snapshots it
    once; the invented temp makes a redundant second copy of the SAME value.

    A pure register-identity tie (which-var-gets-which-register) produces the
    same single-pair swap but NO such duplication -- the source register is
    copied once and then reused for something else -- so this gate removes the
    register-tie false positives (try_a_regionmap_square etc.)."""
    sd = seed_dst.lower()
    ss_full = _FORM_TO_FULL[seed_src.lower()]
    seed_idxs = [i for i, ins in enumerate(rc_insns)
                 if _r2r(ins[3]) == (sd, ss_full)]
    for si in seed_idxs:
        lo, hi = max(0, si - _DUP_WINDOW), min(len(rc_insns), si + _DUP_WINDOW + 1)
        for j in range(lo, hi):
            if j == si:
                continue
            a = rc_insns[j][3]
            cp = _r2r(a)
            if _stores_reg(a, ss_full) or (cp is not None and cp[1] == ss_full):
                return True
    return False


@dataclass
class InventedTempHint:
    pair: tuple[str, str]          # dominant swap pair, e.g. ("EBX", "ECX")
    swap_rows: int                 # rows carrying that pair
    total_swap_rows: int           # all Reg-swap rows
    seed_dst: str                  # invented temp's RC home register
    seed_src: str                  # value being redundantly copied
    extra_copies: int              # how many extra reg-to-reg movs RC has


def detect(hints, rows, ps_insns, rc_insns) -> InventedTempHint | None:
    """Return an InventedTempHint when the diff looks like an invented
    register-to-register copy (redundant local), else None.

    ``hints`` is the per-row RuleHint list (parallel to ``rows``); ``rows``
    are the aligned diff rows; ``ps_insns`` / ``rc_insns`` are the full
    instruction streams (``InsnT`` tuples ``(off, size, bytes, asm)``)."""
    if not rows:
        return None

    # 1. Dominant register-identity swap pair (binding rows only -- ignore
    #    cmp/test-only mirror swaps, which are operand-order, not bindings).
    pair_rows: Counter = Counter()
    for i, h in enumerate(hints):
        if h is None or getattr(h, "rule", None) != "Reg swap":
            continue
        if "register identity swap" not in getattr(h, "summary", ""):
            continue
        o = rows[i].get("o") if i < len(rows) else None
        ps_asm = o[3] if o else ""
        if ps_asm.lstrip().startswith(("cmp", "test")):
            continue
        seen: set[frozenset] = set()
        for a, b in _PAIR_RE.findall(h.summary):
            p = frozenset((a.upper(), b.upper()))
            if len(p) == 2:
                seen.add(p)
        for p in seen:
            pair_rows[p] += 1

    total = sum(pair_rows.values())
    if total < _MIN_SWAP_ROWS:
        return None
    top_pair, top_n = pair_rows.most_common(1)[0]
    if top_n < _MIN_SWAP_ROWS or top_n / total < _DOMINANCE:
        return None
    pa, pb = sorted(top_pair)

    # 2. RC emits a reg-to-reg copy (into a swapped register) that PS lacks.
    ps_cp = _r2r_multiset(ps_insns)
    rc_cp = _r2r_multiset(rc_insns)
    extra = rc_cp - ps_cp        # multiset difference: RC-only copies
    if not extra:
        return None

    # The seed copy moves the value from PS's register into the invented
    # temp's register, so BOTH operands are the swapped pair: `mov rTEMP,
    # rPS` (or its reverse).  That intra-pair copy is the distinctive
    # signature -- it is the literal `temp = value` that PS never makes.
    # (Other extra copies in `extra` are just downstream shuffle artifacts of
    # the misallocation; require both-in-pair so we name the real target.)
    seed: tuple[str, str] | None = None
    for (dst, src), n in extra.most_common():
        if {dst.upper(), src.upper()} == {pa, pb}:
            seed = (dst.upper(), src.upper())
            break
    if seed is None:
        return None

    # 3. The seed must be a genuine DUPLICATION (K+1 live copies), not a
    #    register-identity tie that merely shuffles which var owns which
    #    register.  Require the source value to flow to a SECOND home (a
    #    snapshot store or sibling copy) near the seed.  Without this, a
    #    plain layer-3 swap (try_a_regionmap_square: PS dir->ECX vs RC
    #    dir->EAX) would false-positive.
    if not _value_duplicated(rc_insns, seed[0], seed[1]):
        return None

    return InventedTempHint(
        pair=(pa, pb),
        swap_rows=top_n,
        total_swap_rows=total,
        seed_dst=seed[0],
        seed_src=seed[1],
        extra_copies=sum(extra.values()),
    )


def render(h: InventedTempHint) -> str:
    temp = h.seed_dst.lower()      # invented temp's RC home
    val = h.seed_src.lower()       # value PS keeps / snapshots in one register
    return (
        f"Invented temp (§10 de-invent): the diff is dominated by a single "
        f"{h.pair[0]}\u2194{h.pair[1]} identity swap ({h.swap_rows}/"
        f"{h.total_swap_rows} swap rows), and RC emits a reg-to-reg copy "
        f"`mov {temp}, {val}` that PS lacks AND duplicates a value already "
        f"snapshotted/used nearby.  That copy seeds a LOCAL (in {temp}) "
        f"holding a value PS keeps in ONE register ({val}) and walks/modifies "
        f"in place -- you invented a temp the original didn't have (PS keeps K "
        f"live copies, RC K+1).  Lever: DELETE the `temp = {val}_var;` copy "
        f"and use the original directly (it can be modified in place); a "
        f"separate `start = {val}_var;` snapshot, if present, is the real "
        f"saved copy.  The whole-body {h.pair[0]}\u2194{h.pair[1]} swap then "
        f"collapses."
    )

"""Temp-birth attribution: map every Names[N_TEMP] entry to WHO created it.

Consumes the >= 2026-07-10 trace image's records (parsed by
``c2.regalloc.trace``):

* ``nb``  -- AllocName exit: (name ptr, class, FE line, caller RA);
* ``nbc``/``nbo`` -- SAllocTemp@0x39f0f / STempOffset@0x39e16 ENTRY:
  the direct caller RA and the grandcaller RA through the thin
  ``AllocTemp``@0x39f75 / ``TempOffset``@0x39f82 wrappers.  The parser
  joins each to the next class-2 ``nb`` (``pass_caller``/``pass_caller2``).

Ground truth (watcom10.0a knowledge DB, docs/temp-slot-layout.md):
AllocName PREPENDS to NameLists@0x7f8bc, so Names[N_TEMP] head order ==
reversed(surviving births); TempId@0x7f8f0 == the +0x24 'loc24' creation
ordinal (aliases share it).  The whole slot chain downstream of the births
is corpus-validated 100% (``shellsort_sim_slots.validate_routine_chain``).

This module answers the question the Rule 107 slot-swap levers need:
*which compiler construct births each flip-window temp* -- so the source
search is "move/remove THAT construct" instead of blind decl grinding.
"""

from __future__ import annotations

# RAs (binary VAs) of the thin wrappers' `call` return sites: when the
# direct caller is one of these, the real pass is the GRANDCALLER.
_THIN_WRAPPER_RAS = {0x39F80, 0x39F8D}

# Known creator functions (binary VA ranges, from the watcom10.0a Ghidra DB /
# knowledge/wcc386_regalloc.py -- keep in sync when new creators are named).
# (lo, hi, name, what-it-means-for-source).  FIRST MATCH WINS: keep specific
# entries before region fallbacks.  Coverage census 2026-07-10 (corpus-wide,
# all class-2 births): every caller with >= 10 births is attributed below.
KNOWN_CREATORS = [
    # -- precise (function-level, binary-verified) -------------------------
    (0x443A8, 0x443CA, "BGNewTemp",
     "tree-burn temp mint -- 66%% of all births; the OUTER creator "
     "(FlowOut / BGGlobalTemp / a burn helper) is in the `outer` column "
     "(nbb probe, >= 2026-07-10 image)"),
    (0x443CA, 0x443D4, "BGGlobalTemp",
     "cross-block temp for the cg api layer"),
    (0x443D4, 0x444A9, "FlowOut",
     "BOOLEAN materialisation (bool expr used as a value: `x = (a op b)` / "
     "bool arg) -- births a temp + TWO const-store blocks"),
    (0x4ADA9, 0x4ADCF, "BurnCopyToTemp",
     "copy-into-fresh-temp during the FE burn (carries the FE line)"),
    (0x5E7ED, 0x5E960, "CondConstStores2Bool",
     "diamond collapse: if/else CONSTANT stores differing by 1 -> U1 byte "
     "temp + setCC/ADD (`x = (expr != 0)`-style shapes).  THE anon byte "
     "temps that interleave Names[N_TEMP] and destabilise the size sort"),
    (0x39F8F, 0x39FDE, "SAllocUserTemp",
     "USER-DECLARED local (LkAddBack symbol registry) -- the named temps; "
     "their creation order follows first-reference order in the FE burn"),
    (0x4AF29, 0x4AFE8, "InsToAddr",
     "EXPRESSION-RESULT temp (makeaddr InsToAddr): every NF_INS addr-name "
     "consumed as a value (`a + b` fed into a store / compare / index / "
     "call) gets its ins-result temp here via BGNewTemp -- the DOMINANT "
     "creator; one temp per consumed subexpression, in burn order"),
    (0x4AC91, 0x4AD74, "MakeGets",
     "assignment materialisation (makeaddr.c MakeGets): the INDEXED-dst "
     "path births `temp = SAllocTemp(dst class,size)` for `mem[idx] = x` "
     "whose value is consumed -- one temp per such assignment"),
    (0x533C0, 0x53550, "Points",
     "lvalue address materialisation (makeaddr.c Points): index/address "
     "temps for the DESTINATION of an assignment"),
    (0x53550, 0x53B00, "GetValue",
     "addrfold.c GetValue/MakeAddend (via MaybeTemp@0x4afe8, a tail-jmp "
     "helper): VALUE materialisation of an address fold -- `base + offset` "
     "pointer arithmetic, CL_TEMP_OFFSET/LoadAddress paths.  Fires for "
     "`(char*)map + ptr_expr` style reads even in call-less functions"),
    (0x61C32, 0x61D00, "CheckMul",
     "strength reduction (multiply.c CheckMul): `x * const` -> shl/add "
     "chain births the orig+temp scratch PAIR"),
    # -- region fallbacks (behavioral labels; entries above win) -----------
    (0x5A800, 0x5B000, "ExpandSplit",
     "expand/verify legalization (ExpandOps region): op/result-to-temp "
     "split when an instruction form is illegal (e.g. two memory "
     "operands) -- 0x5a95f op#-temp, 0x5aa42 result-temp, 0x5a9c2 "
     "mem-op dispatcher, 0x5a82f index-to-temp"),
    (0x6AE00, 0x6BC00, "ReduceSplit",
     "split.c ReduceTab rewriter (rOP1REG/rMOVOP1TEMP/rMOVRESTEMP/...): an "
     "instruction the encoder can't emit directly gets an operand/result "
     "split through a fresh temp of ins->type_class.  Verified entries "
     "0x6af2a/0x6afa9/0x6b0ca; range bounds approximate"),
    (0x5D700, 0x5DA50, "ArithExpand",
     "0x5d7a6: arith-opcode (1..0x10) instruction expansion temps"),
    (0x64A00, 0x65000, "I86AddrTemp",
     "0x64ad0/0x64cfe/0x64e06: per-name-class dispatch (jump table) in the "
     "i86 addressing/encoding lowering"),
    (0x5CB00, 0x5CD00, "InsListTemp",
     "0x5cb73: instruction-list walking pass (opcode 0x4b block-boundary "
     "checks) minting temps"),
    (0x44A00, 0x46000, "TreeBurn",
     "tree-burn helper region (0x44b0b, 0x45cad, ...): direct AllocTemp "
     "calls from the expression burners"),
    (0x29000, 0x2A000, "FE_direct",
     "front-end region calling AllocTemp directly (rare; ~10 births "
     "corpus-wide)"),
]


def resolve_wcc_base(nb_records: list) -> int | None:
    """Recover the wibo load base from the birth records' runtime RAs.

    The dominant ``pass_caller`` among AllocTemp-routed births is the thin
    wrapper's return site 0x39F80 (TempOffset-routed: 0x39F8D); the mode of
    ``runtime - RA`` over those anchors is the base.  Returns None when no
    attributed births exist (pre-2026-07-10 trace image)."""
    from collections import Counter
    cand: Counter = Counter()
    for r in nb_records:
        c = r.get("pass_caller")
        if not c:
            continue
        v = int(c, 16)
        for anchor in _THIN_WRAPPER_RAS:
            cand[v - anchor] += 1
    if not cand:
        return None
    base, hits = cand.most_common(1)[0]
    # sanity: a plausible base puts every caller in the code image
    if hits < 1 or base <= 0:
        return None
    return base


def _symbolize(va: int) -> str:
    for lo, hi, name, _ in KNOWN_CREATORS:
        if lo <= va < hi:
            return name
    return f"pass@{va:#x}"


def creator_note(name: str) -> str:
    for _, _, n, note in KNOWN_CREATORS:
        if n == name:
            return note
    return ""


def attribute_births(routine: dict) -> dict:
    """Return ``{name_ptr: {"line": int, "pass": str, "pass_va": int|None,
    "kind": "temp"|"alias"}}`` for every N_TEMP name in the routine, using
    each ptr's LAST birth (AllocFrl recycles freed name structs).

    Empty dict when the trace predates the ``nb`` probes."""
    nb = routine.get("nb") or []
    if not nb:
        return {}
    base = resolve_wcc_base(nb)
    out: dict = {}
    for r in nb:
        if r.get("class") != 2:
            continue
        entry = {"line": r.get("line") or 0, "pass": "?", "pass_va": None,
                 "kind": "alias" if r.get("pass_kind") == "nbo" else "temp"}
        c1, c2 = r.get("pass_caller"), r.get("pass_caller2")
        if base is not None and c1:
            va1 = int(c1, 16) - base
            va = int(c2, 16) - base if (va1 in _THIN_WRAPPER_RAS and c2) else va1
            entry["pass_va"] = va
            entry["pass"] = _symbolize(va)
            # BGNewTemp births carry the OUTER creator (nbb probe): resolve
            # THROUGH it so FlowOut / BGGlobalTemp / the burn helper shows.
            outer = r.get("pass_outer")
            if outer and entry["pass"] == "BGNewTemp":
                ova = int(outer, 16) - base
                entry["outer_va"] = ova
                entry["pass"] = _symbolize(ova)
                if entry["pass"].startswith("pass@"):
                    entry["pass"] = f"TreeBurn@{ova:#x}"
        out[r["name"]] = entry           # later birth overwrites earlier
    return out


def birth_label(name_ptr: str, attrib: dict) -> str:
    """Short human label for one nt entry's birth: ``FlowOut`` /
    ``burn L969`` / ``pass@0x4xxxx`` / ``?`` (no attribution)."""
    a = attrib.get(name_ptr)
    if not a:
        return "?"
    p = a["pass"]
    if a["line"]:
        return f"{p} L{a['line']}" if not p.startswith("pass@") else f"burn L{a['line']}"
    return p

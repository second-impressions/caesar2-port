"""Simulator of the WATCOM 10.0a `AssignTemps` Names[N_TEMP] sort.

Reproduces the EXACT ``nt_pre -> nt_post`` permutation the real compiler
emits, so the resulting AllocNewLocal slot order (hence each spilled local's
``[esp+N]``) is *predictable* from a candidate temp-creation list, without a
recompile.

Ground truth (10.0a binary, verified via pyghidra; see watcom10.0a sister repo
``docs/temp-slot-layout.md``):

* ``AssignTemps`` @0x55463 calls ``SortList(Names[N_TEMP], 0, 0x55503)``.
* ``SortList`` -> ``DoSortList`` @0x665c4: normal alloc-SUCCESS arm runs
  ``ShellSort`` @0x66689 over an array-of-name-pointers, then ``BuildList``
  @0x66532 rebuilds the linked list in array order (order-preserving).  Only
  the alloc-FAILURE arm falls back to the stable ``MergeList`` @0x66566 merge
  sort -- never taken for normal-sized temp lists.
* ``ShellSort`` @0x66689 (exact disasm decoded)::

      array = [name_ptr] * length           # array of POINTERS
      gap = length;  adj = 1                # [EBP-0x10] prev-adjust, init 1
      do:
          adj = (adj == 0)                  # toggle
          gap = (gap >> 1) + adj
          repeat:
              swapped = False
              for i in 0 .. length-gap-1:   # EBX=i, ECX=i+gap
                  if before(a[i+gap], a[i]):  # CALL [EBP-0x18] EAX=a[i+gap],EDX=a[i]
                      swap(a[i], a[i+gap]); swapped = True
          while swapped                    # full bubble-to-fixed-point per gap
      while gap != 1

  The repeat-to-fixed-point per gap level is what the raw disasm's inner-loop
  back-edge (0x666fc ``JNZ 0x666ba``) realises.  Non-stability comes from the
  gap ordering: equal-rank elements shuffled across a large gap pass are
  never restored by a later (smaller-gap) pass that compares them as
  sort-equal (so leaves whatever the big-gap pass decided in place).

* Comparator ``SortCmp_flag2_2b`` @0x55503 -- ``before(x, y)`` returns 1 iff x
  should sort BEFORE y:

      1. ALIAS bit  ``byte[x+0x2b] & 0x2`` vs ``byte[y+0x2b] & 0x2``
         (alias temps float to the front);
      2. ``n.size``  ``[x+0x8]`` vs ``[y+0x8]``  (smaller first);
      3. ``[x+0x24]`` (a per-temp id): if DIFFERENT -> return 0 BOTH ways
         (sort-equal);
      4. ``[x+0x10]`` ``v.offset`` DESCENDING (larger first), only when +0x24
         is equal.

The trace (``c2 regtrace`` -> routine ``nt_pre``/``nt_post`` records) carries
``size`` (+0x8), ``usage`` (+0x18), ``flags`` (+0x28 dword), ``off10`` (+0x10)
and ``loc24`` (+0x24) per temp, which supply every comparator input.  The
ALIAS bit is byte ``+0x2b`` = ``(flags >> 24) & 0x2``.

NOTE on the ALIAS-bit byte: the comparator reads ``byte[EAX+0x2b]`` and tests
``& 0x2``.  ``flags`` (the trace dword at +0x28) covers bytes ``+0x28..0x2b``
little-endian, so byte ``+0x2b`` is ``flags >> 24``.  (An older
``patch_trace.py`` comment mis-stated the ALIAS bit as living at ``+0x2a``;
the DISASM at 0x55504 is authoritative: ``TEST byte ptr [EAX + 0x2b], 0x2``.)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence


@dataclass(frozen=True)
class Temp:
    """Mirror of a Names[N_TEMP] entry with exactly the comparator inputs.

    ``alias`` is the ``byte[+0x2b] & 0x2`` ALIAS bit (see module docstring for
    how to derive it from the trace ``flags`` dword).  ``key`` is an opaque
    label (e.g. the source var name) carried through the sort for diagnosis.
    """
    key: str
    size: int          # n.size        [+0x8]
    loc24: int         # the per-temp id [+0x24]
    off10: int = 0     # v.offset      [+0x10]
    alias: bool = False  # ALIAS bit    byte[+0x2b]&0x2

    @classmethod
    def from_trace(cls, rec: dict, key: str = None) -> "Temp":
        flags = int(rec.get("flags", 0))
        alias = bool((flags >> 24) & 0x2)
        return cls(
            key=key or rec.get("name", "?"),
            size=int(rec.get("size", 0)),
            loc24=int(rec.get("loc24", 0)),
            off10=int(rec.get("off10", 0)),
            alias=alias,
        )


def make_before() -> Callable[["Temp", "Temp"], bool]:
    """Build the SortCmp_flag2_2b @0x55503 ``before(x,y)`` predicate.

    Returns True iff x sorts strictly before y (the comparator returns AL=1).
    """
    def before(x: Temp, y: Temp) -> bool:
        # 1. ALIAS bit (alias-first -> alias sorts before non-alias).
        xa, ya = x.alias, y.alias
        if xa and not ya:
            return True
        if ya and not xa:
            return False
        # 2. n.size (smaller first).
        if x.size != y.size:
            return x.size < y.size
        # 3. +0x24: if DIFFERENT -> sort-equal (return False BOTH ways).
        if x.loc24 != y.loc24:
            return False
        # 4. +0x10 v.offset DESCENDING (larger first).
        if x.off10 != y.off10:
            return x.off10 > y.off10
        return False
    return before


def shellsort(arr: list, before: Callable) -> list:
    """Reproduce ShellSort @0x66689 over ``arr`` (a list of values, in place).

    Returns the sorted list.  ``before(a[i+gap], a[i])`` swapping adjacent
    gap-separated elements; the bubble pass repeats to a fixed point per gap.
    """
    a = list(arr)
    n = len(a)
    if n < 2:
        return a
    gap = n
    adj = 1          # [EBP-0x10] prev-adjust, init 0x1
    while True:
        adj = 1 if adj == 0 else 0   # toggle
        gap = (gap >> 1) + adj
        # inner bubble, repeat to fixed point
        while True:
            swapped = False
            i = 0
            limit = n - gap          # EBX < base+(length-gap)
            while i < limit:
                if before(a[i + gap], a[i]):
                    a[i], a[i + gap] = a[i + gap], a[i]
                    swapped = True
                i += 1
            if not swapped:
                break
        if gap == 1:
            break
    return a


def predict_nt_post(nt_pre: Sequence[Temp]) -> list:
    """Predict Names[N_TEMP] AFTER the AssignTemps SortList, from the pre-sort
    list.  Returns the post-sort list of Temps (same objects, reordered)."""
    before = make_before()
    return shellsort(list(nt_pre), before)


def predict_slots(nt_pre: Sequence[Temp], needs_memory: Callable[[Temp], bool],
                  esp_frame_bytes: int = 0):
    """Predict each NEEDS_MEMORY temp's final ``[esp+N]`` offset.

    Mirrors AllocNewLocal + SetTempLocation: the post-sort NEEDS_MEMORY
    subsequence is walked front-to-back; each fresh slot bumps ``locals.size``
    by ``_RoundUp(size, 4)`` and gets ``t.location = -locals.size`` (base 0);
    the resulting ``[esp+N]`` is ``frame_bytes - locals.size``.

    ``esp_frame_bytes`` is the size of the ``sub esp, N`` frame (so the first
    slot lands at the highest ``[esp+N]``).  Pass 0 to get the signed
    ``t.location`` instead (then slot[i] is more-negative = later).
    """
    post = predict_nt_post(nt_pre)
    slots = []
    size_accum = 0
    for t in post:
        if not needs_memory(t):
            continue
        size_accum += 4 if (t.size if t.size else 1) > 0 else 4
        # _RoundUp to REG_SIZE (4) -- byte temps still take a 4-byte slot.
        loc = -size_accum
        esp_off = (esp_frame_bytes + loc) if esp_frame_bytes else loc
        slots.append((t.key, esp_off, t))
    return slots


def predict_slot_ptrs(nt_pre_records):
    """Predict the NEEDS_MEMORY slot-assignment ORDER as a list of name
    POINTERS (the trace record's ``name`` field), corresponding 1:1 to the
    real compiler's ``an`` record order.  ``nt_pre_records`` is the raw
    ``routine['nt_pre']`` list of trace dicts (carrying name ptr + size +
    loc24 + off10 + flags).  This is the corpus-gate helper: compare its
    output to ``routine['an']``'s ``name`` sequence."""
    before = make_before()
    # decorate each rec with its Temp so the sort preserves identity
    decorated = [(Temp.from_trace(rec), rec["name"]) for rec in nt_pre_records]
    # ShellSort over the Temp objects; carry the name ptr along.
    # (wrap so shellsort sees Temp objects it can compare)
    arr = [(_t, _n) for (_t, _n) in decorated]
    n = len(arr)
    if n >= 2:
        gap = n; adj = 1
        while True:
            adj = 1 if adj == 0 else 0
            gap = (gap >> 1) + adj
            while True:
                swapped = False
                i = 0
                limit = n - gap
                while i < limit:
                    if before(arr[i + gap][0], arr[i][0]):
                        arr[i], arr[i + gap] = arr[i + gap], arr[i]
                        swapped = True
                    i += 1
                if not swapped:
                    break
            if gap == 1:
                break
    # return the name-ptr subsequence that AllocNewLocal would walk:
    # NEEDS_MEMORY (usage&0x80) AND !HAS_MEMORY(0x40) AND !ALIAS(byte+0x2a&2).
    out = []
    for _t, _n in arr:
        rec = next((r for r in nt_pre_records if r["name"] == _n), {})
        usage = rec.get("usage", 0)
        flags = rec.get("flags", 0)
        alias_byte = (flags >> 16) & 0xFF   # byte +0x2a  (flags covers +0x28..+0x2b)
        if (usage & 0x80) and not (usage & 0x40) and not (alias_byte & 0x2):
            out.append(_n)
    return out


# ---------------------------------------------------------------------------
# BuildNameConflicts sort: nb1 (front-end creation order) -> nb2 == nt_pre.
# Comparator AllocBefore @0x5905b (decompiled + validated 53/53 on
# evolve_water_table).  Same non-stable ShellSort as AssignTemps.
# ---------------------------------------------------------------------------

def make_allocbefore():
    """Build the AllocBefore @0x5905b ``before(x,y)`` predicate over trace
    dict records (carrying conf, size, flags, loc24=+0x24, sort_sav)."""
    def before(x: dict, y: dict) -> bool:
        # 1. CONST_TEMP bit (byte +0x2b = flags>>24, bit 0x1): non-CONST
        #    sorts before CONST (both ways consistent).
        xf = int(x.get("flags", 0)); yf = int(y.get("flags", 0))
        xc = bool((xf >> 24) & 0x1); yc = bool((yf >> 24) & 0x1)
        if xc and not yc:
            return False
        if yc and not xc:
            return True
        # 2. have-conflict (v.conflict [+0xc]) sorts before no-conflict.
        xh = x.get("conf") not in (None, "0", 0, "0x0")
        yh = y.get("conf") not in (None, "0", 0, "0x0")
        if xh and not yh:
            return True
        if yh and not xh:
            return False
        if xh and yh:
            # 3a. both have conflict -> savings DESC.
            return int(x.get("sort_sav", 0)) > int(y.get("sort_sav", 0))
        # 3b. both no-conflict -> [+0x24] (loc24) DESC.
        return int(x.get("loc24", 0)) > int(y.get("loc24", 0))
    return before


def predict_nb2(nb1_records) -> list:
    """Predict Names[N_TEMP] AFTER the BuildNameConflicts sort (= nb2 = nt_pre),
    from the pre-sort nb1 list (front-end creation order)."""
    return shellsort(list(nb1_records), make_allocbefore())


def predict_nt_pre(nb1_records) -> list:
    """Alias: predict_nt_pre(nb1) == predict_nb2(nb1) (nb2 IS the AssignTemps
    input)."""
    return predict_nb2(nb1_records)


# ---------------------------------------------------------------------------
# Corpus-gate validation (2026-07-09): the FULL slot chain is modeled and
# validated 100% on the byte-exact corpus:
#
#   source -> AllocName births ('nb' trace records; Names[class] is built by
#             PREPEND @ AllocName, so Names[N_TEMP] head order =
#             reversed(surviving births); TempId = ++[0x7f8f0] = the +0x24
#             'loc24' id, aliases from STempOffset share it)      1137/1137
#          -> BuildNameConflicts AllocBefore@0x5905b ShellSort    1137/1137
#             (nb1 -> nb2; NOTE: the trace parser CONCATENATES the per-round
#             sort events into one nb1/nb2 list -- segment with
#             segment_sort_events() before predicting)
#          -> AssignTemps SortCmp_flag2_2b@0x55503 ShellSort      1224/1224
#          -> AllocNewLocal slot walk ('an' order)                 138/138
#
# The historical '30 failures' of the whole-list nb1->nb2 check were ALL the
# multi-round concatenation artifact, not comparator errors.
# ---------------------------------------------------------------------------

def segment_sort_events(nb1_records, nb2_records):
    """Split the parser's concatenated multi-round nb1/nb2 buffers into
    per-sort-event (pre, post) pairs.  Boundaries are the positions where the
    prefix name-multisets agree.  Greedy-smallest boundaries can split a real
    event at a coincidental prefix match, so callers that VALIDATE should
    accept any segmentation whose every event predicts exactly (see
    validate_routine_chain).  Returns None when the buffers are unsplittable
    (length mismatch / trailing residue)."""
    from collections import Counter
    if len(nb1_records) != len(nb2_records):
        return None
    events, start = [], 0
    c1, c2 = Counter(), Counter()
    for i, (a, b) in enumerate(zip(nb1_records, nb2_records)):
        c1[a["name"]] += 1
        c2[b["name"]] += 1
        if c1 == c2:
            events.append((nb1_records[start:i + 1], nb2_records[start:i + 1]))
            start = i + 1
            c1, c2 = Counter(), Counter()
    if start != len(nb1_records):
        return None
    return events


def validate_routine_chain(routine: dict) -> dict:
    """Validate every modeled stage of the slot chain for one traced routine
    against the live records.  Returns {stage: bool|None} (None = no data).

    Stage 'births' additionally needs the >= 2026-07-09 image ('nb' records).
    The births->nb1 rule: Names[N_TEMP] = reversed(last-birth-per-ptr class-2
    births), filtered to the survivors present in nb1 (AllocName PREPENDS;
    FreeName unlinks without reordering; AllocFrl recycles freed ptrs, so
    only each ptr's LAST birth is live)."""
    from collections import Counter
    out = {"births": None, "nb1_nb2": None, "nt_sort": None, "slots": None}
    nb = routine.get("nb") or []
    nb1 = routine.get("nb1") or []
    nb2 = routine.get("nb2") or []
    nt_pre = routine.get("nt_pre") or []
    nt_post = routine.get("nt_post") or []
    an = routine.get("an") or []
    ev = segment_sort_events(nb1, nb2) if nb1 else None
    if ev:
        # nb1 -> nb2 (accept any segmentation in which every event predicts;
        # DP over candidate boundaries)
        n = len(nb1)
        bounds = [0]
        c1, c2 = Counter(), Counter()
        for i in range(n):
            c1[nb1[i]["name"]] += 1
            c2[nb2[i]["name"]] += 1
            if c1 == c2:
                bounds.append(i + 1)
        reach = {0}
        for j_idx, j in enumerate(bounds):
            if j not in reach:
                continue
            for k in bounds[j_idx + 1:]:
                if k in reach:
                    continue
                a, b = nb1[j:k], nb2[j:k]
                if sorted(x["name"] for x in a) != sorted(x["name"] for x in b):
                    continue
                if [r["name"] for r in predict_nb2(a)] == [r["name"] for r in b]:
                    reach.add(k)
        out["nb1_nb2"] = n in reach
        # births -> nb1 (round 1)
        if nb:
            live = [r["name"] for r in ev[0][0]]
            temps = [r for r in nb if r.get("class") == 2]
            last = {}
            for i, r in enumerate(temps):
                last[r["name"]] = i
            surv = [temps[i] for _, i in sorted(last.items(), key=lambda kv: kv[1])]
            livec, c = Counter(live), Counter()
            pred = []
            for r in reversed(surv):
                if c[r["name"]] < livec.get(r["name"], 0):
                    pred.append(r["name"])
                    c[r["name"]] += 1
            out["births"] = pred == live
    if nt_pre and nt_post and len(nt_pre) == len(nt_post):
        pred = predict_nt_post([Temp.from_trace(r) for r in nt_pre])
        out["nt_sort"] = [t.key for t in pred] == [r["name"] for r in nt_post]
    if nt_pre and an:
        predp = predict_slot_ptrs(nt_pre)
        out["slots"] = (predp == [a["name"] for a in an][:len(predp)]) if predp else None
    return out

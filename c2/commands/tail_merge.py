"""Tail-merge donor scanner for decomp-verify hint output.

Detects the **Rule 42** pattern (cross-function tail-merge donor
selection) by inspecting the last instruction of a PS.EXE function
under verification:

  * If the function ends in an unconditional `jmp <imm32>` (`e9 ?? ?? ?? ??`)
    whose target lands *inside* another known code symbol, that target
    function is the merge donor.
  * The bytes from the merge target up to the donor's end are the
    "shared tail" Watcom factored out.

When this pattern is present, the recompiled function won't byte-match
until the donor function is decompiled with the matching prologue /
epilogue shape (because Watcom only merges with another function that
has the same callee-save set + RetPop — see Rule 42 mechanism).

Usage::

    from c2.commands.tail_merge import scan_tail_merge_donor

    hint = scan_tail_merge_donor(orig_bytes, orig_off)
    if hint:
        # hint.donor_name, hint.merge_offset_in_donor,
        # hint.tail_bytes (bytes), hint.tail_disasm (list[str])
        ...

Detection is conservative: it only fires when the very last instruction
of the function is a near jmp to outside the function — which is the
distinctive PS shape Watcom emits *after* tail-merge folds the
epilogue out.  The renderer in `decomp_verify._render_compact` /
`_render_diff` consumes the hint and prints a one-line summary
alongside the existing rule histogram.

See ``docs/watcom-codegen-patterns.md`` Rule 42 for the underlying
algorithm in OW v1 (`bld/cg/c/optcom.c::ComTail`).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import capstone


# ── Symbol-table cache ──────────────────────────────────────────────────────

@dataclass
class _SymCtx:
    """Just enough of symbols.json to resolve a vaddr to (name, start, size).

    Held in a module-level cache keyed by symbols.json path so repeated
    verifies in one process don't re-parse the JSON.
    """
    addr_to_name: dict[int, str]                  # exact-start lookup
    name_to_addr: dict[str, int]
    func_ranges: list[tuple[int, int, str]]       # sorted by start; (start, end_exclusive, name)
    code_base: int                                # LE code-segment base vaddr (0x10000 by convention)


_sym_cache: dict[Path, _SymCtx] = {}


def _load_symbols(symbols_json: Path) -> _SymCtx:
    """Load + cache the function-range table from ``symbols.json``."""
    key = symbols_json.resolve()
    cached = _sym_cache.get(key)
    if cached is not None:
        return cached

    sym = json.loads(symbols_json.read_text())
    addr_to_name = {s["address"]: s["name"] for s in sym["symbols"]}
    name_to_addr = {s["name"]: s["address"] for s in sym["symbols"]}
    code_base = sym["memory_map"]["objects"][0]["base_address_int"]

    code_syms = sorted(
        [s for s in sym["symbols"] if s.get("is_code")],
        key=lambda s: s["address"],
    )
    ranges: list[tuple[int, int, str]] = []
    for i, s in enumerate(code_syms[:-1]):
        ranges.append((
            s["address"], code_syms[i + 1]["address"], s["name"],
        ))
    if code_syms:
        last = code_syms[-1]
        ranges.append((last["address"], last["address"] + 256, last["name"]))

    ctx = _SymCtx(
        addr_to_name=addr_to_name,
        name_to_addr=name_to_addr,
        func_ranges=ranges,
        code_base=code_base,
    )
    _sym_cache[key] = ctx
    return ctx


def _function_at(ctx: _SymCtx, vaddr: int) -> Optional[tuple[str, int, int]]:
    """Return ``(name, start, end_exclusive)`` of the function containing
    ``vaddr``, or None if no code symbol covers it."""
    # Linear over a sorted small list is fine for our scale (~7 K funcs);
    # a bisect would micro-optimize but this runs once per verified function.
    for start, end, name in ctx.func_ranges:
        if start <= vaddr < end:
            return name, start, end
    return None


# ── Hint type ──────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class TailMergeHint:
    """Result of scanning a function's tail for a Rule 42 donor jmp."""
    donor_name:           str        # e.g. "build_wall_from_elastic"
    donor_start:          int        # virtual address of donor function start
    merge_target:         int        # virtual address the jmp lands at
    merge_offset_in_donor: int       # merge_target - donor_start
    jmp_offset_in_self:   int        # offset of the jmp inside the calling function
    tail_bytes:           bytes      # donor[merge_target : donor_end]
    tail_disasm:          tuple[str, ...]  # one mnemonic+ops per line


# ── Scanner ────────────────────────────────────────────────────────────────

def _disasm_simple(chunk: bytes, base_addr: int) -> list[tuple[int, int, bytes, str, str]]:
    """Return ``[(rel_off, size, raw, mnemonic, op_str), ...]`` for ``chunk``."""
    cs = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    out: list[tuple[int, int, bytes, str, str]] = []
    for ins in cs.disasm(chunk, base_addr):
        out.append((
            ins.address - base_addr, ins.size, ins.bytes,
            ins.mnemonic, ins.op_str,
        ))
    return out


def scan_tail_merge_donor(
    orig: bytes,
    orig_off: int,
    *,
    is_vaddr: bool = True,
    symbols_json: Path = Path("data/out/symbols.json"),
    code_bytes: Optional[bytes] = None,
    code_base: Optional[int] = None,
) -> Optional[TailMergeHint]:
    """Scan ``orig`` (PS bytes of the function under verification) for a
    Rule 42 tail-merge donor jmp.

    Returns a ``TailMergeHint`` if the function's last instruction is
    an unconditional jmp whose target is inside another known function;
    otherwise None.

    Parameters
    ----------
    orig
        Raw PS.EXE bytes of the function under verification.
    orig_off
        Either the virtual address (``is_vaddr=True``, the default) or
        the LE-code-section offset (``is_vaddr=False``) of ``orig[0]``.
        ``decomp_verify`` passes a section offset; standalone callers
        usually pass a vaddr.
    is_vaddr
        Set to False when ``orig_off`` is a section offset rather than
        a vaddr; the scanner adds ``code_base`` (loaded from
        ``symbols.json``) to recover the vaddr.
    symbols_json
        Path to the project's ``symbols.json``; used to resolve the jmp
        target back to a function name and to slice the donor's tail
        bytes.
    code_bytes, code_base
        Optional injection of the LE code-section bytes + its base
        virtual address.  When omitted the scanner falls back to
        ``c2.commands.decomp_verify._load_le_code_and_fixups`` against
        ``data/PS.EXE`` so callers can use this from any context.
    """
    if not orig:
        return None

    sym = _load_symbols(symbols_json)
    base_addr = orig_off if is_vaddr else (orig_off + sym.code_base)

    insns = _disasm_simple(orig, base_addr)
    if not insns:
        return None

    rel_off, size, raw, mnemonic, op_str = insns[-1]

    # We're looking for a near unconditional jmp that ends the function.
    # Encoding: e9 ?? ?? ?? ??  (5 bytes).  Short jmp eb XX (2 bytes) is
    # also valid but ties only fire for very-near targets, where the
    # donor candidate is the immediately following function — Rule 42's
    # save threshold normally rules that out.  We accept both.
    if mnemonic != "jmp":
        return None
    # Indirect jumps (through register / memory) are never tail-merges.
    if not raw or raw[0] not in (0xE9, 0xEB):
        return None

    # Capstone formats absolute branch targets as "0x..." for us.
    op = op_str.strip()
    if not op.startswith("0x"):
        return None
    try:
        target_vaddr = int(op, 16)
    except ValueError:
        return None

    # Self-jumps (loop back to top) aren't tail-merges.
    if base_addr <= target_vaddr < base_addr + len(orig):
        return None

    donor = _function_at(sym, target_vaddr)
    if donor is None:
        return None
    donor_name, donor_start, donor_end = donor

    # Sanity: the merge target must be strictly inside the donor (not
    # at its start — that would be a tail-call, not a merge).
    if target_vaddr <= donor_start:
        return None
    if target_vaddr >= donor_end:
        return None

    # Pull the donor's tail bytes from the LE code section.
    if code_bytes is None:
        from c2.commands.decomp_verify import _load_le_code_and_fixups
        code_bytes, _ = _load_le_code_and_fixups(Path("data/PS.EXE"))
    if code_base is None:
        code_base = sym.code_base

    tail_start = target_vaddr - code_base
    tail_end = donor_end - code_base
    tail = code_bytes[tail_start:tail_end]

    # Disassemble for human-readable preview.  The donor tail almost
    # always ends in `pop … ; ret`; capstone may stop at unknown bytes,
    # which is fine — we only render what's decodable.
    tail_lines = []
    for _o, _s, _b, mn, ops in _disasm_simple(tail, target_vaddr):
        tail_lines.append(f"{mn} {ops}".strip())

    return TailMergeHint(
        donor_name=donor_name,
        donor_start=donor_start,
        merge_target=target_vaddr,
        merge_offset_in_donor=target_vaddr - donor_start,
        jmp_offset_in_self=rel_off,
        tail_bytes=bytes(tail),
        tail_disasm=tuple(tail_lines),
    )


# ── Donor blocking status (Rule 42: donor must be byte-exact first) ─────────
#
# Rule 42 mechanism: Watcom only tail-merges with a donor whose prologue /
# callee-save set / RetPop match.  Until the donor function is itself
# byte-exact, the current function CANNOT match PS -- the merged tail
# bytes are sourced from the donor's epilogue, so any divergence at the
# donor's epilogue propagates here verbatim.
#
# The "exact set" is cached in ``.c2-cache/verify.json`` by the last full
# ``c2 decomp-verify`` run.  We look the donor up there.  If the donor is
# itself diffing, the residue here is a downstream symptom -- the lever
# is on the donor's body, not on this function.

# Module-level cache so single-function `-f` mode doesn't re-parse the
# 12 MB verify.json on every render call.
_donor_status_cache: dict[Path, dict[str, str]] = {}


def _load_donor_status(verify_json: Path) -> dict[str, str]:
    """Build ``{name: 'exact'|'diff'}`` from a verify.json snapshot.

    Returns an empty dict when the cache file is missing.  The result
    is memoised per resolved path.
    """
    key = verify_json.resolve() if verify_json.exists() else verify_json
    cached = _donor_status_cache.get(key)
    if cached is not None:
        return cached
    if not verify_json.exists():
        _donor_status_cache[key] = {}
        return {}
    try:
        data = json.loads(verify_json.read_text())
    except (OSError, json.JSONDecodeError):
        _donor_status_cache[key] = {}
        return {}
    out: dict[str, str] = {}
    for fn in data.get("functions", []):
        name = fn.get("name")
        if not name:
            continue
        if fn.get("diff_byte_count", 0) > 0:
            out[name] = "diff"
        elif fn.get("exact"):
            out[name] = "exact"
        # else: stub / not_found -> omit
    _donor_status_cache[key] = out
    return out


def donor_blocking_status(
    donor_name: str,
    verify_json: Path = Path(".c2-cache/verify.json"),
) -> Optional[str]:
    """Look up whether ``donor_name`` is itself diffing.

    Returns ``"diff"`` when the donor is in the diff set (this function
    is BLOCKED on the donor — don't touch the body until the donor is
    byte-exact), ``"exact"`` when the donor is already byte-exact (the
    residue here is intrinsic, not downstream), or ``None`` when status
    is unknown (no recent full verify run, or donor not in the cache).
    """
    status_map = _load_donor_status(verify_json)
    return status_map.get(donor_name)


@dataclass
class EpilogueChain:
    """Resolved cross-function epilogue chain (Rule 42 stubs).

    PS factors shared epilogues into CHAINS of partial stubs:
    ``pop ebp; jmp <hop>`` → ``pop edi; pop esi; pop edx; pop ecx;
    pop ebx; ret`` (pcsound: 0x118df → 0x13181).  The full restore
    sequence dictates the EXACT callee-save set the RC function must
    end with for ComTail to merge it the same way (suffix match).
    """
    hops: list[tuple[str, int]]          # (owner_name, vaddr) per hop
    restores: list[str]                  # pop regs in restore order
    ends_in_ret: bool

    @property
    def required_saves(self) -> list[str]:
        """Push order (prologue) implied by the restore sequence."""
        return list(reversed(self.restores))


def trace_epilogue_chain(
    hint: TailMergeHint,
    *,
    symbols_json: Path = Path("data/out/symbols.json"),
    code_bytes: Optional[bytes] = None,
    max_hops: int = 4,
) -> Optional[EpilogueChain]:
    """Follow the donor jmp through chained partial-epilogue stubs.

    Starting from ``hint.merge_target``, collect ``pop`` instructions;
    when a stub ends in another unconditional ``jmp``, hop to its
    target (each hop may be owned by a different function).  Stops at
    ``ret`` or after ``max_hops``.
    """
    sym = _load_symbols(symbols_json)
    if code_bytes is None:
        from c2.commands.decomp_verify import _load_le_code_and_fixups
        code_bytes, _ = _load_le_code_and_fixups(Path("data/PS.EXE"))

    hops: list[tuple[str, int]] = []
    restores: list[str] = []
    target = hint.merge_target
    for _ in range(max_hops):
        owner = _function_at(sym, target)
        hops.append((owner[0] if owner else "?", target))
        chunk = code_bytes[target - sym.code_base: target - sym.code_base + 64]
        nxt: Optional[int] = None
        for _o, _s, raw, mn, ops in _disasm_simple(chunk, target):
            if mn == "pop":
                restores.append(ops.strip())
                continue
            if mn == "ret":
                return EpilogueChain(hops, restores, True)
            if mn == "jmp" and raw and raw[0] in (0xE9, 0xEB) \
                    and ops.strip().startswith("0x"):
                nxt = int(ops.strip(), 16)
            break
        if nxt is None:
            return EpilogueChain(hops, restores, False)
        target = nxt
    return EpilogueChain(hops, restores, False)


# ── Block-ownership mapping (Rule 125 hosted blocks) ───────────────────────
#
# A full-image branch index: every direct jmp/jcc (src_vaddr -> dst_vaddr)
# in the PS code section.  Built once per process (~1-2 s), then ownership
# queries are instant.  This is THE tool behind the foreign-frame hint's
# instruction "map which jump sources feed those offsets": inbound foreign
# branches show who executes a hosted block; outbound foreign branches
# show where a function's control flow escapes its symbol range.

_branch_index_cache: dict[int, list[tuple[int, int]]] = {}


def _branch_index(code_bytes: bytes, code_base: int) -> list[tuple[int, int]]:
    key = id(code_bytes)  # one PS image per process in practice
    cached = _branch_index_cache.get(key)
    if cached is not None:
        return cached
    cs = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    cs.skipdata = True
    out: list[tuple[int, int]] = []
    for addr, _size, mn, ops in cs.disasm_lite(code_bytes, code_base):
        if mn == "jmp" or (mn.startswith("j") and len(mn) <= 4):
            t = ops.strip()
            if t.startswith("0x"):
                try:
                    out.append((addr, int(t, 16)))
                except ValueError:
                    pass
    _branch_index_cache[key] = out
    return out


def foreign_branches(
    func_start: int,
    func_end: int,
    *,
    symbols_json: Path = Path("data/out/symbols.json"),
    code_bytes: Optional[bytes] = None,
) -> tuple[list[tuple[str, int, int]], list[tuple[int, str, int]]]:
    """Map block ownership for the vaddr range [func_start, func_end).

    Returns ``(inbound, outbound)``:

    * inbound:  ``(src_owner_name, src_rel_in_owner, dst_rel_off)`` for every
      branch FROM OUTSIDE the range landing inside it (excluding
      branches to func_start = ordinary calls/tail-calls).  These are
      the executors of hosted blocks.
    * outbound: ``(src_rel_off, dst_owner_name, dst_rel_in_owner)`` for
      every branch from inside the range landing outside it (epilogue
      chains, shared call tails, hauled continuations).
    """
    sym = _load_symbols(symbols_json)
    if code_bytes is None:
        from c2.commands.decomp_verify import _load_le_code_and_fixups
        code_bytes, _ = _load_le_code_and_fixups(Path("data/PS.EXE"))
    idx = _branch_index(code_bytes, sym.code_base)
    inbound: list[tuple[str, int, int]] = []
    outbound: list[tuple[int, str, int]] = []
    for src, dst in idx:
        src_in = func_start <= src < func_end
        dst_in = func_start <= dst < func_end
        if src_in and not dst_in:
            owner = _function_at(sym, dst)
            outbound.append((src - func_start,
                             owner[0] if owner else "?",
                             dst - owner[1] if owner else dst))
        elif dst_in and not src_in and dst != func_start:
            owner = _function_at(sym, src)
            inbound.append((owner[0] if owner else "?",
                            src - owner[1] if owner else src,
                            dst - func_start))
    return inbound, outbound


def classify_regpair_exit(
    target_vaddr: int,
    *,
    symbols_json: Path = Path("data/out/symbols.json"),
    code_bytes: Optional[bytes] = None,
    max_hops: int = 4,
) -> str:
    """Resolve a binir ``regpair_const_exit`` jmp target: does the shared
    tail RETURN (pops/stub-chain ending in ret → the EDX:EAX pair is a
    Rule 85 far-ptr return constant) or does it CALL (the pair is the
    callee's (eax,edx) watcall args at a ComTail-merged call site)?

    Returns ``"return"``, ``"args"``, or ``"unknown"``.
    """
    sym = _load_symbols(symbols_json)
    if code_bytes is None:
        from c2.commands.decomp_verify import _load_le_code_and_fixups
        code_bytes, _ = _load_le_code_and_fixups(Path("data/PS.EXE"))
    va = target_vaddr
    for _ in range(max_hops):
        chunk = code_bytes[va - sym.code_base: va - sym.code_base + 96]
        nxt: Optional[int] = None
        for _o, _s, raw, mn, ops in _disasm_simple(chunk, va):
            if mn == "pop":
                continue
            # `add esp, N` is the caller-cleanup that precedes the pops in a
            # stack-arg epilogue stub (e.g. start_tune's far-ptr returns jmp
            # to `add esp,4; pop...; ret`).  Skip it like a pop so the chain
            # resolves to the RET instead of returning "unknown".
            if mn == "add" and ops.replace(" ", "").startswith("esp,"):
                continue
            if mn == "ret":
                return "return"
            if mn == "call":
                return "args"
            if mn == "jmp" and raw and raw[0] in (0xE9, 0xEB) \
                    and ops.strip().startswith("0x"):
                nxt = int(ops.strip(), 16)
            break
        if nxt is None:
            return "unknown"
        va = nxt
    return "unknown"


def render_epilogue_chain(chain: EpilogueChain,
                          rc_saves: Optional[list[str]] = None) -> list[str]:
    """Human lines for the chain: hops, restores, required save suffix,
    and (when RC's save set is supplied) the exact delta to fix."""
    hop_s = " → ".join(f"{n}@{a:#x}" for n, a in chain.hops)
    out = [
        f"epilogue chain: {hop_s}; restores: "
        f"{'; '.join('pop ' + r for r in chain.restores)}"
        f"{'; ret' if chain.ends_in_ret else ' … (unresolved)'}",
        f"  → RC must push EXACTLY {chain.required_saves} (in this order) "
        f"for its epilogue to suffix-match the donor.",
    ]
    if rc_saves is not None and chain.ends_in_ret:
        need, have = chain.required_saves, list(rc_saves)
        missing = [r for r in need if r not in have]
        extra = [r for r in have if r not in need]
        if missing:
            out.append(
                f"  → RC is MISSING save(s) {missing}: PS holds a value "
                f"there — typically a const-store temp (Rule 110) or a "
                f"byte-seat exile (Rule 126); find WHAT PS keeps in "
                f"{missing[0]} before touching source.")
        if extra:
            out.append(
                f"  → RC saves {extra} that the donor never restores — "
                f"an RC value was exiled there (join-read funnel / "
                f"pessimistic wr); the merge cannot fire until it moves.")
    return out


def render_tail_merge_hint(
    hint: TailMergeHint,
    *,
    max_disasm: int = 8,
) -> str:
    """Format a ``TailMergeHint`` body as a single hint line (no markup).

    Output looks like::

        Tail-merge donor: build_wall_from_elastic+0x261 (7 b): pop ecx;
        pop ebx; ret

    The ``max_disasm`` instructions are joined with ``; ``; longer
    tails get an ellipsis.  Always returns a plain string (the caller
    wraps Rich markup around it via ``escape()``).
    """
    head = (
        f"Tail-merge donor: {hint.donor_name}"
        f"+0x{hint.merge_offset_in_donor:X} "
        f"({len(hint.tail_bytes)} b)"
    )
    if not hint.tail_disasm:
        return head
    shown = list(hint.tail_disasm[:max_disasm])
    if len(hint.tail_disasm) > max_disasm:
        shown.append("…")
    return f"{head}: {'; '.join(shown)}"


def render_donor_status_tag(hint: TailMergeHint, donor_status: Optional[str]) -> Optional[str]:
    """Render the DONOR-BLOCKED / donor-byte-exact annotation, or None.

    Returns a plain-text string for the caller to wrap in Rich markup
    (it contains the donor name only -- no markup itself).  ``None``
    when ``donor_status`` is unknown or the donor is at an unhelpful
    status (e.g. stub).
    """
    if donor_status == "diff":
        return (
            f"\u26a0 DONOR-BLOCKED: `{hint.donor_name}` itself diffs "
            f"\u2014 fix the donor's body first, the residue here is "
            f"downstream."
        )
    if donor_status == "exact":
        return (
            f"donor byte-exact \u2014 residue here is intrinsic to this "
            f"function (not a donor problem)."
        )
    return None


# ── Merged-tail expansion (side-by-side disasm aid) ─────────────────────────
#
# When Watcom tail-merges a function's epilogue, the function's last
# instruction is a `jmp` into a DONOR -- the shared tail (the pop/ret
# sequence, or whatever the linker factored out) physically lives in the
# donor, not in the function's own byte range.  A naive side-by-side
# disasm therefore shows nothing on the side that merged: the bytes that
# logically belong to the function are hidden behind the jmp.
#
# `expand_merged_tail` follows the jmp (and any chained partial-epilogue
# hops) and returns the borrowed tail bytes so the renderer can splice
# them back in.  It is side-agnostic: works on the PS image or the
# freshly-built RC image, given that image's code section + a function
# resolver.  This is what lets the verifier display both sides' full
# logical epilogue, so a still-diffing function can be driven until the
# epilogues line up and the merge "just happens".

_EXP_CS = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)


@dataclass(frozen=True)
class TailSegment:
    """One hop of a (possibly chained) merged tail."""
    name:      str    # donor function owning these bytes
    src_off:   int    # section offset of the first borrowed byte
    length:    int    # number of bytes taken from this hop
    start_va:  int    # vaddr of the first borrowed byte
    merge_off: int    # start_va - donor_start (offset within the donor)


@dataclass(frozen=True)
class TailExpansion:
    """Result of expanding a function's trailing tail-merge jmp."""
    jmp_rel:      int                      # offset of the trailing jmp in the body
    jmp_size:     int
    tail_bytes:   bytes                    # concatenated borrowed epilogue bytes
    segments:     tuple[TailSegment, ...]
    ends_in_ret:  bool                     # did the chain resolve to a ret?

    @property
    def label(self) -> str:
        """Short provenance string, e.g. ``basic_temple_screen+0x647`` or a
        chained ``stubA+0x4 →stubB`` for multi-hop epilogues."""
        if not self.segments:
            return "?"
        s0 = self.segments[0]
        out = f"{s0.name}+0x{s0.merge_off:x}"
        if len(self.segments) > 1:
            out += " →" + "→".join(s.name for s in self.segments[1:])
        return out


def ranges_from_offset_map(
    off_by_name: dict[str, int],
    code_base: int,
):
    """Build a ``resolve(vaddr) -> (name, start_va, end_va) | None`` callable
    from a ``{name: section_offset}`` map (e.g. the recompiled image's
    linker map).  Function ends are inferred as the next symbol's start;
    the last symbol gets a small synthetic tail.
    """
    items = sorted(off_by_name.items(), key=lambda kv: kv[1])
    ranges: list[tuple[int, int, str]] = []
    for i, (nm, off) in enumerate(items):
        nxt = items[i + 1][1] if i + 1 < len(items) else off + 256
        ranges.append((off + code_base, nxt + code_base, nm))

    def resolve(va: int) -> Optional[tuple[str, int, int]]:
        # Linear scan is fine for the ~1-2 K symbols we see per build.
        for s, e, n in ranges:
            if s <= va < e:
                return n, s, e
        return None

    return resolve


def expand_merged_tail(
    body: bytes,
    body_off: int,
    *,
    code_bytes: bytes,
    code_base: int,
    resolve,
    max_hops: int = 8,
) -> Optional[TailExpansion]:
    """Follow a function body's trailing tail-merge jmp into its donor(s)
    and return the borrowed epilogue bytes.

    Returns None unless the body's LAST instruction is a near `jmp`
    (``e9``/``eb``) that ends the body exactly and targets the interior of
    another known function (i.e. a Rule 42 tail-merge, not a tail-call to a
    function start).  Chained partial-epilogue stubs (``pop ebp; jmp …``)
    are followed up to ``max_hops`` times; each intermediate jmp is dropped
    and replaced by its target's bytes, so ``tail_bytes`` is the straight
    epilogue the function actually executes.

    Parameters
    ----------
    body, body_off
        Function bytes and their section offset within ``code_bytes``.
    code_bytes, code_base
        The image's code section and its base vaddr (0x10000 for both PS
        and the Watcom-built RC).
    resolve
        ``resolve(vaddr) -> (name, start_va, end_va) | None`` -- see
        ``ranges_from_offset_map`` / ``_function_at``.
    """
    if not body:
        return None
    base_va = body_off + code_base
    insns = list(_EXP_CS.disasm(body, base_va))
    if not insns:
        return None
    last = insns[-1]
    # The jmp must terminate the body exactly (no trailing raw bytes).
    if (last.address - base_va) + last.size != len(body):
        return None
    if last.mnemonic != "jmp" or not last.bytes or last.bytes[0] not in (0xE9, 0xEB):
        return None
    op = last.op_str.strip()
    if not op.startswith("0x"):
        return None
    try:
        target = int(op, 16)
    except ValueError:
        return None
    # A jmp back into our own body is a loop, not a merge.
    if base_va <= target < base_va + len(body):
        return None

    jmp_rel = last.address - base_va
    jmp_size = last.size
    tail = bytearray()
    segments: list[TailSegment] = []
    ends_in_ret = False
    visited: set[int] = set()
    for _ in range(max_hops):
        if target in visited:
            break
        visited.add(target)
        owner = resolve(target)
        if owner is None:
            break
        nm, donor_start, donor_end = owner
        # Strictly inside the donor -> a real merge; at the start -> a
        # tail-call (the target is a whole separate function), skip.
        if not (donor_start < target < donor_end):
            break
        chunk = code_bytes[target - code_base: donor_end - code_base]
        seg_len = 0
        nxt: Optional[int] = None
        hit_ret = False
        for ins in _EXP_CS.disasm(chunk, target):
            if ins.mnemonic == "ret":
                seg_len += ins.size
                hit_ret = True
                break
            if (ins.mnemonic == "jmp" and ins.bytes
                    and ins.bytes[0] in (0xE9, 0xEB)
                    and ins.op_str.strip().startswith("0x")):
                nxt = int(ins.op_str.strip(), 16)
                break
            seg_len += ins.size
        tail += chunk[:seg_len]
        segments.append(TailSegment(
            name=nm,
            src_off=target - code_base,
            length=seg_len,
            start_va=target,
            merge_off=target - donor_start,
        ))
        if hit_ret:
            ends_in_ret = True
            break
        if nxt is None:
            break
        target = nxt

    if not segments:
        return None
    return TailExpansion(
        jmp_rel=jmp_rel,
        jmp_size=jmp_size,
        tail_bytes=bytes(tail),
        segments=tuple(segments),
        ends_in_ret=ends_in_ret,
    )

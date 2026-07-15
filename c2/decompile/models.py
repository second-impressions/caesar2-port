"""Pydantic models + enums for ``c2 decompile``.

Every tool-boundary value is typed here.  Enums for the three binaries /
the two byte-oracle targets / the four shape layers replace the
free-form strings used by the legacy ``c2_ext`` extension.

The ``FinishReport`` is the agent's structured output type — pydantic-ai
will refuse to terminate the run until the model produces one of these,
which gives the orchestrator a typed verdict to dispatch on instead of
having to parse English.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field


# ── enums ────────────────────────────────────────────────────────────────


class Target(str, Enum):
    """Compile target + byte oracle pair for ``verify``."""

    WATCOM = "watcom"   # wcc386 → PS.EXE (DOS 32-bit, Watcom 10.0a)
    MSVC = "msvc"       # cl.exe → CAESAR2.EXE (Win32, MSVC 4.0 /Od)


class Binary(str, Enum):
    """One of the three reference binaries (for read-only inspection)."""

    WATCOM = "watcom"   # PS.EXE          — primary byte oracle
    MSVC = "msvc"       # CAESAR2.EXE     — secondary byte oracle
    MAC = "mac"         # Caesar_II_*.pef — PowerPC source-shape oracle


class FixLayer(str, Enum):
    """The layer of the layered shape-distance that needs work first.

    Strict fix-order: work the highest non-zero layer first.
    """

    IR = "ir"         # wrong source SHAPE (missing else-if, wrong expr, …)
    WIDTH = "width"   # wrong type/signedness on a local
    SPILL = "spill"   # frame / live-range divergence
    SEAT = "seat"     # register-identity tie (often sub-source)
    NONE = "none"     # shape == 0 — pure regalloc/encoding residue


class Verdict(str, Enum):
    """The agent's final classification of its run."""

    BYTE_EXACT = "byte_exact"           # 0/N ✓ — done
    SHAPE_MATCHES = "shape_matches"     # shape == 0 but bytes still residual
    IMPROVED_PARTIAL = "improved_partial"
    NO_CHANGE = "no_change"
    REGRESSED = "regressed"             # should be impossible if revert_to_best honoured
    BUILD_BROKEN = "build_broken"


# ── verify result ────────────────────────────────────────────────────────


class ShapeDistance(BaseModel):
    """Layered byte-INDEPENDENT distance-to-PS, decomposed by residue layer.

    Each layer is ``(divergent, total)`` — fewer divergent is better.
    ``fix_next`` names the highest non-zero layer to attack first.
    """

    ir: tuple[int, int] = (0, 0)
    width: tuple[int, int] = (0, 0)
    spill: tuple[int, int] = (0, 0)
    seat: tuple[int, int] = (0, 0)
    fix_next: FixLayer = FixLayer.NONE
    islands: Optional[int] = None
    """Run-ledger island count — the ir layer's fine-grained unit (one
    island = one local statement-shape divergence in the register-blind
    dual-marks stream alignment).  0 = regalloc_pure (every instruction
    matches register-blind — stop restructuring, the residue is seats/
    slots/encoding); None = ledger unavailable (ir fell back to the
    byte-diff-aligned binir count).  Drill in with ``lines()``."""

    @property
    def is_matched(self) -> bool:
        return all(d == 0 for d, _ in (self.ir, self.width, self.spill, self.seat))

    def fmt(self) -> str:
        """``ir 0/14 (isl 0) · width 1/12 · spill 0/5 · seat 1/8 → seat``"""
        ir_cell = f"ir {self.ir[0]}/{self.ir[1]}"
        if self.islands is not None:
            ir_cell += f" (isl {self.islands})"
        parts = [
            ir_cell,
            f"width {self.width[0]}/{self.width[1]}",
            f"spill {self.spill[0]}/{self.spill[1]}",
            f"seat {self.seat[0]}/{self.seat[1]}",
        ]
        return " · ".join(parts) + f" → fix-next: {self.fix_next.value}"


class DiffRow(BaseModel):
    """One row of an aligned PS-vs-RC asm diff."""

    side: Literal["both", "target", "ours", "changed"]
    target_l: Optional[str] = None      # 'L+3' / 'D+0' / None
    ours_l: Optional[str] = None
    offset: int
    target_text: Optional[str] = None
    ours_text: Optional[str] = None


class BestSnapshot(BaseModel):
    """Snapshot of the best verify seen so far in this run.

    Persisted to ``<run_dir>/best/verify.json`` by the orchestrator on
    every is_new_best transition.
    """

    byte_diff: int
    shape: Optional[ShapeDistance] = None
    target: Target
    taken_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class VerifyResult(BaseModel):
    """One ``verify`` tool call's result.

    This is the workflow's currency.  Lives in three places:
      * the tool return (what the model sees)
      * the run's ``history.jsonl`` (audit trail)
      * the orchestrator's live state (status stream)
    """

    target: Target
    build_ok: bool
    stderr: str = ""
    byte_diff: int = 0                # 0 ⇒ exact
    target_size: int = 0
    your_size: Optional[int] = None
    exact: bool = False
    shape: Optional[ShapeDistance] = None
    """Layered shape distance — the per-function JUDGE metric.  Only
    computed for ``target=watcom`` (MSVC encoding differs too much for
    the layered comparison).  ``None`` on build failure or MSVC."""
    diff_rows: list[DiffRow] = Field(default_factory=list)
    has_line_numbers: bool = False
    """Whether the L+N source-line column of ``diff_rows`` is populated.
    ``True`` for ``target=watcom`` (both sides built ``-d1``); ``False``
    for ``target=msvc`` (no recoverable line info on either side)."""
    donor: Optional[str] = None
    fallthrough_callee: Optional[str] = None
    is_new_best: bool = False
    best_so_far: Optional[BestSnapshot] = None
    notes: list[str] = Field(default_factory=list)
    """Free-form caveats the agent should be aware of (e.g. 'shape is
    not computed on the MSVC target' or 'L+N columns are not
    available on this oracle').  Always non-empty when a field is
    intentionally None so the agent isn't left guessing."""

    def headline(self) -> str:
        """``✓ exact`` / ``✗ 47 byte diff [watcom]`` / ``✗ build failed``."""
        if not self.build_ok:
            return "✗ build failed"
        if self.exact:
            return f"✓ exact [{self.target.value}]"
        return f"✗ {self.byte_diff} byte diff [{self.target.value}]"


# ── disasm ───────────────────────────────────────────────────────────────


class DisasmRow(BaseModel):
    offset: int
    line: Optional[int] = None      # the L<N> column (Hard Rule #4)
    bytes_hex: str
    mnemonic: str
    operands: str


class DisasmResult(BaseModel):
    binary: Binary
    function: str
    rows: list[DisasmRow] = Field(default_factory=list)
    has_line_numbers: bool = False
    """Whether the ``line`` column of each row is populated.  ``True``
    for the Watcom oracle (PS.EXE was built ``-d1``); ``False`` for
    MSVC (CAESAR2.EXE carries no recoverable line info) and Mac (PPC,
    no source mapping in our pipeline)."""
    raw_text: Optional[str] = None
    """For Mac PPC asm where row-level parsing isn't reliable, the
    full unparsed output from ``c2 mac-fn``.  Falls back to this when
    parsing produces 0 rows so the agent never gets an empty result."""
    error: Optional[str] = None


# ── decompile ────────────────────────────────────────────────────────────


class DecompileResult(BaseModel):
    """Ghidra-decompiled C code for an MSVC or Mac function."""

    binary: Binary                    # MSVC or MAC (Watcom uses ``fetch`` instead)
    function: str
    signature: Optional[str] = None
    code: str = ""
    error: Optional[str] = None


# ── info / nearest / fetch / lookup ──────────────────────────────────────


class CallInfo(BaseModel):
    name: str
    times: int


class TypeInfo(BaseModel):
    name: str
    header: str
    definition: str


class SiblingInfo(BaseModel):
    name: str
    score: float
    source_file: Optional[str] = None


class NameRelative(BaseModel):
    """A function whose name differs by exactly one template-instantiation
    token (zoom level, render layer, direction, with/no sides, …).

    When ``status == "byte-exact"`` the relative's source is the
    single strongest PS-faithful template available — it shows exactly
    the shape PS expects for the family.  ``fetch(<name>)`` reads it.
    """
    name: str
    pattern: str
    status: str   # 'byte-exact' | 'diffing' | 'unknown'
    byte_diff: int = 0
    source_file: Optional[str] = None


class FunctionInfo(BaseModel):
    name: str
    address_hex: str
    size: int
    source_file: Optional[str] = None
    signature: Optional[str] = None
    prologue_pushes: list[str] = Field(default_factory=list)
    stack_frame: int = 0
    argc: int = 0
    source_line_range: Optional[tuple[int, int]] = None
    calls: list[CallInfo] = Field(default_factory=list)
    types: list[TypeInfo] = Field(default_factory=list)
    siblings: list[SiblingInfo] = Field(default_factory=list)
    name_relatives: list[NameRelative] = Field(default_factory=list)
    tail_merge_donor: Optional[str] = None


class NearestHit(BaseModel):
    name: str
    score: float
    source_file: Optional[str] = None
    # Pool is restricted to byte-exact functions, so ``status`` is implicit.


class NearestResult(BaseModel):
    hits: list[NearestHit] = Field(default_factory=list)
    query_kind: Literal["function", "snippet"]


class FetchResult(BaseModel):
    """C source of a byte-exact function (read-only study template)."""

    name: str
    source_file: Optional[str] = None
    code: str = ""
    error: Optional[str] = None


# ── regtrace ─────────────────────────────────────────────────────────


class SeatSwap(BaseModel):
    """One value seated in a different register than PS.

    Built directly from :func:`c2.commands.regtrace.vs_ps_data`.  The
    ``lever`` / ``best-guess`` / ``do-this`` hints from the text view
    are DELIBERATELY OMITTED — the agent should observe the swap (which
    value, which registers, ``tie`` Y/N) and reason about it itself,
    not follow an embedded recommendation that may not generalise.
    """
    value: str
    """Source-level value name (``(temp)`` for anonymous compiler temps)."""
    rc: str        # which register our compile put it in (e.g. "EBX")
    ps: str        # which register PS.EXE put it in (e.g. "EDI")
    savings: int   # the allocator's per-conflict savings for this value
    tie: bool      # True ⇒ equal-savings ConfBefore tie; a weaker signal than
                   # chain_verdict -- prefer the latter when present
    chain_verdict: Optional[str] = None
    """CERTIFIED full-chain flip verdict (c2.regalloc.seatchain, identity
    6,243/6,243): ``masked`` (live-range lever), ``outscored`` (the
    winner's credits are per-instruction named -- de-CSE/de-name/reorder
    lever), ``tie-order`` (Rule 115/28a order lever), ``vetoed``
    (savings), ``not-a-candidate`` (type class -- Rule 151 first),
    ``no-alloc-row (rover/scratch)`` (not an allocator seat at all).
    Authoritative over ``tie`` when they disagree."""
    chain_mask_rows: int = 0     # masked: count of contributing walk rows
    chain_credits: int = 0       # outscored: count of named winner credits


class FirstDivergence(BaseModel):
    """Where the first PS<->RC seat divergence occurs in the asm."""
    offset: int                # byte offset within the function
    line: Optional[int] = None # PS -d1 source line at that offset
    rc: str                    # RC register involved
    ps: str                    # PS register involved
    ps_asm: str = ""           # the PS-side instruction string
    rc_asm: str = ""           # the RC-side instruction string


class RegtraceResult(BaseModel):
    """The Watcom 10.0a register-allocator ground-truth lens.

    Backed by :func:`c2.commands.regtrace.vs_ps_data` — the structured
    output of running the REAL 10.0a allocator on the function's TU and
    correlating with the live PS-vs-RC diff.  Run this when
    ``shape.fix_next == FixLayer.SEAT`` and your source-shape edits
    aren't moving the seat layer: regtrace tells you WHICH value is
    seated wrong, in WHICH registers, and WHETHER the swap is reachable
    from source (``tie=True``) or sits outside the regalloc surface
    (``tie=False`` ⇒ likely sub-source residue — classify and finish).

    Lever / best-guess hints from the text view are NOT exposed here:
    the data is the observation, not the recommendation.
    """

    function: str
    verdict: str = ""
    """One-word headline of the seat-diff verdict (``clean`` / ``tie`` /
    ``not_tie`` / ``shape_mismatch`` / etc.)."""
    coverage: int = 0
    """Number of register operands compared between PS and RC."""
    swaps: list[SeatSwap] = Field(default_factory=list)
    """Per-value seat swaps; empty when the verdict is ``clean``."""
    first_divergence: Optional[FirstDivergence] = None
    """The earliest offset where PS and RC disagree on a register seat."""
    shape_distance: Optional[ShapeDistance] = None
    """The layered shape distance at the time of the trace.  Same
    layered form as :class:`VerifyResult.shape` so callers can compare."""
    error: Optional[str] = None


# ── -d1 line ledger (W1 witness) ───────────────────────────────


class LineLedgerRow(BaseModel):
    """One PS ``-d1`` line RUN, aligned against your scratch.c via the
    DUAL-MARKS run ledger (register-blind stream alignment; each side
    segmented by its OWN -d1 marks — attribution stays exact at any
    function size)."""
    ps_line: int
    """PS's relative source line (the ``L+N`` of the diff view); -1 on
    an unanchored rc_only row."""
    rc_lines: list[int] = Field(default_factory=list)
    """ABSOLUTE scratch.c line numbers of the RC instructions aligned
    to this run — these are the lines to edit.  >1 entries = your
    source SPLITS what PS emitted under ONE mark (byte-neutral packing
    when the verdict is ``pack``)."""
    ps_insns: int = 0
    rc_insns: int = 0
    verdict: str = "match"
    """``match`` (every insn of the run matches register-blind — do not
    touch) | ``pack`` (matches, but your source spreads the run over
    several lines where the original wrote ONE — byte-neutral packing
    witness, do NOT chase it for bytes) | ``form`` (a divergence island
    touches this run: real statement-shape work — see ``tags`` +
    the ops fields) | ``ps_only`` (PS emits instructions here with NO
    RC counterpart: a statement/form you LACK) | ``rc_only`` (your
    source emits instructions PS lacks: remove/inline them)."""
    ps_only_ops: dict[str, int] = Field(default_factory=dict)
    rc_only_ops: dict[str, int] = Field(default_factory=dict)
    ps_head: str = ""
    rc_head: str = ""
    order_flip: bool = False
    tags: list[str] = Field(default_factory=list)
    """Island family tags for divergent rows: ``width`` / ``zext-idiom``
    (char-vs-int local, movzx / and 0xff / clear-first — Rules 49/151),
    ``signedness`` (jl↔jb twins — signed vs unsigned local),
    ``loop-form`` (rotated for vs head-tested while — Rules 134/93),
    ``slot`` (same ops, different [esp+N] — Rule 107, usually
    downstream), ``frame`` (frame size differs — local SET differs),
    ``const`` (immediate differs), ``ops`` (genuinely different
    instructions — read the PS side; that IS the target shape)."""
    """PS's line number stepped BACKWARD here while yours stepped
    forward (or vice versa): the original source had these statements
    in a different ORDER (Hard Rule #8 smell)."""


class LinesResult(BaseModel):
    """The per-line ``-d1`` ledger — the W1 witness, statement by statement.

    PS.EXE was compiled ``-d1``: every source LINE gets a mark in the
    debug info, and your scratch.c compile gets the same.  This ledger
    segments EACH side by its OWN marks and aligns the two
    REGISTER-BLIND canonical instruction streams (``c2.runledger``), so
    attribution stays EXACT at any function size (it does NOT drift with
    the byte diff).  Per PS line run it reports: how many instructions
    each side emits, which scratch.c lines align there, the divergence
    family ``tags``, and what binir constructs differ.  It is the tool
    for working a BIG function statement-by-statement instead of
    holding the whole diff in your head: walk rows top-down, fix the
    FIRST non-match row, re-verify, repeat.  Zero divergent rows on a
    still-diffing function = the whole diff is register seats/slots/
    encoding (regalloc territory -- do NOT restructure the source).
    """
    function: str
    total: int = 0
    divergent: int = 0
    rows: list[LineLedgerRow] = Field(default_factory=list)
    """Divergent rows only (pass ``all=True`` for every row)."""
    note: str = ""
    error: Optional[str] = None


# ── win /Od named-local census (W2 witness) ───────────────────────


class SlotInfo(BaseModel):
    """One ``[ebp-N]`` frame slot in an MSVC /Od compile."""
    slot: str          # e.g. "ebp-0x14"
    widths: str        # access widths seen: subset of "bwd"
    n_uses: int
    first_use: str     # asm of the first instruction touching it


class CensusResult(BaseModel):
    """Named-local census: your scratch.c (MSVC /Od) vs CAESAR2.EXE.

    At /Od every named source local owns a distinct ``[ebp-N]`` frame
    slot, so CAESAR2.EXE's slot set is a WITNESS of the original
    source's local-variable set — the input that decides Watcom conflict
    membership, savings rank, and the spill boundary.  ``delta`` is
    ``len(slots_theirs) - len(slots_ours)``:

    * ``> 0`` — the original declared MORE locals: find the unmatched
      slot in ``slots_theirs`` (width + use profile) and NAME that value
      in your source.
    * ``< 0`` — your source INVENTED locals the original lacks: inline
      them.
    * ``== 0`` — the local SET matches; check widths for type drift.

    Trust gate: only act when ``gate == "usable"`` (the CAESAR2.EXE
    function mapping is fuzzy; ``quality`` is the aligned-instruction
    match ratio).  The Windows source is a later cut — treat every
    delta as a CANDIDATE and adjudicate against the PS asm + the -d1
    line marks before editing.
    """
    function: str
    ok: bool
    note: str = ""
    quality: float = 0.0
    gate: str = ""                 # "usable" | "caution" | "mapping-suspect"
    frame_ours: Optional[int] = None
    frame_theirs: Optional[int] = None
    slots_ours: list[SlotInfo] = Field(default_factory=list)
    slots_theirs: list[SlotInfo] = Field(default_factory=list)
    delta: int = 0


class LookupHit(BaseModel):
    name: str
    address_hex: str
    kind: Literal["function", "global", "label"] = "function"
    source_file: Optional[str] = None


class LookupResult(BaseModel):
    query: str
    hits: list[LookupHit] = Field(default_factory=list)


# ── trace-level spelling tools (spell / fusion / walk_order / suggest) ───


class BirthDiff(BaseModel):
    """One birth-stream comparison (block births or IL births)."""

    verdict: str = ""
    """``identical`` or ``diverged``."""
    n_base: int = 0
    n_cand: int = 0
    delta_lines: list[int] = Field(default_factory=list)
    """Source lines whose emission count changed (IL births only) --
    the finest-grained edit targets the trace can name."""
    first_delta: Optional[int] = None
    """First diverging birth ordinal (block births only)."""


class SpellResult(BaseModel):
    """Trace-only screening of the CURRENT scratch.c against the best
    snapshot: at which compiler stage does the source distinction DIE?

    The staged ladder: tree -> block births (bo) -> IL births (ni) ->
    LdStAlloc walk (lw).  ``verdict`` is the walk-level headline:

    * ``INERT@TREE`` -- the parser canonicalized the edit away; the
      spelling family is provably unreachable, try a different IDEA.
    * ``INERT@BURN`` -- trees differ but the walk is identical; read
      ``il_births.delta_lines``: identical IL births = canonicalized AT
      emission (deepest inert, stop the family); diverged births = a
      post-emission pass re-converged it (siblings at those lines may
      survive).
    * ``LIVE...`` -- the walk differs (advance deltas shown); worth a
      byte ``verify``.

    Costs one container trace compile (~15 s); MUCH cheaper than
    reasoning from a byte diff about whether an edit even reached the
    compiler's back end."""

    function: str
    verdict: str = ""
    adv_base: dict[str, int] = Field(default_factory=dict)
    """Per-rover-class advance counts in the BASELINE (best) source."""
    adv_cand: dict[str, int] = Field(default_factory=dict)
    """Per-rover-class advance counts in the CURRENT scratch.c."""
    block_births: Optional[BirthDiff] = None
    il_births: Optional[BirthDiff] = None
    error: Optional[str] = None


class FusionRow(BaseModel):
    """One RISCified rover op's fuse fate."""

    fr_idx: int
    line: Optional[int] = None
    state: str = ""
    """``fused`` or ``lcx0``..``lcx5`` (named rejection) or
    ``no-record``."""
    meaning: str = ""
    """Human meaning of an lcx rejection (empty for fused)."""


class CompressAttempt(BaseModel):
    """One LdStCompress pair-scan attempt (the cw record)."""

    ins: str
    blk: Optional[int] = None
    """Chain-block index (lw walk order) the ins lives in."""
    opcode: int = 0
    prevkind: int = 0
    """Pair-recognition kind of the PREVIOUS chain ins: 3 = recognized
    MOV load half; 0x1NN = not a MOV, NN = that ins's opcode (0x14b =
    BLOCK HEADER: the halves are chain-separated even when the final
    layout is byte-adjacent)."""
    nextkind: int = 0
    outcome: str = ""


class FusionResult(BaseModel):
    """The fr->fusion map + every compress attempt's pair-scan context
    for the CURRENT scratch.c.  The split (fr) happens at PostOptimize
    HEAD; the fuse decision runs ONCE at PostOptimize END, after Score
    and the intermediate passes have perturbed adjacency -- an lcx0
    reject here is the byte-level \"hoist\" fingerprint."""

    function: str
    rows: list[FusionRow] = Field(default_factory=list)
    attempts: list[CompressAttempt] = Field(default_factory=list)
    error: Optional[str] = None


class WalkOrderRow(BaseModel):
    walk: int
    lines: str = ""
    layout: int = 0
    birth: Optional[str] = None
    """Front-end birth ordinal (chain order at GenBlock time), or
    ``opt`` for optimizer-born merge blocks."""
    moved: bool = False


class WalkOrderResult(BaseModel):
    """Walk-vs-layout block map for the CURRENT scratch.c.  ``moved``
    rows are walk-order divergence candidates; birth ordinals running
    OUT of walk order = the optimizer restructured a source-ordered
    chain (the reverse-arm class).  Consult the construct -> block-birth
    dictionary (watcom10.0a docs/block-birth-dictionary.md) before
    designing a structural variant: labels add a walk-invisible birth;
    &&/||/nested-if are birth-identical; loop forms have distinct
    signatures."""

    function: str
    rows: list[WalkOrderRow] = Field(default_factory=list)
    reverse_arm: bool = False
    """True when birth ordinals run out of walk order."""
    opt_born: int = 0
    error: Optional[str] = None


class SuggestCandidate(BaseModel):
    tag: str
    """The generator tag, e.g. ``de_invent(kind)`` (fold: read the
    global/field inline; +1 rover advance) or ``cache_field(...)``
    (unfold: name the repeated read; -1)."""
    lines: list[int] = Field(default_factory=list)
    path: str = ""
    """Candidate file (relative to the sandbox) -- read/copy it over
    scratch.c to apply."""
    verdict: str = ""
    """Screening verdict (same ladder as :class:`SpellResult`); only
    ``LIVE...`` candidates are worth a byte verify."""


class SuggestResult(BaseModel):
    """Machine-generated fold/unfold candidate spellings for the rover
    census, written as real files into the sandbox and trace-screened.
    The generation machinery is hazard-checked (single-write,
    side-effect-free, no intervening call/store), so every candidate is
    semantics-preserving by construction."""

    function: str
    candidates: list[SuggestCandidate] = Field(default_factory=list)
    note: str = ""
    error: Optional[str] = None


# ── file ops ─────────────────────────────────────────────────────────────


class WriteResult(BaseModel):
    """Outcome of a ``write`` / ``edit`` tool call."""

    path: str
    bytes_written: int
    ok: bool = True
    message: Optional[str] = None


# ── search ──────────────────────────────────────────────────────────────────


class SearchHit(BaseModel):
    """One ripgrep match inside the sandbox."""
    file: str            # path relative to the sandbox work dir
    line: int            # 1-indexed line number in that file
    text: str            # the matching line's text (un-coloured)


class SearchResult(BaseModel):
    pattern: str
    scope: str           # the search root the agent passed in
    hits: list[SearchHit] = Field(default_factory=list)
    truncated: bool = False
    error: Optional[str] = None


class ReadResult(BaseModel):
    """Outcome of a ``read`` tool call."""

    path: str
    content: str
    truncated: bool = False


# ── start ────────────────────────────────────────────────────────────────


class StartResult(BaseModel):
    """What ``start`` returns: a snapshot of the composed workspace."""

    function: str
    address_hex: str
    target_size: int
    target: Target
    cflags: list[str]
    source_file: Optional[str] = None
    signature: Optional[str] = None
    tail_merge_donor: Optional[str] = None
    scratch_excerpt: str               # first N lines of scratch.c
    info_md: str                       # the composed info.md
    initial_verify: Optional[VerifyResult] = None


# ── finish ───────────────────────────────────────────────────────────────


class AgentFinishReport(BaseModel):
    """The MINIMAL schema the agent is asked to produce.

    Only the four fields below — each a short scalar / string — so
    weaker models can fill them in reliably.  The previous schema
    (with nested ``VerifyResult`` objects for ``final_verify`` /
    ``best_verify``) routinely exhausted glm-5.2-short's output-retry
    budget AND blew past its context window with retry prompts.

    The orchestrator merges this with workspace-observed ground truth
    into the richer :class:`FinishReport` that the CLI returns.
    """

    verdict: Verdict = Field(
        description=(
            "Pick ONE: byte_exact (verify reported 0/N ✓) | "
            "shape_matches (shape all zero, byte residue remains) | "
            "improved_partial (some progress; not done) | "
            "no_change (ended at base) | regressed (worse than base) | "
            "build_broken (scratch.c doesn't compile)."
        ),
    )
    reason: str = Field(
        max_length=800,
        description=(
            "Brief free-text rationale: what you tried, what landed, "
            "what (if anything) the residue is.  Keep under ~500 chars."
        ),
    )
    classification: Optional[str] = Field(
        default=None,
        description=(
            "For shape_matches / improved_partial: name the residue class "
            "(e.g. 'regalloc_temp', 'spill_tiebreak', 'donor_flip', "
            "'rover_on_temp', 'outside_regalloc').  Omit on byte_exact."
        ),
    )
    next_suggested_tool: Optional[str] = Field(
        default=None,
        description=(
            "Tool the next-step human/agent should reach for (e.g. "
            "'c2 regtrace --explain', 'c2 forge solve …').  Omit on done."
        ),
    )


class FinishReport(BaseModel):
    """The RICH final report the CLI exposes — agent fields + workspace truth.

    Built by the orchestrator: takes the model's :class:`AgentFinishReport`
    and merges in ``function``, ``final_target``, ``final_verify``, and
    ``best_verify`` from the workspace's history / best snapshot.  The
    model is never asked to reconstruct those.
    """

    function: str
    final_target: Target
    verdict: Verdict
    reason: str = Field(max_length=800)
    classification: Optional[str] = None
    next_suggested_tool: Optional[str] = None
    final_verify: Optional[VerifyResult] = None
    best_verify: Optional[VerifyResult] = None
    run_dir: Optional[str] = None
    """Absolute path to this agent's run directory.  Populated by the
    orchestrator so a multi-replica race (``--count N``) can locate the
    winning replica's ``best/`` snapshot and apply it."""


# ── orchestrator event types (for jsonl mirror) ──────────────────────────


class AgentStatus(str, Enum):
    PENDING = "pending"
    COMPOSING = "composing"
    RUNNING = "running"
    FINISHING = "finishing"
    DONE = "done"
    FAILED = "failed"


class AgentSnapshot(BaseModel):
    """Live status snapshot emitted by the reporter."""

    fn: str
    status: AgentStatus
    started_at: float                 # unix ts
    turns: int = 0
    tool_calls: int = 0
    last_tool: Optional[str] = None
    last_event: Optional[str] = None
    best: Optional[BestSnapshot] = None
    current: Optional[VerifyResult] = None
    final: Optional[FinishReport] = None
    error: Optional[str] = None

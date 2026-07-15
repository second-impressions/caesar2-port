"""Pydantic-AI tool functions for the decompile subagent.

Each tool is a thin, typed wrapper around either the engine glue or a
focused c2-core helper.  All side effects (history append, best-snapshot
save) flow through :class:`Workspace`; the agent never touches the
orchestrator's run-dir metadata directly.

The tools are wired onto the Agent in :mod:`c2.decompile.agent`.  Every
tool here takes ``ctx: RunContext[AgentDeps]`` first; ``AgentDeps``
carries the Workspace + the engine project + the running event reporter.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from pydantic_ai import ModelRetry, RunContext

from c2.decompile import engine_glue
from c2.decompile._engine.project import ProjectConfig as EngineProjectConfig
from c2.decompile.models import (
    Binary,
    BirthDiff,
    CallInfo,
    CensusResult,
    CompressAttempt,
    FusionResult,
    FusionRow,
    SpellResult,
    SuggestCandidate,
    SuggestResult,
    WalkOrderResult,
    WalkOrderRow,
    DecompileResult,
    DisasmResult,
    DisasmRow,
    FetchResult,
    FirstDivergence,
    FixLayer,
    FunctionInfo,
    LookupHit,
    LookupResult,
    NameRelative,
    LineLedgerRow,
    LinesResult,
    NearestHit,
    NearestResult,
    ReadResult,
    RegtraceResult,
    SearchHit,
    SearchResult,
    SeatSwap,
    ShapeDistance,
    SlotInfo,
    SiblingInfo,
    Target,
    TypeInfo,
    VerifyResult,
    WriteResult,
)
from c2.decompile.workspace import Workspace


# ── deps ─────────────────────────────────────────────────────────────────


@dataclass
class AgentDeps:
    """Carried through every tool call via :class:`RunContext`.

    Also holds the small bit of state needed to enforce the
    inspect-before-revert policy (see :func:`revert_to_best`).
    """

    workspace: Workspace
    project: EngineProjectConfig
    target: Target              # default target for verify
    function: str               # the agent's TASK
    on_event: object = None     # callable: (event_type:str, payload:dict) -> None

    # ── inspect-before-revert state machine ───────────────────────────
    # ``edits_since_inspection`` increments every time the agent
    # mutates ``scratch.c`` (write/edit) and resets to 0 when the
    # agent inspects the assembly via ``verify(diff=True)`` or
    # ``disasm`` of the function under test.  ``revert_to_best`` is
    # REFUSED (ModelRetry) while ``edits_since_inspection > 0`` so the
    # agent can't bail out on a byte-count rise without reading the
    # asm first — the byte count alone is the wrong judge metric
    # (AGENTS.md Hard Rule #3: judge by SHAPE + asm).
    edits_since_inspection: int = 0

    def mark_edit(self) -> None:
        self.edits_since_inspection += 1

    def mark_asm_inspected(self) -> None:
        self.edits_since_inspection = 0

    def event(self, etype: str, **payload) -> None:
        if self.on_event is None:
            return
        try:
            self.on_event(etype, payload)
        except Exception:
            pass


def _safe_resolve(ws: Workspace, path: str) -> Path:
    """Resolve ``path`` inside the sandbox, converting policy violations
    into :class:`ModelRetry` so the agent can self-correct.

    :func:`Workspace.resolve_in_work` raises ``ValueError`` for absolute
    paths and for paths that escape the sandbox.  If a tool lets that
    bubble up, pydantic-ai treats it as a hard error and KILLS the
    agent — worked-example: ``show_regionmap_top`` once hallucinated
    ``search(path="/proc")`` and lost ~2 minutes of progress because
    that ValueError terminated the run.  Translating to ``ModelRetry``
    surfaces the policy as a feedback message the model can react to.
    """
    try:
        return ws.resolve_in_work(path)
    except ValueError as exc:
        raise ModelRetry(
            f"path policy violation: {exc}.  Allowed: paths RELATIVE to "
            f"the sandbox root — e.g. `scratch.c`, `info.md`, "
            f"`open-watcom/bld/cg/intel/c/<file>`.  Absolute paths "
            f"(like `/proc/…` or `/home/…`) and paths that escape the "
            f"sandbox are rejected."
        ) from None


def _truncate(text: str, max_bytes: int) -> tuple[str, bool]:
    b = text.encode("utf-8")
    if len(b) <= max_bytes:
        return text, False
    return b[:max_bytes].decode("utf-8", errors="ignore") + "\n…[truncated]", True



# (No bootstrap tool: the orchestrator composes the workspace BEFORE
# the agent runs, and embeds the function brief in the initial user
# message.  Tools below operate on the already-populated work/ dir.)


# ── read / write / edit ──────────────────────────────────────────────────


async def read(
    ctx: RunContext[AgentDeps], path: str,
    offset: int = 0, limit: int | None = None,
) -> ReadResult:
    """Read one file from the sandbox.

    Relative paths only.  ``scratch.c`` / ``info.md`` are the usual two;
    ``open-watcom/bld/cg/...`` is read-only available for codegen-source
    consultation.

    The TU's header block (every prototype, typedef, pragma, global)
    lives INLINED at the top of ``scratch.c`` -- no separate file to
    chase.

    The sibling files ``tu-body.c`` / ``tu-post.c`` carry the
    function-definition halves of the source TU.  They are MASSIVE --
    often hundreds of KB -- and should NOT be read in full.  Use the
    ``offset`` (1-based line number) + ``limit`` (max lines) args to
    do targeted reads, or call ``search(pattern, path="tu-body.c")``
    to grep them.  A read without ``offset``/``limit`` on either of
    those files will be refused.
    """
    if path.strip() in {
        "tu-body.c", "tu-post.c", "./tu-body.c", "./tu-post.c",
    }:
        if limit is None and offset == 0:
            raise ModelRetry(
                f"{path} is the surrounding source TU and is too large"
                " to load in full -- pass offset (1-based line) + limit"
                " (max lines) for a targeted read, or call"
                f" search(pattern, path={path!r}) to grep it."
            )
    p = _safe_resolve(ctx.deps.workspace, path)
    if not p.is_file():
        raise ModelRetry(f"no such file: {path}")
    content = p.read_text(errors="replace")
    if offset > 0 or limit is not None:
        lines = content.splitlines(keepends=True)
        start = max(0, offset - 1) if offset > 0 else 0
        end = start + limit if limit is not None else len(lines)
        content = "".join(lines[start:end])
    content, truncated = _truncate(content, 64_000)
    return ReadResult(path=path, content=content, truncated=truncated)


async def write(ctx: RunContext[AgentDeps], path: str, content: str) -> WriteResult:
    """Overwrite one file in the sandbox.

    Only ``scratch.c`` is writable; every other path raises.
    """
    if path.strip() not in {"scratch.c", "./scratch.c"}:
        raise ModelRetry(
            f"refused: only scratch.c is writable in this sandbox "
            f"(got {path!r}); use edit() for partial changes."
        )
    p = _safe_resolve(ctx.deps.workspace, path)
    n = p.write_text(content)
    ctx.deps.mark_edit()
    ctx.deps.workspace.append_history({"type": "write", "path": path, "bytes": len(content)})
    return WriteResult(path=path, bytes_written=len(content.encode("utf-8")))


async def edit(
    ctx: RunContext[AgentDeps],
    path: str,
    old_text: str,
    new_text: str,
) -> WriteResult:
    """Exact-text replacement in a sandbox file (only scratch.c writable).

    ``old_text`` must appear exactly once.  Mirrors pi's ``edit`` tool
    semantics.
    """
    if path.strip() not in {"scratch.c", "./scratch.c"}:
        raise ModelRetry(
            f"refused: only scratch.c is editable (got {path!r})."
        )
    p = _safe_resolve(ctx.deps.workspace, path)
    src = p.read_text()
    count = src.count(old_text)
    if count == 0:
        raise ModelRetry(
            "old_text not found in scratch.c — read the file again to "
            "see the current contents."
        )
    if count > 1:
        raise ModelRetry(
            f"old_text matches {count} places in scratch.c — make it "
            "unique by including more surrounding context."
        )
    new_src = src.replace(old_text, new_text, 1)
    p.write_text(new_src)
    ctx.deps.mark_edit()
    ctx.deps.workspace.append_history({
        "type": "edit", "path": path,
        "old_len": len(old_text), "new_len": len(new_text),
    })
    return WriteResult(
        path=path, bytes_written=len(new_src.encode("utf-8")),
        message=f"replaced 1 occurrence ({len(old_text)} -> {len(new_text)} bytes)",
    )


# ── verify / revert_to_best ──────────────────────────────────────────────


async def verify(
    ctx: RunContext[AgentDeps],
    diff: bool = False,
    target: Optional[Target] = None,
) -> VerifyResult:
    """Compile scratch.c and byte-compare against the chosen oracle.

    ``target=Target.WATCOM`` (the default) compiles with wcc386 and
    diffs against PS.EXE; ``target=Target.MSVC`` compiles with cl.exe
    and diffs against CAESAR2.EXE.  ``diff=True`` includes the windowed
    PS-vs-RC asm diff rows; otherwise just the headline + shape.

    JUDGE EVERY EDIT BY ``shape``, NOT ``byte_diff`` (Hard Rule #3).
    """
    import asyncio
    t = target or ctx.deps.target
    deps = ctx.deps
    deps.event("verify_start", target=t.value)
    # Run the (blocking, podman-shelling) verify off the event loop so
    # parallel agents don't serialize.
    vr = await asyncio.to_thread(
        engine_glue.run_verify,
        workspace=deps.workspace, project=deps.project,
        target=t, diff=diff,
    )
    # A verify-with-diff IS an asm inspection — the agent saw the
    # PS-vs-RC rows.  A bare verify() (diff=False) gives only the
    # headline + shape and does NOT clear the revert guard.
    if diff:
        deps.mark_asm_inspected()
    deps.event(
        "verify_done",
        target=t.value,
        build_ok=vr.build_ok,
        byte_diff=vr.byte_diff,
        exact=vr.exact,
        is_new_best=vr.is_new_best,
        shape=vr.shape.model_dump() if vr.shape else None,
    )
    return vr


async def revert_to_best(ctx: RunContext[AgentDeps]) -> VerifyResult:
    """Restore scratch.c to the best version this run has seen.

    Best is determined by the layered shape sum (judge metric); on ties,
    by byte_diff.  Re-runs verify against the default target afterward
    so you get a fresh VerifyResult to reason from.

    **Inspect-before-revert policy (enforced):** This tool refuses if
    you've edited scratch.c since your last asm inspection.  Call
    ``verify(diff=True)`` (or ``disasm()`` of your own function) FIRST
    so you can judge the change by SHAPE + asm — not just by byte
    count.  AGENTS.md Hard Rule #3: an edit that drops shape is
    PS-faithful even if bytes rose; reverting on bytes alone is
    counter-productive.
    """
    import asyncio
    deps = ctx.deps
    if deps.edits_since_inspection > 0:
        raise ModelRetry(
            f"refused: you've made {deps.edits_since_inspection} edit(s) "
            "since the last asm inspection.  Before reverting, call "
            "verify(diff=True) to see the PS-vs-RC asm diff, or "
            "disasm() on your function.  Judge by SHAPE + asm — the "
            "byte count alone is the wrong oracle (Hard Rule #3)."
        )
    restored = engine_glue.revert_to_best(deps.workspace)
    if not restored:
        raise ModelRetry(
            "no best snapshot yet — call verify() at least once first."
        )
    # After a successful revert, scratch.c == best.  The best state
    # was inspected back when it BECAME the best, so reset the guard.
    deps.mark_asm_inspected()
    deps.event("revert", restored=True)
    vr = await asyncio.to_thread(
        engine_glue.run_verify,
        workspace=deps.workspace, project=deps.project,
        target=deps.target, diff=False,
    )
    return vr


# ── disasm ───────────────────────────────────────────────────────────────


async def disasm(
    ctx: RunContext[AgentDeps],
    function: Optional[str] = None,
    binary: Binary = Binary.WATCOM,
) -> DisasmResult:
    """Disassemble a function from one of the three reference binaries.

    ``binary=Binary.WATCOM`` (default): from PS.EXE — must be in the
    byte-exact pool OR be the function you're working on.
    ``binary=Binary.MSVC``: from CAESAR2.EXE.
    ``binary=Binary.MAC``: PPC asm from the Mac binary.

    Keep the L<N> column — those are the original Watcom -d1 source
    line numbers (Hard Rule #4).
    """
    deps = ctx.deps
    fn = function or deps.function
    proj = deps.project if binary == Binary.WATCOM else (
        deps.project.for_target("msvc")
        if binary == Binary.MSVC and deps.project.active_target != "msvc"
        else deps.project
    )

    # disasm() of the function under test counts as an asm inspection
    # for the revert-guard (Hard Rule #3): the agent has seen the
    # post-edit instructions and can now judge whether to revert.
    if fn == deps.function:
        deps.mark_asm_inspected()

    if binary == Binary.MAC:
        # Mac PPC disasm — defer to `c2 mac-fn` (no python API)
        cp = subprocess.run(
            ["uv", "run", "c2", "mac-fn", fn],
            capture_output=True, text=True, timeout=60,
        )
        if cp.returncode != 0:
            return DisasmResult(
                binary=binary, function=fn,
                error=f"mac-fn failed: {cp.stderr.strip()[:400]}",
            )
        # Parse lines best-effort: "ADDR  bytes  mnemonic  operands"
        rows: list[DisasmRow] = []
        for ln in cp.stdout.splitlines():
            parts = ln.split(None, 3)
            if len(parts) < 3 or not parts[0].startswith("0x"):
                continue
            try:
                off = int(parts[0], 16)
            except ValueError:
                continue
            bytes_hex = parts[1] if len(parts) >= 4 else ""
            mnem = parts[2 if len(parts) >= 4 else 1]
            ops = parts[3] if len(parts) >= 4 else ""
            rows.append(DisasmRow(offset=off, bytes_hex=bytes_hex, mnemonic=mnem, operands=ops))
        # FALL THROUGH: if our parse heuristic produced zero rows, the
        # agent should still see SOMETHING.  Return the raw stdout via
        # ``raw_text`` so they can read it as-is.
        raw_text = cp.stdout if not rows else None
        return DisasmResult(
            binary=binary, function=fn, rows=rows,
            raw_text=_truncate(cp.stdout, 24_000)[0] if not rows else None,
            has_line_numbers=False,    # Mac PPC has no -d1
        )

    # Watcom / MSVC via engine toolchain
    tc = proj.toolchain()
    try:
        info = tc.function_info(fn)
        body = tc.function_bytes(fn)
        fixups = tc.function_fixups(fn)
        lines = tc.line_numbers(fn)
    except KeyError as e:
        return DisasmResult(binary=binary, function=fn, error=str(e))

    insns = tc.disassemble(body, info.address, fixups)
    line_marks = {off: ln for off, ln in lines}
    has_lines = bool(line_marks)

    rows: list[DisasmRow] = []
    last_line: Optional[int] = None
    for insn in insns:
        ln_at = line_marks.get(insn.offset)
        if ln_at is not None:
            last_line = ln_at
        rows.append(DisasmRow(
            offset=insn.offset,
            line=last_line,
            bytes_hex=insn.raw.hex(),
            mnemonic=insn.mnemonic,
            operands=insn.op_str,
        ))
    return DisasmResult(
        binary=binary, function=fn, rows=rows,
        has_line_numbers=has_lines,
    )


# ── decompile (mac / msvc) ───────────────────────────────────────────────


async def decompile(
    ctx: RunContext[AgentDeps],
    function: str,
    binary: Binary,
) -> DecompileResult:
    """Ghidra-decompiled C source for a function from CAESAR2.EXE
    (``binary=Binary.MSVC``) or the Mac PPC binary (``binary=Binary.MAC``).

    Source-SHAPE oracle.  ``Binary.WATCOM`` is NOT supported here — use
    ``fetch`` to read the project's own decomp for already-byte-exact
    Watcom functions.
    """
    if binary == Binary.WATCOM:
        raise ModelRetry(
            "decompile() takes binary=Binary.MSVC or Binary.MAC.  For "
            "Watcom source, use fetch() (the project's own decomp of a "
            "byte-exact function)."
        )
    cmd = "mac-decompile" if binary == Binary.MAC else "win-decompile"
    cp = subprocess.run(
        ["uv", "run", "c2", cmd, function],
        capture_output=True, text=True, timeout=120,
    )
    if cp.returncode != 0:
        return DecompileResult(
            binary=binary, function=function,
            error=f"{cmd} failed: {cp.stderr.strip()[:400]}",
        )
    text, _ = _truncate(cp.stdout, 32_000)
    # Heuristic: first non-comment, non-blank line is usually the signature.
    sig: Optional[str] = None
    for ln in text.splitlines():
        s = ln.strip()
        if not s or s.startswith("/*") or s.startswith("//"):
            continue
        if "(" in s and s.endswith("{"):
            sig = s.rstrip("{").strip()
            break
        if "(" in s and ";" not in s:
            sig = s
            break
    return DecompileResult(
        binary=binary, function=function,
        signature=sig, code=text,
    )


# ── info / nearest / fetch / lookup ──────────────────────────────────────


async def info(
    ctx: RunContext[AgentDeps],
    function: Optional[str] = None,
    siblings_top: int = 8,
) -> FunctionInfo:
    """Structural brief: types, calls, siblings, AND name-pattern relatives.

    Includes two kinds of related functions:

    * **siblings** — structurally similar byte-exact functions, found by
      5-insn asm shingle containment (asm-level twins).
    * **name_relatives** — functions whose name differs by ONE
      template-instantiation token (zoom `_`/`2`/`3`, layer
      `top`/`base`/`roof`, direction `up`/`down`, `with_sides`/`no_sides`,
      …).  Each row reports byte-exact / diffing status from the corpus
      verify cache; a byte-exact relative is the strongest PS-faithful
      template the agent can lift structure from.

    Defaults to the function under test.  For OTHER functions, pass
    ``function=name``.
    """
    import asyncio
    deps = ctx.deps
    fn = function or deps.function

    def _build():
        from c2.decompile._engine.info import info as _info_build
        return _info_build(deps.project, fn, siblings_top=siblings_top)

    raw = await asyncio.to_thread(_build)
    return FunctionInfo(
        name=raw.name,
        address_hex=raw.address_hex,
        size=raw.size,
        source_file=raw.source_file,
        signature=raw.signature,
        prologue_pushes=list(raw.prologue_pushes),
        stack_frame=getattr(raw, "frame_size", 0),
        argc=raw.argc,
        source_line_range=raw.source_line_range,
        calls=[CallInfo(name=c.name, times=c.times) for c in raw.calls],
        types=[TypeInfo(name=t.name, header=t.header, definition=t.definition)
               for t in raw.types],
        siblings=[SiblingInfo(name=s.name, score=s.score) for s in raw.siblings],
        name_relatives=[
            NameRelative(
                name=r.name, pattern=r.pattern, status=r.status,
                byte_diff=r.byte_diff, source_file=r.source_file,
            )
            for r in raw.name_relatives
        ],
        tail_merge_donor=raw.tail_merge_donor,
    )


async def nearest(
    ctx: RunContext[AgentDeps],
    function: Optional[str] = None,
    top: int = 10,
) -> NearestResult:
    """Find byte-exact functions whose asm structurally resembles ``function``.

    Backed by ``c2 sibling`` shingle-hash matching (same engine as
    ``info``'s siblings field, but standalone and with a configurable
    ``top``).  Returns names you can then ``fetch`` / ``disasm`` to study.
    """
    import asyncio
    deps = ctx.deps
    fn = function or deps.function

    def _find():
        from c2.commands.sibling import find_siblings
        return find_siblings(
            fn, filter_status={"exact"}, top_n=top, min_score=0.05,
        )
    try:
        hits = await asyncio.to_thread(_find)
    except Exception as e:
        return NearestResult(query_kind="function", hits=[])
    return NearestResult(
        query_kind="function",
        hits=[NearestHit(name=h.name, score=float(h.score)) for h in hits],
    )


async def fetch(ctx: RunContext[AgentDeps], function: str) -> FetchResult:
    """Return the project's C source for a byte-exact Watcom function.

    Read-only study template — DO NOT paste verbatim into scratch.c.
    """
    import asyncio
    deps = ctx.deps

    def _fetch():
        tc = deps.project.toolchain()
        return tc.existing_source(function)
    try:
        src = await asyncio.to_thread(_fetch)
    except Exception as e:
        return FetchResult(name=function, error=str(e))
    if src is None:
        return FetchResult(
            name=function,
            error=f"no existing source for {function!r} in decomp/src/",
        )
    src_file, body = src
    return FetchResult(name=function, source_file=src_file, code=body)


# ── regtrace ───────────────────────────────────────────────────────────


def _shape_dict_to_model(d: dict | None) -> Optional[ShapeDistance]:
    """Map an engine-style ``shape_distance`` dict to our typed model."""
    if not d:
        return None
    fn_raw = (d.get("fix_next") or "none").lower()
    if fn_raw == "done":
        fn = FixLayer.NONE
    else:
        try:
            fn = FixLayer(fn_raw)
        except ValueError:
            fn = FixLayer.NONE
    isl = d.get("islands")
    return ShapeDistance(
        ir=(int(d.get("ir", 0)), int(d.get("ir_total", 0))),
        width=(int(d.get("width", 0)), int(d.get("width_total", 0))),
        spill=(int(d.get("spill", 0)), int(d.get("spill_total", 0))),
        seat=(int(d.get("seat", 0)), int(d.get("seat_total", 0))),
        fix_next=fn,
        islands=int(isl) if isl is not None else None,
    )


async def regtrace(
    ctx: RunContext[AgentDeps],
    function: Optional[str] = None,
) -> RegtraceResult:
    """Trace the REAL Watcom 10.0a register allocator over the function's TU.

    Run this when ``shape.fix_next == FixLayer.SEAT`` and your
    source-shape edits aren't moving the seat layer — regtrace is the
    ground-truth allocator lens.  Returns:

    * **verdict** — the seat-diff classification
      (``clean`` / ``tie`` / ``not_tie`` / …).
    * **swaps** — each value seated in a different register than PS,
      with its RC reg, PS reg, savings, the equal-savings ``tie`` flag,
      and — when the trace substrate allows — the CERTIFIED
      ``chain_verdict`` (full-chain recomputation, identity
      6,243/6,243): ``masked`` = live-range lever (``chain_mask_rows``
      contributing rows), ``outscored`` = per-instruction-named credit
      lever (``chain_credits``), ``tie-order`` = Rule 115/28a order
      lever, ``vetoed`` / ``not-a-candidate`` = savings / type-class
      levers, ``no-alloc-row`` = rover/scratch seat (use spell/fusion,
      not decl orders).  The chain verdict is authoritative over the
      ``tie`` heuristic when they disagree.
    * **first_divergence** — the earliest byte offset where PS and RC
      disagree on a register seat (with the two asm lines).
    * **shape_distance** — the layered shape distance at trace time.

    The data is the observation; reason about it yourself.  ``tie=True``
    means the swap can in principle be moved by changing what gets
    referenced first / declared first in the source; ``tie=False`` is a
    classification signal that source levers probably won't help.
    """
    deps = ctx.deps
    fn = function or deps.function

    def _run():
        from c2.commands.regtrace import _container_rows, vs_ps_data
        src_file, start, end, rows, _n_funcs, _sortmeta = _container_rows(
            fn, None
        )
        return vs_ps_data(fn, src_file, rows, start, end)

    import asyncio
    try:
        data = await asyncio.to_thread(_run)
    except Exception as e:
        return RegtraceResult(function=fn, error=f"{type(e).__name__}: {e}")

    # Build typed swaps.  The free-text ``lever`` heuristic stays omitted
    # (data-not-conclusions), but the CERTIFIED chain verdict is data:
    # it is a recomputed ground-truth classification, not a suggestion.
    swaps: list[SeatSwap] = []
    for sw in data.get("swaps", []) or []:
        ev = sw.get("chain_evidence") or {}
        swaps.append(SeatSwap(
            value=str(sw.get("value") or "(temp)"),
            rc=str(sw.get("rc") or ""),
            ps=str(sw.get("ps") or ""),
            savings=int(sw.get("savings") or 0),
            tie=bool(sw.get("tie")),
            chain_verdict=sw.get("chain_verdict"),
            chain_mask_rows=int(ev.get("mask_rows") or 0),
            chain_credits=int(ev.get("winner_credits") or 0),
        ))

    first_div: Optional[FirstDivergence] = None
    fd = data.get("first_divergence")
    if fd:
        first_div = FirstDivergence(
            offset=int(fd.get("off", 0) or 0),
            line=fd.get("ln"),
            rc=str(fd.get("rc") or ""),
            ps=str(fd.get("ps") or ""),
            ps_asm=str(fd.get("ps_asm") or ""),
            rc_asm=str(fd.get("rc_asm") or ""),
        )

    return RegtraceResult(
        function=fn,
        verdict=str(data.get("verdict") or ""),
        coverage=int(data.get("coverage") or 0),
        swaps=swaps,
        first_divergence=first_div,
        shape_distance=_shape_dict_to_model(data.get("shape_distance")),
    )


# ── grep / search ───────────────────────────────────────────────────────


async def search(
    ctx: RunContext[AgentDeps],
    pattern: str,
    path: str = ".",
    max_results: int = 50,
    context: int = 0,
    case_sensitive: bool = True,
) -> SearchResult:
    """Search files in the sandbox for ``pattern`` (regex).

    Scope:
      * ``path="."`` (default) — search the whole sandbox: ``scratch.c``
        + ``info.md`` + the ``open-watcom/`` symlink (so you can grep
        the Watcom codegen-source oracle for algorithm questions).
      * ``path="open-watcom/bld/cg/intel"`` — narrow to a subtree.
      * ``path="scratch.c"`` — search just one file.

    Backed by ripgrep.  Output capped at ``max_results`` matches
    (default 50) so deeply-nested searches don't drown the agent.
    ``context`` adds N lines of context above + below each match.
    """
    import shutil
    if shutil.which("rg") is None:
        raise ModelRetry("ripgrep (rg) not available on this host")
    deps = ctx.deps
    # Resolve + sandbox-check the path.
    if path in (".", "", "./"):
        scope = deps.workspace.work_dir
    else:
        scope = _safe_resolve(deps.workspace, path)
    args = [
        "rg", "--no-heading", "--line-number", "--color=never",
        # Force ripgrep to always prefix matches with the path (it omits
        # it by default when searching a single file, which breaks our
        # "PATH:LINE:TEXT" line parser below).
        "--with-filename",
        "--max-count", str(max_results),
    ]
    if context > 0:
        args += ["--context", str(context)]
    if not case_sensitive:
        args.append("--ignore-case")
    args += ["--", pattern, str(scope)]
    # IMPORTANT: capture bytes, not text.  Ripgrep can stream lines from
    # files containing non-UTF8 bytes (binaries in vendor/, codepage-1252
    # docs, etc.) which would raise ``UnicodeDecodeError`` if we let
    # subprocess decode under ``text=True``.  Decode here with
    # ``errors="replace"`` so a stray byte never crashes the tool.
    cp = subprocess.run(args, capture_output=True, timeout=30)
    stdout = cp.stdout.decode("utf-8", errors="replace")
    stderr = cp.stderr.decode("utf-8", errors="replace")
    # rg exit codes: 0 = matches, 1 = no matches, 2 = error.
    if cp.returncode == 2:
        return SearchResult(
            pattern=pattern, scope=path,
            hits=[], truncated=False,
            error=stderr.strip()[-400:],
        )
    # For paths that resolved THROUGH the open-watcom symlink, ripgrep
    # follows the symlink target and emits the absolute vendor path; we
    # map those back to ``open-watcom/...`` so the agent only ever sees
    # sandbox-relative paths.
    ow_real = (deps.workspace.work_dir / "open-watcom").resolve()

    def _rel(p_str: str) -> str:
        p_path = Path(p_str)
        try:
            return str(p_path.relative_to(deps.workspace.work_dir))
        except ValueError:
            pass
        try:
            return str(Path("open-watcom") / p_path.relative_to(ow_real))
        except ValueError:
            pass
        return p_str

    hits: list[SearchHit] = []
    for ln in stdout.splitlines():
        # rg line format: "PATH:LINE:TEXT" (or PATH-LINE-TEXT for context)
        # Split into 3 fields max so colons inside the text survive.
        for sep in (":", "-"):
            parts = ln.split(sep, 2)
            if len(parts) == 3 and parts[1].isdigit():
                p, line_s, body = parts
                try:
                    line_n = int(line_s)
                except ValueError:
                    continue
                hits.append(SearchHit(file=_rel(p), line=line_n, text=body))
                break
        if len(hits) >= max_results:
            break
    truncated = len(hits) >= max_results
    return SearchResult(
        pattern=pattern, scope=path,
        hits=hits, truncated=truncated,
    )


# ── lookup ─────────────────────────────────────────────────────────────────


async def lookup(ctx: RunContext[AgentDeps], query: str) -> LookupResult:
    """Look up a symbol by name, hex address, glob, or substring.

    Wraps ``c2 sym`` (the symbol-table inspector).
    """
    cp = subprocess.run(
        ["uv", "run", "c2", "sym", query, "--json"],
        capture_output=True, text=True, timeout=30,
    )
    hits: list[LookupHit] = []
    if cp.returncode == 0 and cp.stdout.strip():
        try:
            data = json.loads(cp.stdout)
            for h in (data if isinstance(data, list) else data.get("hits", [])):
                hits.append(LookupHit(
                    name=h.get("name", "?"),
                    address_hex=h.get("address_hex") or h.get("address", "?"),
                    kind=h.get("kind", "function"),
                    source_file=h.get("source_file"),
                ))
        except json.JSONDecodeError:
            pass
    return LookupResult(query=query, hits=hits)


# ── census ─────────────────────────────────────────────────────────────


async def census(ctx: RunContext[AgentDeps]) -> CensusResult:
    """Named-local census: your scratch.c (MSVC /Od) vs CAESAR2.EXE.

    MSVC /Od gives EVERY named source local a distinct ``[ebp-N]`` frame
    slot, so CAESAR2.EXE's slot set witnesses the ORIGINAL source's
    local-variable set — the input that decides Watcom conflict
    membership, savings rank, and the spill boundary.  Run this:

    * when ``shape.fix_next`` is ``SPILL`` (a different live-value set
      almost always means a missing/invented named local), or
    * before a structural rewrite on a big cascade-head function, or
    * whenever you suspect an invented temp (§13: a single-assign local
      mirroring a global/field read that PS inlined).

    Read the result:

    * ``delta > 0`` — the original declared MORE locals.  Find the
      unmatched slot in ``slots_theirs`` (width + n_uses + first_use
      profile identifies the expression) and NAME that value in
      scratch.c.  Worked: evolve_water_table's ``kind - 0xda`` int temp
      took shape ir 7/29 → 5/29 after 24/24 decl permutations had
      failed — permutations can never change the temp SET.
    * ``delta < 0`` — your source INVENTED locals: inline them.
    * ``delta == 0`` — the local set matches; check ``widths`` for type
      drift (b vs d ⇒ char vs int).

    TRUST GATE: act only when ``gate == "usable"``.  The win mapping is
    fuzzy and the Windows source is a later cut (port drift is real —
    e.g. added ``x = 0`` initialisers).  Adjudicate every census delta
    against the PS asm / -d1 line marks (``verify(diff=True)``,
    ``disasm()``) before editing; the census is a candidate generator,
    not ground truth.
    """
    import asyncio

    deps = ctx.deps
    deps.event("census_start")
    try:
        data = await asyncio.to_thread(
            engine_glue.run_census,
            workspace=deps.workspace, project=deps.project,
        )
    except Exception as e:
        return CensusResult(function=deps.function, ok=False,
                            note=f"{type(e).__name__}: {e}")
    if not data.get("ok"):
        return CensusResult(function=deps.function, ok=False,
                            note=str(data.get("note") or "census failed"))
    res = CensusResult(
        function=deps.function, ok=True,
        quality=float(data["quality"]), gate=str(data["gate"]),
        frame_ours=data.get("frame_ours"), frame_theirs=data.get("frame_theirs"),
        slots_ours=[SlotInfo(**s) for s in data["slots_ours"]],
        slots_theirs=[SlotInfo(**s) for s in data["slots_theirs"]],
        delta=int(data["delta"]),
    )
    deps.event("census_done", quality=res.quality, gate=res.gate,
               delta=res.delta)
    return res


# ── lines (the -d1 ledger) ─────────────────────────────────────────────


async def lines(ctx: RunContext[AgentDeps], all: bool = False) -> LinesResult:
    """The per-line ``-d1`` ledger: PS's line marks vs your scratch.c's.

    THE tool for working a BIG function statement-by-statement instead
    of reading the whole diff.  PS.EXE carries one debug mark per
    source LINE; your compile gets the same.  Each side is segmented
    by its OWN marks and the REGISTER-BLIND canonical instruction
    streams are aligned — attribution stays EXACT no matter how large
    the function or how far the byte diff drifts.  Per PS line run:

    * ``ps_insns`` vs ``rc_insns`` — does your statement emit too many
      / too few instructions?
    * ``rc_lines`` — the ABSOLUTE scratch.c lines whose instructions
      align to this PS line (your edit target).  A ``ps_only`` row =
      PS emits a form you LACK entirely; ``rc_only`` = your source
      emits instructions PS lacks (remove/inline them).
    * ``tags`` — the divergence FAMILY: ``width``/``zext-idiom``
      (char-vs-int local — Rules 49/151), ``signedness`` (jl↔jb =
      signed vs unsigned local), ``loop-form`` (rotated for vs
      head-tested while — Rule 134), ``slot`` (spill-slot layout —
      usually downstream, work LAST), ``frame`` (local set differs),
      ``const``, ``ops`` (read the PS side; that IS the target shape).
    * ``ps_only_ops`` / ``rc_only_ops`` — binir constructs on the
      divergent part only.
    * ``order_flip`` — the statements are in a different ORDER than
      the original source.

    Recommended loop for big functions: ``lines()`` → take the FIRST
    row whose verdict is ``form`` / ``ps_only`` / ``rc_only`` (or
    ``order_flip``) → read that statement (``read(scratch.c,
    offset=rc_lines[0]-3, limit=8)``) + the PS asm at that L+N
    (``verify(diff=True)`` window or ``disasm()``) → make ONE
    statement-level edit → ``verify()`` → repeat.  ``slot``/``frame``
    tagged rows are spill territory — work them LAST (census/regtrace).
    ``pack`` verdicts are byte-neutral line-packing witness (the
    original wrote those statements on one physical line) — never
    chase them for bytes.  ZERO divergent rows on a still-diffing
    function = the whole diff is register seats/encoding: STOP
    restructuring; go to ``regtrace()``.

    By default only divergent rows are returned; ``all=True`` includes
    the matching rows too.
    """
    import asyncio

    deps = ctx.deps
    deps.event("lines_start")
    try:
        data = await asyncio.to_thread(
            engine_glue.run_lines,
            workspace=deps.workspace, project=deps.project,
        )
    except Exception as e:
        return LinesResult(function=deps.function,
                           error=f"{type(e).__name__}: {e}")
    if isinstance(data, str):
        return LinesResult(function=deps.function, error=data)
    rows = [LineLedgerRow(**r) for r in data]
    divergent = [r for r in rows if r.verdict != "match"]
    out_rows = rows if all else divergent
    note = ""
    if len(out_rows) > 80:
        note = (f"ledger truncated to the first 80 of {len(out_rows)} rows; "
                "work top-down and re-run after edits")
        out_rows = out_rows[:80]
    res = LinesResult(function=deps.function, total=len(rows),
                      divergent=len(divergent), rows=out_rows, note=note)
    deps.event("lines_done", total=res.total, divergent=res.divergent)
    return res


# ── trace-level spelling tools (spell / fusion / walk_order / suggest) ────
#
# All four run on the sandbox's SELF-CONTAINED scratch.c (types/externs
# inlined), traced with the instrumented 10.0a compiler in a transient
# container (~15 s per trace).  The analyses are the same engine the
# project-level `c2 spell` uses (c2/regalloc/lwalk.py); background:
# watcom10.0a docs/rover-model.md + docs/block-birth-dictionary.md.


def _trace_scratch_routine(fn: str, text: str) -> dict:
    """Trace a self-contained TU text and return the routine for ``fn``.

    Routine pick: max fr-line hits inside the function's line span in
    ``text`` (tree-sitter span when available, else the whole file --
    scratch.c usually holds one real function plus stubs, and stubs
    have no fr records)."""
    from c2 import regalloc
    from c2.regalloc import trace as rtrace

    td = regalloc.trace_compile({"SCRATCH.C": text}, main="SCRATCH.C")
    parsed = rtrace.parse(td["stdout"])
    start, end = 1, len(text.splitlines()) + 1
    try:
        from c2.forge import cspan
        fs = cspan.fnspan(text, fn)
        if fs is not None:
            start = text.count("\n", 0, fs.fn_node.start_byte) + 1
            end = text.count("\n", 0, fs.fn_node.end_byte) + 1
    except Exception:
        pass
    best, best_hits = None, -1
    for ro in parsed["routines"]:
        frs = ro.get("fr", [])
        hits = sum(1 for x in frs
                   if x.get("line") and start <= x["line"] <= end)
        score = hits * 1000 + len(frs) + len(ro.get("lw", []))
        if score > best_hits:
            best_hits, best = score, ro
    if best is None:
        raise RuntimeError(f"{fn}: no traced routine in scratch.c")
    return best


async def spell(ctx: RunContext[AgentDeps]) -> SpellResult:
    """Trace-screen your CURRENT scratch.c against the BEST snapshot:
    at which compiler stage does your edit's distinction DIE?

    Run this BEFORE ``verify`` when you are probing a SPELLING (same
    semantics, different form: statement order, packing, temp
    naming/inlining, guard shape).  The staged ladder — tree → block
    births → IL births → LdStAlloc walk — tells you whether the edit
    even reaches the back end:

    * ``INERT@TREE`` — canonicalized away by the parser; the whole
      spelling family is provably unreachable.  Do NOT verify; try a
      different IDEA, not a sibling spelling.
    * ``INERT@BURN`` — read ``il_births``: identical = canonicalized AT
      IL emission (deepest inert, stop the family); diverged (with
      ``delta_lines``) = a later pass re-converged it — siblings at
      exactly those lines may survive.
    * ``LIVE…`` — the walk differs; NOW spend the byte ``verify``.

    Requires a best snapshot (verify at least once first).  One
    container trace (~15 s) — far cheaper than reasoning backwards
    from an unchanged byte count.
    """
    deps = ctx.deps
    best = deps.workspace.read_best()
    if best is None:
        return SpellResult(function=deps.function,
                           error="no best snapshot yet -- run verify once "
                                 "first (spell compares scratch.c against "
                                 "best/scratch.c)")
    base_text = (deps.workspace.best_dir / "scratch.c").read_text(
        errors="replace")
    cand_text = deps.workspace.scratch_path.read_text(errors="replace")
    if base_text == cand_text:
        return SpellResult(function=deps.function,
                           error="scratch.c is byte-identical to the best "
                                 "snapshot -- edit first, then spell")

    def _run():
        from c2.regalloc import lwalk
        base = _trace_scratch_routine(deps.function, base_text)
        cand = _trace_scratch_routine(deps.function, cand_text)
        v = lwalk.spelling_compare(base, cand)
        bc = lwalk.birth_compare(base, cand)
        ib = lwalk.il_birth_compare(base, cand)
        return v, bc, ib

    import asyncio
    try:
        v, bc, ib = await asyncio.to_thread(_run)
    except Exception as e:
        return SpellResult(function=deps.function,
                           error=f"{type(e).__name__}: {e}")
    res = SpellResult(
        function=deps.function,
        verdict=v.headline(),
        adv_base=dict(v.adv_base),
        adv_cand=dict(v.adv_cand),
        block_births=BirthDiff(
            verdict=bc["verdict"].lower(),
            n_base=len(bc["base_sig"]), n_cand=len(bc["cand_sig"]),
            first_delta=(bc["delta"][0] if bc["delta"] else None)),
        il_births=BirthDiff(
            verdict=ib["verdict"].lower(),
            n_base=ib["n_base"], n_cand=ib["n_cand"],
            delta_lines=ib["delta_lines"][:12]),
    )
    deps.event("spell_done", verdict=res.verdict)
    return res


async def fusion(ctx: RunContext[AgentDeps]) -> FusionResult:
    """The rover fuse map + compress pair-scan context for your CURRENT
    scratch.c.

    Every RISCified rover op resolves to ``fused`` or a NAMED
    rejection; the ``attempts`` list shows what the ONE compress pass
    (PostOptimize END) actually saw per attempt.  Key read:
    ``prevkind``/``nextkind`` 3 = a recognized MOV half sits adjacent
    in CHAIN order; ``0x1NN`` = ins with opcode NN between the halves
    — ``0x14b`` = a BLOCK HEADER (chain-separated pair, the byte-level
    "hoist" fingerprint: the final layout can still be byte-adjacent).
    Use when the diff shows a PS-only reg-copy / a hoisted const store
    that your compile fuses away (or vice versa).
    """
    deps = ctx.deps
    text = deps.workspace.scratch_path.read_text(errors="replace")

    def _run():
        from c2.regalloc import lwalk
        ro = _trace_scratch_routine(deps.function, text)
        return lwalk.fusion_map(ro), lwalk.compress_context(ro), lwalk
    import asyncio
    try:
        rows, ctx_rows, lwalk = await asyncio.to_thread(_run)
    except Exception as e:
        return FusionResult(function=deps.function,
                            error=f"{type(e).__name__}: {e}")
    return FusionResult(
        function=deps.function,
        rows=[FusionRow(fr_idx=r["fr_idx"], line=r.get("line"),
                        state=r["state"],
                        meaning=lwalk.LCX_MEANING.get(r["state"], ""))
              for r in rows],
        attempts=[CompressAttempt(
            ins=c["ins"], blk=c.get("blk"), opcode=c["opcode"],
            prevkind=c["prevkind"], nextkind=c["nextkind"],
            outcome=c["outcome"]) for c in ctx_rows],
    )


async def walk_order(ctx: RunContext[AgentDeps]) -> WalkOrderResult:
    """The walk-vs-layout block map (with birth ordinals) for your
    CURRENT scratch.c.

    ``moved`` rows = the rover walks that block far from its source-
    line position; ``reverse_arm=True`` = birth ordinals run OUT of
    walk order (the optimizer restructured a source-ordered chain —
    else-if arms walk in REVERSE source order).  Before designing a
    structural variant, consult the construct → block-birth dictionary
    (``lookup("block-birth")`` or watcom10.0a
    docs/block-birth-dictionary.md): labels add a walk-invisible birth;
    ``&&``/``||``/nested-if are birth-identical; loop forms have
    distinct signatures.
    """
    deps = ctx.deps
    text = deps.workspace.scratch_path.read_text(errors="replace")

    def _run():
        from c2.regalloc import lwalk
        ro = _trace_scratch_routine(deps.function, text)
        return lwalk.walk_vs_layout(ro)
    import asyncio
    try:
        rows = await asyncio.to_thread(_run)
    except Exception as e:
        return WalkOrderResult(function=deps.function,
                               error=f"{type(e).__name__}: {e}")
    births = [r.get("birth") for r in rows if isinstance(r.get("birth"), int)]
    return WalkOrderResult(
        function=deps.function,
        rows=[WalkOrderRow(
            walk=r["walk"],
            lines=(f"L{r['lines'][0]}" if r["lines"][0] == r["lines"][1]
                   else f"L{r['lines'][0]}..L{r['lines'][1]}"),
            layout=r["layout"],
            birth=(str(r["birth"]) if r.get("birth") is not None else None),
            moved=r["moved"]) for r in rows],
        reverse_arm=bool(births and births != sorted(births)),
        opt_born=sum(1 for r in rows if r.get("birth") == "opt"),
    )


async def suggest(
    ctx: RunContext[AgentDeps],
    lines: Optional[str] = None,
    max_candidates: int = 6,
) -> SuggestResult:
    """GENERATE fold/unfold candidate spellings from your CURRENT
    scratch.c and trace-screen each one.

    Fold (de-invent: delete a single-write local, read its RHS inline —
    the +1 rover-advance direction) and unfold (cache-field: name a
    repeated field/array read — the −1 direction), generated by
    hazard-checked span machinery (single write, side-effect-free RHS,
    no intervening call/store), so every candidate is semantics-
    preserving by construction.  Candidates are written into the
    sandbox at ``cands/NN-<tag>.c`` — apply one with
    ``read(path)`` + ``write("scratch.c", …)`` (or copy the edit by
    hand), then ``verify``.

    ``lines`` (comma-separated source lines, e.g. from a rover census
    or your own diff read) restricts to candidates touching those
    lines.  Only ``LIVE…`` verdicts are worth a byte verify; INERT
    candidates are documented dead ends (do not re-try their family).
    Each screen costs a container trace (~15 s); ``max_candidates``
    caps the run.
    """
    deps = ctx.deps
    text = deps.workspace.scratch_path.read_text(errors="replace")

    def _run():
        import bisect as _bisect
        from c2.regalloc import lwalk
        from c2.forge.presets import de_invent_candidates, preset_cache_field

        class _Shim:
            def __init__(self):
                self.text = text
                self.function = deps.function
                self.collected = []

            def candidate(self, tag, *edits):
                self.collected.append((tag, edits))

        shim = _Shim()
        de_invent_candidates(shim)
        preset_cache_field(shim)
        if not shim.collected:
            return None, []

        want = ({int(x) for x in lines.replace(" ", "").split(",") if x}
                if lines else None)
        line_starts = [0]
        for i, ch in enumerate(text):
            if ch == "\n":
                line_starts.append(i + 1)

        def lineno(off):
            return _bisect.bisect_right(line_starts, off)

        cands_dir = deps.workspace.work_dir / "cands"
        cands_dir.mkdir(exist_ok=True)
        base_ro = _trace_scratch_routine(deps.function, text)
        out = []
        for idx, (tag, edits) in enumerate(shim.collected):
            touched = sorted({lineno(e.start) for e in edits})
            if want and not (want & set(touched)):
                continue
            if len(out) >= max_candidates:
                break
            buf = text
            for e in sorted(edits, key=lambda e: (-e.start, -e.end)):
                buf = buf[:e.start] + e.replacement + buf[e.end:]
            safe = tag.replace("(", "-").replace(")", "").replace(",", "_")
            path = cands_dir / f"{idx:02d}-{safe}.c"
            path.write_text(buf)
            try:
                cand_ro = _trace_scratch_routine(deps.function, buf)
                verdict = lwalk.spelling_compare(base_ro, cand_ro).headline()
            except Exception as exc:
                verdict = f"ERROR ({exc})"
            out.append((tag, touched, f"cands/{path.name}", verdict))
        return shim.collected, out

    import asyncio
    try:
        collected, out = await asyncio.to_thread(_run)
    except Exception as e:
        return SuggestResult(function=deps.function,
                             error=f"{type(e).__name__}: {e}")
    if collected is None:
        return SuggestResult(
            function=deps.function,
            note="no safe fold/unfold candidates (the hazard analysis "
                 "rejected everything -- the residue is likely walk-order "
                 "or sub-source; try walk_order()/fusion())")
    res = SuggestResult(
        function=deps.function,
        candidates=[SuggestCandidate(tag=t, lines=l, path=p, verdict=v)
                    for t, l, p, v in out],
        note=(f"{len(collected)} generated, {len(out)} screened"
              + (f" (restricted to lines {lines})" if lines else "")))
    deps.event("suggest_done", n=len(out))
    return res

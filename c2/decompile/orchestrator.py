"""Asyncio-based parallel decompile orchestrator.

Drives N pydantic-ai agents at once (one per function), each in its own
sandboxed :class:`Workspace`.  Streams live progress through
:class:`LiveReporter`.

The orchestrator:

  * Resolves selectors → target list.
  * For each target, allocates a fresh ``Workspace`` under
    ``runs_root`` (default ``.c2-runs/`` in the repo).
  * Spawns up to ``batch`` agents concurrently via an
    :class:`asyncio.Semaphore`.
  * Subscribes to pydantic-ai's stream events for each agent and
    forwards them to the reporter.
  * Returns the list of :class:`FinishReport`s when every agent has
    terminated.

Cancellation: SIGINT interrupts every in-flight agent; partial
``transcript.jsonl`` / ``history.jsonl`` are preserved so the run can
be inspected.
"""

from __future__ import annotations

import asyncio
import json
import random
import time
import traceback
from pathlib import Path
from typing import Optional

from pydantic_ai import (
    Agent,
    AgentRunResultEvent,
    AgentStreamEvent,
    FinalResultEvent,
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    PartStartEvent,
    UsageLimits,
)

from c2.decompile import engine_glue
from c2.decompile.agent import DEFAULT_MODEL_ID, build_agent
from c2.decompile.models import (
    AgentFinishReport,
    AgentStatus,
    FinishReport,
    Target,
    Verdict,
    VerifyResult,
)
from c2.decompile.reporter import LiveReporter
from c2.decompile.selectors import Resolution
from c2.decompile.tools import AgentDeps
from c2.decompile.tracing import (
    agent_span,
    configure_tracing,
    flush_tracing,
    is_configured as tracing_is_configured,
    orchestrator_span,
)
from c2.decompile.workspace import DEFAULT_RUNS_ROOT, Workspace


# ── orchestrator config ──────────────────────────────────────────────────


class OrchestratorConfig:
    """Plain config bag for an orchestrator run."""

    def __init__(
        self,
        *,
        runs_root: Path = DEFAULT_RUNS_ROOT,
        batch: int = 4,
        target: Target = Target.WATCOM,
        model_id: str = DEFAULT_MODEL_ID,
        max_turns: int = 200,
        max_tokens: Optional[int] = None,
        thinking: Optional[str] = None,
        time_budget_s: Optional[float] = None,
        apply_byte_exact: bool = True,
        count: int = 1,
        jsonl_output: bool = False,
        project_root: Path = Path("."),
        model_override: object = None,
        trace: bool = False,
        trace_file: Optional[Path] = None,
        otlp_endpoint: Optional[str] = None,
        extra_prompt: Optional[str] = None,
    ):
        self.runs_root = runs_root.resolve()
        self.batch = batch
        self.target = target
        self.model_id = model_id
        self.max_turns = max_turns
        self.max_tokens = max_tokens
        self.thinking = thinking
        self.time_budget_s = time_budget_s
        self.apply_byte_exact = apply_byte_exact
        # ``count`` > 1 races N replicas on EACH target function.  Per-
        # agent auto-apply is suppressed for a race (concurrent writers
        # to one TU is the parallel-clobber hazard); the single best
        # replica is applied once, after the race, in run_orchestrator.
        self.count = max(1, int(count))
        self.jsonl_output = jsonl_output
        self.project_root = project_root.resolve()
        self.model_override = model_override
        self.trace = trace
        self.trace_file = trace_file
        self.otlp_endpoint = otlp_endpoint
        self.extra_prompt = extra_prompt


# ── transient API-error retry ─────────────────────────────────

#: HTTP statuses / error signatures that are transient at the API/proxy
#: level and worth retrying (overloaded, rate-limited, gateway/5xx,
#: timeouts).  A UsageLimitExceeded (agent hit --max-turns) is NOT here
#: -- that is a real stop, not a transient failure.
_TRANSIENT_STATUS = {408, 409, 425, 429, 500, 502, 503, 504, 522, 524, 529}
_TRANSIENT_SIGNS = (
    "overloaded", "rate limit", "rate_limit", "try again", "timeout",
    "timed out", "temporarily unavailable", "service unavailable",
    "bad gateway", "gateway timeout", "connection", "econnreset",
    "429", "500", "502", "503", "504", "529",
)


def _is_transient_api_error(exc: BaseException) -> bool:
    """True when ``exc`` is a transient model/proxy failure worth
    retrying (vs a real stop like UsageLimitExceeded or a build error)."""
    name = type(exc).__name__
    if name in ("UsageLimitExceeded", "KeyboardInterrupt", "CancelledError"):
        return False
    sc = getattr(exc, "status_code", None) or getattr(exc, "status", None)
    if isinstance(sc, int) and sc in _TRANSIENT_STATUS:
        return True
    # ModelAPIError / ModelHTTPError carry the provider error body in str()
    if name in ("ModelAPIError", "ModelHTTPError", "APIError",
                "APIStatusError", "APIConnectionError", "APITimeoutError",
                "InternalServerError", "RateLimitError", "OverloadedError"):
        return True
    msg = str(exc).lower()
    return any(s in msg for s in _TRANSIENT_SIGNS)


# ── per-agent run loop ───────────────────────────────────────────────────


async def _run_one_agent(
    fn: str,
    *,
    cfg: OrchestratorConfig,
    reporter: LiveReporter,
    project,
) -> FinishReport:
    """Run one agent end-to-end against ``fn``.

    ``fn`` is the reporter/workspace LABEL, which for a ``--count N``
    race carries a ``#NN`` replica suffix (e.g. ``build_city_item#03``).
    The REAL function the agent works on is the label with that suffix
    stripped -- used for compose, deps, and the FinishReport identity so
    disasm/verify/apply all target the true function.

    Returns the FinishReport.  Exceptions are caught and converted into
    a ``FAILED`` event + a synthetic FinishReport carrying the error.
    """
    real_fn = fn.split("#", 1)[0]
    reporter.register(fn)
    ws: Optional[Workspace] = None
    with agent_span(function=fn, target=cfg.target.value):
     try:
        # Allocate workspace AND compose it BEFORE the agent runs — so
        # the agent's first turn can be productive work (verify / read
        # / edit) instead of mechanical "call start() to bootstrap".
        # We embed the function brief in the initial user message,
        # giving the model the function's identity (name, address,
        # cflags, signature, tail-merge donor) and the rendered
        # info.md (types + name-pattern relatives) directly.
        reporter.event(fn, "status", {"status": AgentStatus.COMPOSING.value})
        ws = Workspace.create(runs_root=cfg.runs_root, function=fn)
        from c2.decompile import engine_glue
        meta = engine_glue.compose_workspace(
            workspace=ws, project=project,
            function=real_fn, target=cfg.target,
        )

        agent: Agent[AgentDeps, FinishReport] = build_agent(
            target=cfg.target,
            model_id=cfg.model_id,
            max_tokens=cfg.max_tokens,
            thinking=cfg.thinking,
            model_override=cfg.model_override,
            extra_prompt=cfg.extra_prompt,
        )

        # Wire deps; the closure into reporter is the live status feed.
        def on_event(etype: str, payload: dict) -> None:
            reporter.event(fn, etype, payload)

        deps = AgentDeps(
            workspace=ws, project=project,
            target=cfg.target, function=real_fn,
            on_event=on_event,
        )

        reporter.event(fn, "status", {"status": AgentStatus.RUNNING.value})
        user_prompt = _build_function_brief(meta=meta, ws=ws)

        # Stream events via run_stream_events so we get tool calls AND
        # the final AgentRunResultEvent in one pipe.
        agent_report: Optional[AgentFinishReport] = None
        usage_limits = UsageLimits(request_limit=cfg.max_turns)
        # Retry transient API/proxy failures (overloaded / 429 / 5xx /
        # timeouts) instead of failing the agent outright.  Most such
        # failures hit the FIRST request (proxy overload when a whole
        # batch starts at once), so a re-run is clean; a later failure
        # re-runs on the current workspace (revert_to_best preserves the
        # best snapshot).  UsageLimitExceeded is NOT retried.
        _MAX_API_ATTEMPTS = 6
        for _api_attempt in range(1, _MAX_API_ATTEMPTS + 1):
            try:
                async with agent.run_stream_events(
                    user_prompt, deps=deps, usage_limits=usage_limits,
                ) as events:
                    time_limit_task: Optional[asyncio.Task] = None
                    if cfg.time_budget_s is not None:
                        async def _budget_kill():
                            await asyncio.sleep(cfg.time_budget_s)
                        time_limit_task = asyncio.create_task(_budget_kill())

                    async for ev in events:
                        _record_stream_event(ev, fn, reporter, ws)
                        if isinstance(ev, AgentRunResultEvent):
                            agent_report = ev.result.output
                            break
                        if time_limit_task is not None and time_limit_task.done():
                            reporter.event(fn, "fail", {"error": "time budget exceeded"})
                            break

                    if time_limit_task is not None and not time_limit_task.done():
                        time_limit_task.cancel()
                break                       # completed (result / budget / usage-limit)
            except Exception as _api_exc:    # noqa: BLE001
                if (_is_transient_api_error(_api_exc)
                        and _api_attempt < _MAX_API_ATTEMPTS):
                    _delay = min(45.0, 1.5 * (2 ** _api_attempt)) \
                        + random.uniform(0, 1.5)
                    reporter.event(fn, "status", {
                        "status": f"api-retry {_api_attempt}/"
                                  f"{_MAX_API_ATTEMPTS - 1} in {_delay:.0f}s "
                                  f"({type(_api_exc).__name__})"})
                    await asyncio.sleep(_delay)
                    continue
                raise

        if agent_report is None:
            # Time-out / interrupted before the agent emitted any output.
            final_report = _synthesise_finish_report(
                fn=real_fn, target=cfg.target, ws=ws,
                verdict=Verdict.BUILD_BROKEN,
                reason="agent terminated before producing a FinishReport",
            )
        else:
            # Merge the minimal agent output with workspace-observed truth.
            final_report = _merge_finish_report(
                agent_report=agent_report, fn=real_fn, target=cfg.target, ws=ws,
            )
        final_report.run_dir = str(ws.run_dir)

        final_byte_diff = final_report.final_verify.byte_diff if final_report.final_verify else 0
        final_exact = final_report.final_verify.exact if final_report.final_verify else False
        reporter.event(fn, "finish", {
            "verdict": final_report.verdict.value,
            "byte_diff": final_byte_diff,
            "exact": final_exact,
        })
        _postprocess(final_report, ws=ws, cfg=cfg, project=project)
        return final_report

     except Exception as e:
        tb = traceback.format_exc()
        reporter.event(fn, "fail", {"error": f"{type(e).__name__}: {e}", "traceback": tb})
        rep = _synthesise_finish_report(
            fn=real_fn, target=cfg.target, ws=ws,
            verdict=Verdict.BUILD_BROKEN,
            reason=f"{type(e).__name__}: {e}",
        )
        if ws is not None:
            rep.run_dir = str(ws.run_dir)
        return rep
     finally:
        # Best-effort: tear down the per-agent warm container if the
        # toolchain has one (Watcom).  Failure here is non-fatal.
        try:
            if ws is not None:
                tc = project.toolchain()
                if hasattr(tc, "stop_warm_container"):
                    tc.stop_warm_container(ws.work_dir)
        except Exception:
            pass


def _record_stream_event(
    ev: AgentStreamEvent | AgentRunResultEvent,
    fn: str,
    reporter: LiveReporter,
    ws: Optional[Workspace],
) -> None:
    """Translate one pydantic-ai stream event into a reporter event.

    Turn counting: ``PartStartEvent(index=0)`` fires exactly once at
    the start of every NEW model response (text part OR tool-call
    part), so we use it as the canonical turn boundary.  Subsequent
    parts of the same response have ``index > 0``.
    """
    if isinstance(ev, PartStartEvent):
        if ev.index == 0:
            reporter.event(fn, "model_turn", {})
            if ws is not None:
                ws.append_transcript({"kind": "model_turn_start"})
    elif isinstance(ev, FunctionToolCallEvent):
        # Args travel verbatim to the reporter so the live stream shows
        # what the agent actually called.  The reporter does the
        # short-rendering (truncating big text blobs to byte counts).
        args = ev.part.args
        if isinstance(args, str):
            # Some model providers emit tool args as a JSON string;
            # decode best-effort so the reporter can introspect keys.
            try:
                import json as _json
                args = _json.loads(args)
            except Exception:
                args = {"raw": args}
        reporter.event(fn, "tool_call", {
            "tool": ev.part.tool_name,
            "args": args or {},
        })
        if ws is not None:
            ws.append_transcript({
                "kind": "tool_call",
                "tool": ev.part.tool_name,
                "args": ev.part.args,
            })
    elif isinstance(ev, FunctionToolResultEvent):
        if ws is not None:
            # Don't dump huge tool returns verbatim — keep the type and a
            # small head for forensics.
            content = ev.part.content
            if hasattr(content, "model_dump_json"):
                ser = content.model_dump_json()
            else:
                ser = str(content)
            ws.append_transcript({
                "kind": "tool_result",
                "tool_call_id": ev.tool_call_id,
                "content_head": ser[:1000],
            })
    elif isinstance(ev, FinalResultEvent):
        reporter.event(fn, "status", {"status": AgentStatus.FINISHING.value})


def _ws_truth_verify(target: Target, ws: Optional[Workspace]) -> Optional[VerifyResult]:
    """Construct a VerifyResult mirroring the workspace's best snapshot."""
    if ws is None:
        return None
    best = ws.read_best()
    if best is None:
        return None
    return VerifyResult(
        target=target,
        build_ok=True,
        byte_diff=best.byte_diff,
        exact=(best.byte_diff == 0),
        shape=best.shape,
        best_so_far=best,
    )


def _build_function_brief(*, meta, ws: Workspace) -> str:
    """Build the initial user-message brief the agent sees on turn 1.

    Embeds the function's identity (name, address, target binary,
    target size, cflags, signature, tail-merge donor) and the rendered
    ``info.md`` brief (types referenced, cross-function calls,
    **name-pattern relatives** marked byte-exact / diffing, structural
    siblings) directly in the user prompt — so the agent starts turn 1
    with full structural awareness and can pick the right next move
    (verify / read / fetch a byte-exact relative) immediately, instead
    of paying a tool-call round-trip for mechanical bootstrap.

    scratch.c is NOT embedded here — even small functions are tens of
    lines and the agent should ``read("scratch.c")`` once it knows the
    target.  info.md is the static structural pane; scratch.c is the
    editable body.
    """
    info_path = ws.work_dir / "info.md"
    info_md = info_path.read_text() if info_path.is_file() else "(info.md missing)"

    lines: list[str] = []
    lines.append(f"# Function under test: `{meta.function}`")
    lines.append("")
    lines.append(f"- **address**: `{meta.address_hex}`")
    lines.append(f"- **target size**: {meta.target_size} bytes (in {meta.target.value})")
    lines.append(f"- **source file**: `{meta.source_file}`" if meta.source_file else "- **source file**: (unknown)")
    if meta.signature:
        lines.append(f"- **signature**: `{meta.signature}`")
    lines.append(f"- **cflags**: `{' '.join(meta.cflags)}`")
    if meta.tail_merge_donor:
        lines.append(
            f"- **tail-merge donor**: `{meta.tail_merge_donor}` — the "
            f"target's trailing `jmp` lands inside this sibling; verify "
            f"accounts for it."
        )
    lines.append("")
    lines.append(
        "Your workspace is ALREADY composed: `scratch.c` carries the "
        "current best body wrapped in a self-contained TU, `info.md` is "
        "the structural brief (reproduced below), and `open-watcom/` is "
        "the read-only codegen-source oracle.  Reach for `verify()` "
        "first to see where we stand, or `read(\"scratch.c\")` to see "
        "the body — then drive toward byte-exact, or to a classified "
        "residue (shape all zero + named regalloc class)."
    )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(info_md.strip())
    return "\n".join(lines)


def _merge_finish_report(
    *,
    agent_report: AgentFinishReport,
    fn: str,
    target: Target,
    ws: Optional[Workspace],
) -> FinishReport:
    """Combine the model's minimal report with workspace ground truth.

    The model's :class:`AgentFinishReport` carries just the four
    interpretive fields (verdict + reason + optional classification +
    next_suggested_tool); the orchestrator fills in ``function`` /
    ``final_target`` / ``final_verify`` / ``best_verify`` from the
    workspace, and PROMOTES the verdict when ground truth disagrees
    (e.g. the model said improved_partial but the snapshot is exact —
    we trust the snapshot).
    """
    truth = _ws_truth_verify(target, ws)
    verdict = agent_report.verdict
    reason = agent_report.reason
    # Trust ground truth over the model's self-report — BOTH DIRECTIONS.
    # The agent occasionally claims a stronger verdict than the snapshot
    # supports (Opus 4.7 once reported byte_exact on a 199-byte residue
    # because the shape said width=1 spill=0 seat=0 — mistook that for
    # "done"), or a weaker one (claims build_broken when the build
    # actually succeeded but the agent gave up).  Reconcile via
    # SNAPSHOT, which is the only ground truth.
    if truth is not None:
        truth_matched = truth.shape is not None and truth.shape.is_matched
        if truth.exact:
            # PROMOTE: snapshot IS byte-exact → verdict must be BYTE_EXACT.
            if verdict != Verdict.BYTE_EXACT:
                reason = (f"[promoted: best snapshot is byte-exact; "
                          f"model claimed {verdict.value}] {reason}")[:800]
                verdict = Verdict.BYTE_EXACT
        else:
            # NOT byte-exact in the snapshot.  Block any byte_exact claim,
            # and reconcile shape_matches / build_broken against truth.
            if verdict == Verdict.BYTE_EXACT:
                if truth_matched:
                    reason = (f"[demoted: model claimed byte_exact but "
                              f"snapshot is shape-matched at "
                              f"{truth.byte_diff}b residue] {reason}")[:800]
                    verdict = Verdict.SHAPE_MATCHES
                else:
                    reason = (f"[demoted: model claimed byte_exact but "
                              f"snapshot is {truth.byte_diff}b with shape "
                              f"residue] {reason}")[:800]
                    verdict = Verdict.IMPROVED_PARTIAL
            elif verdict == Verdict.SHAPE_MATCHES and not truth_matched:
                # DEMOTE: model claimed shape_matches but the snapshot's
                # shape STILL has divergent layers (fix_next != none).
                # DeepSeek hit this on pm_map2.c: claimed shape_matches
                # on residues like ``Σ1 → seat``, which are real seat
                # divergence, not classified-residue territory.
                shape_str = (truth.shape.fmt() if truth.shape
                             else "(no shape data)")
                reason = (f"[demoted: model claimed shape_matches but "
                          f"snapshot shape is {shape_str}] {reason}")[:800]
                verdict = Verdict.IMPROVED_PARTIAL
            elif truth_matched and verdict not in (
                Verdict.SHAPE_MATCHES, Verdict.BYTE_EXACT,
            ):
                # PROMOTE the other direction: snapshot is shape-matched
                # but model was conservative.
                reason = (f"[promoted: best snapshot is shape-matched; "
                          f"model claimed {verdict.value}] {reason}")[:800]
                verdict = Verdict.SHAPE_MATCHES
            elif verdict == Verdict.BUILD_BROKEN and truth.build_ok:
                # DEMOTE: model says build_broken but the snapshot is a
                # working build (just not exact).  This happens when the
                # agent fails its FinishReport composition or gives up
                # without a recent failed verify.
                reason = (f"[demoted: model claimed build_broken but "
                          f"snapshot builds and is {truth.byte_diff}b] "
                          f"{reason}")[:800]
                verdict = Verdict.IMPROVED_PARTIAL
    return FinishReport(
        function=fn,
        final_target=target,
        verdict=verdict,
        reason=reason,
        classification=agent_report.classification,
        next_suggested_tool=agent_report.next_suggested_tool,
        final_verify=truth,
        best_verify=truth,
    )


def _synthesise_finish_report(
    *,
    fn: str,
    target: Target,
    ws: Optional[Workspace],
    verdict: Verdict,
    reason: str,
) -> FinishReport:
    """Build a stand-in FinishReport for failure / interrupt paths.

    Critical: when the agent fails to emit a valid FinishReport (output
    retries exhausted, time budget, etc.) but the workspace's best
    snapshot is byte-exact — or shape-matched — the run actually
    SUCCEEDED.  We must reflect that, otherwise a real win is
    misreported as ``build_broken`` and the byte-exact ``scratch.c``
    sitting in ``work/`` doesn't get auto-applied.  Worked-example
    from glm-5.2-short on controls.c: ``control_buttons`` reached 0/N
    byte-exact internally, then exceeded the output-retry budget while
    composing the FinishReport — without this fix the win was lost.
    """
    from c2.decompile.models import VerifyResult

    best_snap = ws.read_best() if ws is not None else None

    # Promote the verdict on the basis of OBSERVED ground truth in the
    # best snapshot.  The agent's stated verdict (or our default
    # ``build_broken``) is only used when there is no snapshot OR the
    # snapshot is genuinely worse than the caller's claim.
    promoted_verdict = verdict
    if best_snap is not None:
        if best_snap.byte_diff == 0:
            promoted_verdict = Verdict.BYTE_EXACT
        elif best_snap.shape is not None and best_snap.shape.is_matched:
            promoted_verdict = Verdict.SHAPE_MATCHES
        elif promoted_verdict == Verdict.BUILD_BROKEN:
            # We have a non-zero, non-matched best but it IS a real
            # build.  Better classified as ``improved_partial`` than
            # the doom-and-gloom ``build_broken`` default.
            promoted_verdict = Verdict.IMPROVED_PARTIAL

    fallback_vr = VerifyResult(
        target=target,
        build_ok=(best_snap is not None),
        byte_diff=999_999 if best_snap is None else best_snap.byte_diff,
        exact=(best_snap is not None and best_snap.byte_diff == 0),
        shape=best_snap.shape if best_snap else None,
        best_so_far=best_snap,
    )
    if promoted_verdict != verdict:
        reason = (
            f"[ground truth from best snapshot, original verdict={verdict.value}] "
            + reason
        )
    return FinishReport(
        function=fn,
        final_target=target,
        verdict=promoted_verdict,
        reason=reason[:500],
        final_verify=fallback_vr,
        best_verify=fallback_vr,
    )


def _race_rank_key(report: FinishReport) -> tuple:
    """Sort key for picking the best replica of a raced function.

    Lower is better: lexicographic on the layered shape vector
    ``(ir, width, spill, seat)`` (the project's fix-order priority),
    then byte_diff as the tiebreaker.  A replica with no best snapshot
    sorts last.
    """
    bv = report.best_verify
    if bv is None:
        return (1, (1 << 30,) * 4, 1 << 30)
    if bv.shape is not None:
        sh = bv.shape
        vec = (sh.ir[0], sh.width[0], sh.spill[0], sh.seat[0])
    else:
        vec = ((1 << 30) - 1,) * 4
    return (0, vec, int(bv.byte_diff))


def _apply_race_winners(
    reports: list[FinishReport],
    *,
    cfg: OrchestratorConfig,
    project,
    reporter: LiveReporter,
) -> None:
    """After a ``--count N`` race, apply the SINGLE best replica per
    function.  Runs post-gather on one thread, so there is no concurrent
    writer; :func:`apply_if_improves` stays monotonic against HEAD.
    """
    from c2.decompile.apply_best import apply_if_improves

    by_fn: dict[str, list[FinishReport]] = {}
    for r in reports:
        by_fn.setdefault(r.function, []).append(r)

    for fn, group in by_fn.items():
        winner = min(group, key=_race_rank_key)
        if winner.run_dir is None:
            reporter.print(f"[yellow]race[{fn}]: winner has no run dir; skipping apply[/]")
            continue
        try:
            ws = Workspace(Path(winner.run_dir))
            decision = apply_if_improves(
                ws=ws, project=project,
                project_root=cfg.project_root, function=fn,
            )
            key = _race_rank_key(winner)
            shp = "/".join(str(x) for x in key[1]) if key[0] == 0 else "n/a"
            reporter.print(
                f"[bold cyan]race[{fn}][/]: best of {len(group)} "
                f"(shape {shp}, {winner.best_verify.byte_diff if winner.best_verify else '?'}b) "
                f"-> {decision.verdict.value}, "
                + ("[green]applied[/]" if decision.applied else "not applied")
                + f"  ({Path(winner.run_dir).name})"
            )
        except Exception as e:  # noqa: BLE001
            reporter.print(f"[red]race[{fn}]: apply failed: {type(e).__name__}: {e}[/]")


def _postprocess(
    report: FinishReport,
    *,
    ws: Optional[Workspace],
    cfg: OrchestratorConfig,
    project,
) -> None:
    """Apply byte-exact wins AND clear shape improvements if configured.

    Per Hard Rule #3, an edit that drops shape_distance is PS-faithful
    even if the byte count rose.  This hook materialises that ranking
    objectively via :func:`c2.decompile.apply_best.apply_if_improves`,
    which compares the agent's BEST snapshot against HEAD's shape
    vector from ``.c2-cache/verify.json`` and applies iff:

      * the candidate is byte-exact, OR
      * the candidate strictly improves the layered shape vector
        ``(ir, width, spill, seat)`` (lex; ir-drop > width-drop > …), OR
      * the candidate ties shape and strictly improves bytes (the
        regalloc tie-break rung).

    Regressions and ties are SKIPPED with a history.jsonl breadcrumb,
    so postmortems can see exactly why a run was not landed.

    NOTE: byte-exact in the standalone scratch compile does NOT
    guarantee byte-exact in the full TU compile (sibling functions in
    the same .c can influence regalloc / scheduling).  The user must
    re-run ``c2 decomp-verify`` after apply to confirm the win
    generalised; the orchestrator records ``applied`` / ``apply_skipped``
    / ``apply_failed`` in history.jsonl so the trail is clear.
    """
    if not cfg.apply_byte_exact:
        return
    if cfg.count > 1:
        # Racing N replicas on one function: per-agent apply is
        # suppressed to avoid concurrent writers to the same TU.  The
        # single best replica is applied once, post-race, in
        # run_orchestrator (_apply_race_winners).
        return
    if ws is None:
        return
    from c2.decompile.apply_best import apply_if_improves
    apply_if_improves(
        ws=ws,
        project=project,
        project_root=cfg.project_root,
        function=report.function,
    )


# ── entry point ──────────────────────────────────────────────────────────


async def run_orchestrator(
    resolution: Resolution,
    cfg: OrchestratorConfig,
) -> list[FinishReport]:
    """Run the decompile loop end-to-end.  Returns one FinishReport per
    target."""
    cfg.runs_root.mkdir(parents=True, exist_ok=True)

    # Configure tracing FIRST so the orchestrator's own span sees a
    # configured tracer.  100% local: never sends to logfire cloud or
    # any unsolicited OTLP endpoint -- see :mod:`c2.decompile.tracing`.
    if cfg.trace:
        trace_file = cfg.trace_file or (cfg.runs_root / "traces.jsonl")
        configure_tracing(
            enabled=True,
            trace_file=trace_file,
            otlp_endpoint=cfg.otlp_endpoint,
        )

    reporter = LiveReporter(
        runs_root=cfg.runs_root,
        jsonl=cfg.jsonl_output,
    )

    # Persist the manifest so the run is inspectable after the fact.
    manifest = {
        "started_at": time.time(),
        "batch": cfg.batch,
        "target": cfg.target.value,
        "model_id": cfg.model_id,
        "targets": resolution.targets,
        "skipped_exact": resolution.skipped_exact,
        "unknown": resolution.unknown,
    }
    (cfg.runs_root / "manifest.json").write_text(json.dumps(manifest, indent=2))

    project = engine_glue.load_project(cfg.project_root, cfg.target)

    sem = asyncio.Semaphore(cfg.batch)

    async def _bounded(fn: str) -> FinishReport:
        async with sem:
            return await _run_one_agent(fn, cfg=cfg, reporter=reporter, project=project)

    # Replica expansion: with ``--count N`` each target becomes N labelled
    # replicas (``<fn>#01`` .. ``<fn>#NN``) racing on the SAME function.
    # The ``#NN`` suffix is stripped inside _run_one_agent for all real
    # work; it only distinguishes the reporter row + run dir per replica.
    if cfg.count > 1:
        labels = [
            f"{fn}#{i:02d}"
            for fn in resolution.targets
            for i in range(1, cfg.count + 1)
        ]
    else:
        labels = list(resolution.targets)

    with orchestrator_span(
        batch=cfg.batch, n_targets=len(labels),
        target=cfg.target.value, model_id=cfg.model_id,
    ):
        tasks = [asyncio.create_task(_bounded(lbl)) for lbl in labels]
        try:
            reports = await asyncio.gather(*tasks, return_exceptions=False)
        except (KeyboardInterrupt, asyncio.CancelledError):
            for t in tasks:
                if not t.done():
                    t.cancel()
            reports = []
            for t in tasks:
                try:
                    reports.append(await t)
                except Exception:
                    continue

    # Race resolution: with ``--count N`` no replica auto-applied (to
    # avoid concurrent TU writers).  Now that all replicas are done and
    # we're back on a single thread, apply the SINGLE best replica per
    # function -- apply_if_improves is monotonic against HEAD, so it only
    # lands a genuine improvement.
    if cfg.count > 1 and cfg.apply_byte_exact:
        _apply_race_winners(reports, cfg=cfg, project=project, reporter=reporter)

    # Flush any in-flight trace spans BEFORE we write final.json so a
    # caller reading the trace file finds it complete.
    flush_tracing()

    # Final summary
    final_summary = {
        "started_at": manifest["started_at"],
        "ended_at": time.time(),
        "reports": [r.model_dump() for r in reports],
    }
    (cfg.runs_root / "final.json").write_text(
        json.dumps(final_summary, indent=2, default=str)
    )
    return reports

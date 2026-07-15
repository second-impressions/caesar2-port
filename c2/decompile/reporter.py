"""Live progress stream for the orchestrator.

Plain stream by design (per user spec — no curses, no redraw): one
timestamped line per state change, suitable for tail -f / log capture.
Every event is ALSO mirrored to ``<runs_root>/orchestrator.jsonl`` for
postmortem inspection.
"""

from __future__ import annotations

import json
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, TextIO

from rich.console import Console
from rich.markup import escape as rich_escape
from rich.table import Table

from c2.decompile.models import (
    AgentSnapshot,
    AgentStatus,
    BestSnapshot,
    FinishReport,
    ShapeDistance,
    Target,
    VerifyResult,
    Verdict,
)


def _now_hms() -> str:
    return time.strftime("%H:%M:%S")


# ── colour palette (rich markup) ─────────────────────────────────────────
# Colours are emitted only when the project's NO_COLOR convention is OFF
# (i.e. ``C2_COLOR=1``).  Otherwise rich's Console with ``no_color=True``
# strips ANSI but still parses ``[tag]`` markup, so the same code path
# works for both styled and plain output.

_STATUS_COLOUR = {
    "pending":     "dim",
    "composing":   "cyan",
    "running":     "yellow",
    "finishing":   "magenta",
    "done":        "green",
    "failed":      "bold red",
}

_BADGE = {
    "exact":    ("[bold green]✓[/]", "green"),
    "new_best": ("[yellow]★[/]", "yellow"),
    "regular":  ("[dim]·[/]", "dim"),
}

_VERDICT_STYLE = {
    Verdict.BYTE_EXACT:       "bold green",
    Verdict.SHAPE_MATCHES:    "green",
    Verdict.IMPROVED_PARTIAL: "yellow",
    Verdict.NO_CHANGE:        "dim",
    Verdict.REGRESSED:        "red",
    Verdict.BUILD_BROKEN:     "bold red",
}


@dataclass
class AgentState:
    """Mutable per-agent state held in the reporter."""

    fn: str
    started_at: float
    status: AgentStatus = AgentStatus.PENDING
    turns: int = 0
    tool_calls: int = 0
    last_tool: Optional[str] = None
    last_event_at: float = 0.0    # for step-duration timing
    best: Optional[BestSnapshot] = None
    current: Optional[VerifyResult] = None
    final: Optional[FinishReport] = None
    error: Optional[str] = None

    def snapshot(self) -> AgentSnapshot:
        return AgentSnapshot(
            fn=self.fn,
            status=self.status,
            started_at=self.started_at,
            turns=self.turns,
            tool_calls=self.tool_calls,
            last_tool=self.last_tool,
            best=self.best,
            current=self.current,
            final=self.final,
            error=self.error,
        )


class LiveReporter:
    """Owns stdout + the orchestrator.jsonl event log.

    Thread-safe — tools call ``reporter.event(fn, ...)`` from worker
    threads spawned by ``asyncio.to_thread`` inside the verify path.

    Output is rendered via :class:`rich.console.Console` so styling
    happens through the same markup syntax as the rest of the c2
    toolkit.  Colour is OFF by default (the project's ``NO_COLOR=1``
    convention; opt back in with ``C2_COLOR=1``).
    """

    def __init__(
        self,
        *,
        runs_root: Path,
        out: TextIO = sys.stdout,
        jsonl: bool = False,
        silent: bool = False,
    ):
        self.runs_root = runs_root
        self.out = out
        self.jsonl_mode = jsonl
        self.silent = silent
        self._lock = threading.Lock()
        self._states: dict[str, AgentState] = {}
        self._jsonl_path = runs_root / "orchestrator.jsonl"
        runs_root.mkdir(parents=True, exist_ok=True)

        # Honour the project's NO_COLOR / C2_COLOR convention.  The
        # ``c2.app`` module sets ``NO_COLOR=1`` at import time unless
        # ``C2_COLOR=1`` is set, so rich strips ANSI by default for
        # piped/log-captured output, but the [markup] syntax still
        # parses cleanly.
        import os
        force_plain = bool(os.environ.get("NO_COLOR")) or jsonl
        self._console = Console(
            file=out,
            no_color=force_plain,
            highlight=False,
            markup=True,
            soft_wrap=True,
        )

    # ----- pre-run banners / sweep summary --------------------------

    def print(self, msg: str) -> None:
        """Emit a one-shot banner line (not tied to any agent's state).

        Used by ``run_orchestrator`` for the --apply pre-sweep summary
        and other startup notices.  Respects ``silent`` + ``jsonl``
        modes (silent suppresses; jsonl drops human text -- only the
        per-agent stream remains machine-readable).
        """
        if self.silent or self.jsonl_mode:
            return
        self._console.print(msg)

    # ----- state mgmt -----------------------------------------------

    def register(self, fn: str) -> AgentState:
        with self._lock:
            st = self._states.setdefault(
                fn, AgentState(fn=fn, started_at=time.time())
            )
        self.event(fn, "register", {})
        return st

    def get(self, fn: str) -> AgentState:
        with self._lock:
            return self._states[fn]

    # ----- single-event entry point ---------------------------------

    def event(self, fn: str, etype: str, payload: dict) -> None:
        """Record + emit one event for ``fn``.

        Mutates the agent's state based on ``etype`` and prints a
        one-line summary (unless ``silent``).  Mirrors to JSONL log.
        """
        with self._lock:
            st = self._states.get(fn)
            if st is None:
                now = time.time()
                st = AgentState(fn=fn, started_at=now, last_event_at=now)
                self._states[fn] = st

            now = time.time()
            dt = now - st.last_event_at if st.last_event_at else 0.0
            st.last_event_at = now
            line = self._apply(st, etype, payload, dt=dt)

            # JSONL mirror
            rec = {
                "t": time.time(),
                "type": etype,
                "fn": fn,
                "turns": st.turns,
                "tool_calls": st.tool_calls,
                **payload,
            }
            with self._jsonl_path.open("a") as f:
                f.write(json.dumps(rec, default=str) + "\n")

            # stdout
            if not self.silent and line is not None:
                if self.jsonl_mode:
                    self.out.write(json.dumps(rec, default=str) + "\n")
                    self.out.flush()
                else:
                    # rich Console handles markup + colour + thread-safe
                    # writes (it acquires its own lock internally).
                    self._console.print(line, soft_wrap=True)

    # ----- per-event handling ---------------------------------------

    def _apply(
        self,
        st: AgentState,
        etype: str,
        payload: dict,
        dt: float = 0.0,
    ) -> Optional[str]:
        """Mutate ``st`` and (maybe) return a one-line rich-markup summary.

        Returns ``None`` for events we deliberately don't surface to the
        live stream:

        * ``register`` / ``status``  — lifecycle micro-state (pending /
          composing / running / finishing) is noise; we only show what
          the AGENT is actually doing.
        * ``revert``                 — redundant with the
          ``tool_call: revert_to_best`` line that always precedes it.
        * ``model_turn``             — used only to increment the turn
          counter shown on subsequent tool_call lines.
        * ``verify_start``           — the ``verify_done`` line carries
          the result.
        """
        ts = _now_hms()
        fn_label = rich_escape(st.fn)[:32].ljust(32)
        head = f"[dim]{ts}[/] [cyan]{fn_label}[/]"
        dt_s = f"[dim]+{dt:5.1f}s[/]" if dt > 0 else "[dim]       [/]"

        # ── lifecycle events: silently update state ───────────────────────────
        if etype == "register":
            st.status = AgentStatus.PENDING
            return None
        if etype == "status":
            new_status = payload.get("status")
            if new_status:
                try:
                    st.status = AgentStatus(new_status)
                except ValueError:
                    pass
            return None
        if etype == "model_turn":
            st.turns += 1
            return None
        if etype == "verify_start":
            return None
        if etype == "revert":
            return None

        # ── tool_call ─────────────────────────────────────────────────────
        if etype == "tool_call":
            st.tool_calls += 1
            st.last_tool = payload.get("tool")
            if st.status == AgentStatus.PENDING:
                st.status = AgentStatus.RUNNING
            tool = rich_escape(st.last_tool or "?")
            args_str = _fmt_tool_args(st.last_tool, payload.get("args") or {})
            return (
                f"{head} {dt_s}  [dim]t{st.turns:<3d} #{st.tool_calls:<3d}[/]  "
                f"[bold]→[/] [magenta]{tool}[/][dim]({args_str})[/]"
            )

        # ── verify_done ─────────────────────────────────────────────────
        if etype == "verify_done":
            build_ok = payload.get("build_ok", True)
            byte_diff = payload.get("byte_diff", 0)
            exact = payload.get("exact", False)
            is_new_best = payload.get("is_new_best", False)
            shape = payload.get("shape")
            if not build_ok:
                # Build failure used to render identically to a 0-byte
                # success — surface it explicitly so it's never confused
                # with byte-exactness.
                return (
                    f"{head} {dt_s}  [dim]t{st.turns:<3d} #{st.tool_calls:<3d}[/]  "
                    f"[bold red]✗ BUILD FAIL[/]"
                )
            shape_str = ""
            if shape:
                try:
                    sd = ShapeDistance.model_validate(shape)
                    shape_str = f"  [dim]shape[/] {rich_escape(sd.fmt())}"
                except Exception:
                    pass
            if is_new_best:
                st.best = BestSnapshot(
                    byte_diff=byte_diff,
                    shape=ShapeDistance.model_validate(shape) if shape else None,
                    target=Target(payload.get("target", "watcom")),
                )
            kind = "exact" if exact else ("new_best" if is_new_best else "regular")
            badge, byte_style = _BADGE[kind]
            return (
                f"{head} {dt_s}  [dim]t{st.turns:<3d} #{st.tool_calls:<3d}[/]  "
                f"{badge} [{byte_style}]{byte_diff}[/] [dim]bytes[/]{shape_str}"
            )

        # ── finish / fail ─────────────────────────────────────────────────
        if etype == "finish":
            st.status = AgentStatus.DONE
            verdict_raw = payload.get("verdict", "?")
            try:
                verdict_enum = Verdict(verdict_raw)
                vstyle = _VERDICT_STYLE.get(verdict_enum, "white")
            except ValueError:
                vstyle = "white"
            wall = time.time() - st.started_at
            return (
                f"{head} {dt_s}  [bold]DONE[/]  [{vstyle}]{verdict_raw}[/]  "
                f"[dim]turns={st.turns} tools={st.tool_calls} "
                f"wall={wall:.0f}s[/]"
            )

        if etype == "fail":
            st.status = AgentStatus.FAILED
            st.error = payload.get("error", "")[:200]
            return f"{head}  [bold red]FAILED[/]  [red]{rich_escape(st.error)}[/]"

        return None


def _fmt_tool_args(tool: Optional[str], args: dict) -> str:
    """Render tool args for the live stream — short, scan-friendly.

    Long string values (``edit``'s ``old_text`` / ``new_text``, ``write``'s
    ``content``) collapse to a byte count.  Path-ish values stay verbatim.
    """
    if not args:
        return ""
    parts: list[str] = []
    for k, v in args.items():
        if isinstance(v, str):
            if k in ("old_text", "new_text", "content"):
                parts.append(f"{k}={len(v)}b")
            else:
                snippet = v.replace("\n", "⏎")
                if len(snippet) > 40:
                    snippet = snippet[:37] + "…"
                parts.append(f'{k}="{rich_escape(snippet)}"')
        elif isinstance(v, bool):
            if v:    # only show true booleans — false is the default
                parts.append(k)
        elif isinstance(v, (int, float)):
            parts.append(f"{k}={v}")
        elif v is None:
            continue
        else:
            rep = rich_escape(repr(v))
            if len(rep) > 40:
                rep = rep[:37] + "…"
            parts.append(f"{k}={rep}")
    return ", ".join(parts)

    # ----- summary --------------------------------------------------

    def snapshot_all(self) -> list[AgentSnapshot]:
        with self._lock:
            return [s.snapshot() for s in self._states.values()]

    def render_final_table(self, reports: list[FinishReport]) -> None:
        """Pretty final summary table.  Called by the CLI at end-of-run."""
        if self.jsonl_mode or self.silent:
            return
        tbl = Table(title="decompile summary", show_lines=False, expand=False)
        tbl.add_column("function", style="cyan", no_wrap=True)
        tbl.add_column("verdict")
        tbl.add_column("bytes", justify="right")
        tbl.add_column("shape", justify="right")
        tbl.add_column("target")
        for r in reports:
            v_style = _VERDICT_STYLE.get(r.verdict, "white")
            bd = r.final_verify.byte_diff
            bd_text = f"[bold green]0[/]" if bd == 0 else str(bd)
            shape_text = "—"
            if r.final_verify.shape is not None:
                s = r.final_verify.shape
                ssum = sum(d for d, _ in (s.ir, s.width, s.spill, s.seat))
                isl = f"·i{s.islands}" if s.islands is not None else ""
                shape_text = f"Σ{ssum}{isl} → {s.fix_next.value}"
            tbl.add_row(
                r.function,
                f"[{v_style}]{r.verdict.value}[/]",
                bd_text,
                shape_text,
                r.final_target.value,
            )
        self._console.print(tbl)

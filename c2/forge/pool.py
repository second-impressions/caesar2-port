"""Worker pool driver for forge.

A pool owns N persistent worker subprocesses, each holding ONE warm
podman container and ONE scratch decomp tree.  Variants are dispatched
round-robin and results are streamed back via a JSON-lines protocol
over stdin/stdout.

Why subprocesses (not threads)?  The
container handle / cwd are process-local, and a worker crash should
not bring down the orchestrator.  Also: each subprocess gets its own
import-cached PSRef so the parent can drop its cache after warm-up.

Why JSON-lines (not pickle)?  Variants are small text payloads; the
schema is short.  Pickle would buy nothing and makes the wire-format
opaque to ``strace`` / ``tail -f`` debugging.

Protocol::

    Parent -> Worker:
      {"op": "init", "function": "show_menus",
       "file": "controls.c", "cflags": "...", "image": "..."}
      {"op": "score_only", "id": "baseline", "file_text": "<full>"}
      {"op": "compile", "id": "v0042", "file_text": "<full>"}
      {"op": "exit"}

    Worker -> Parent:
      {"event": "warmed"}
      {"id": "baseline", "ok": true, "bytes": 8, ...}
      {"id": "v0042", "ok": true, "bytes": 8, ...}
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Iterator

from c2.forge.judge import Score
from c2.forge.ps_ref import PSRef
from c2.forge.variant import Variant


_WORKER_MODULE = "c2.forge.worker"


# A tiny result type for the pool's run_stream output -- intentionally
# decoupled from the higher-level PlanResult so the pool doesn't depend
# on any particular experiment shape.  Forge.experiment glues these to
# its own PlanResult after consumption.
@dataclass
class VariantResult:
    """One scored variant: the Variant that produced it + its Score."""
    variant: "Variant"
    score: Score


@dataclass
class _Worker:
    """One subprocess worker.  Internal to the pool."""

    proc: subprocess.Popen
    busy_with: str | None = None        # variant id currently assigned


class ForgePool:
    """Manage N forge workers + serve variant requests."""

    def __init__(self, *, workers: int, file: str, function: str,
                 cflags: str | None = None, image: str | None = None,
                 source_root: Path = Path("decomp")):
        self.n = max(1, int(workers))
        self.file = file
        self.function = function
        self.cflags = cflags
        self.image = image
        self.source_root = source_root
        self._workers: list[_Worker] = []
        self._started = False

    def __enter__(self) -> "ForgePool":
        self._start()
        return self

    def __exit__(self, *_exc) -> None:
        self.shutdown()


    def _start(self) -> None:
        if self._started:
            return
        if not _can_run_subprocess():
            raise RuntimeError(
                "ForgePool requires a Python that can spawn subprocesses; "
                "current environment forbids it.")
        for i in range(self.n):
            proc = subprocess.Popen(
                [sys.executable, "-m", _WORKER_MODULE],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=1,
                text=True,
            )
            init = {
                "op": "init",
                "file": self.file,
                "function": self.function,
                "cflags": self.cflags,
                "image": self.image,
                "source_root": str(self.source_root.resolve()),
            }
            proc.stdin.write(json.dumps(init) + "\n")
            proc.stdin.flush()
            # Wait for the warmed event.
            while True:
                line = proc.stdout.readline()
                if not line:
                    err = proc.stderr.read() if proc.stderr else ""
                    raise RuntimeError(
                        f"forge worker {i} died during warm-up: {err}")
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if msg.get("event") == "warmed":
                    break
                if msg.get("event") == "error":
                    raise RuntimeError(
                        f"forge worker {i} warm-up error: {msg.get('msg')}")
            self._workers.append(_Worker(proc=proc))
        self._started = True

    def shutdown(self) -> None:
        for w in self._workers:
            try:
                w.proc.stdin.write(json.dumps({"op": "exit"}) + "\n")
                w.proc.stdin.flush()
            except Exception:                  # noqa: BLE001
                pass
        for w in self._workers:
            try:
                w.proc.wait(timeout=10)
            except Exception:                  # noqa: BLE001
                w.proc.kill()
        self._workers = []
        self._started = False


    def compile_and_score(self, variant: Variant, ps: PSRef,
                          want_ledger: bool = False) -> Score:
        """Compile a single variant on the first available worker and
        return its Score.  Used for baseline scoring.  ``want_ledger``
        additionally returns the run-ledger islands (baseline only --
        feeds island-first plan ORDERING)."""
        if not self._workers:
            self._start()
        w = self._workers[0]
        return self._round_trip(w, variant, want_ledger=want_ledger)

    def run_stream(self, variants: Iterable[Variant],
                   ps: PSRef) -> Iterator[VariantResult]:
        """Stream variants through the pool, yielding VariantResult
        objects in completion order (NOT input order).

        The dispatcher keeps every worker busy whenever a variant is
        available; ``select.select`` reaps completed work.  ``ps`` is
        only used for typing -- the workers already know which PS
        function to compare against (set in init)."""
        if not self._workers:
            self._start()
        import select

        # FIXME(perf): if the input iterator is itself slow to produce
        # (a deep compose), this loop blocks on the iterator.  Acceptable
        # in v1; consider a producer thread later if it bites.
        it = iter(variants)
        pending: dict[str, Variant] = {}
        idle: list[_Worker] = list(self._workers)
        exhausted = False

        def _dispatch_one(w: _Worker, var: Variant) -> None:
            req = {"op": "compile", "id": var.id, "file_text": var.file_text}
            try:
                w.proc.stdin.write(json.dumps(req) + "\n")
                w.proc.stdin.flush()
            except BrokenPipeError as exc:
                raise RuntimeError(
                    f"forge worker stdin closed unexpectedly: {exc}")
            w.busy_with = var.id
            pending[var.id] = var

        while True:
            # Dispatch as many as we can.
            while idle and not exhausted:
                try:
                    nxt = next(it)
                except StopIteration:
                    exhausted = True
                    break
                _dispatch_one(idle.pop(), nxt)
            if not pending and exhausted:
                break
            # Reap.
            readers = [w.proc.stdout for w in self._workers if w.busy_with]
            if not readers:
                if exhausted:
                    break
                continue
            r, _, _ = select.select(readers, [], [], 120)
            if not r:
                # Stall: rather than hanging, surface a clear error.
                raise RuntimeError(
                    f"forge pool stalled ({len(pending)} in-flight, "
                    "no worker output for 120 s)")
            for fd in r:
                # Find which worker this fd belongs to.
                w = next((ww for ww in self._workers
                          if ww.proc.stdout is fd), None)
                if w is None:
                    continue
                line = fd.readline()
                if not line:
                    err = w.proc.stderr.read() if w.proc.stderr else ""
                    raise RuntimeError(
                        f"forge worker died mid-stream: {err}")
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    continue
                vid = msg.get("id")
                if vid not in pending:
                    continue
                var = pending.pop(vid)
                w.busy_with = None
                idle.append(w)
                yield VariantResult(
                    variant=var,
                    score=_score_from_msg(msg),
                )


    def request_stop(self) -> None:
        """Tell the dispatch loop to stop pulling new variants.
        In-flight workers run to completion; their results are
        drained by :meth:`drain_inflight`.  No-op when no run_stream
        is active."""
        self._stopping = True

    def drain_inflight(self) -> None:
        """Block until every worker is idle, discarding any responses
        that arrive.  Use after :meth:`request_stop` so a subsequent
        :meth:`run_stream` (e.g. a hill-climb round) starts on a clean
        pool with no stale buffered stdout.
        """
        import select
        busy = [w for w in self._workers if w.busy_with]
        deadline = 60.0
        t_start = time.monotonic()
        while busy:
            r, _, _ = select.select(
                [w.proc.stdout for w in busy], [],
                [], max(0.1, deadline - (time.monotonic() - t_start)),
            )
            if not r and (time.monotonic() - t_start) > deadline:
                return                # don't hang; teardown will kill
            for fd in r:
                w = next((ww for ww in self._workers
                          if ww.proc.stdout is fd), None)
                if w is None:
                    continue
                line = fd.readline()
                w.busy_with = None    # discard regardless of payload
                if not line:
                    continue
            busy = [w for w in self._workers if w.busy_with]


    def _round_trip(self, w: _Worker, var: Variant,
                    want_ledger: bool = False) -> Score:
        req = {"op": "compile", "id": var.id, "file_text": var.file_text}
        if want_ledger:
            req["want_ledger"] = True
        w.proc.stdin.write(json.dumps(req) + "\n")
        w.proc.stdin.flush()
        while True:
            line = w.proc.stdout.readline()
            if not line:
                err = w.proc.stderr.read() if w.proc.stderr else ""
                raise RuntimeError(f"forge worker died: {err}")
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            if msg.get("id") == var.id:
                return _score_from_msg(msg)


def _can_run_subprocess() -> bool:
    """Defensive: refuse to start if we're already a worker (avoids
    recursion when forge is invoked from a forge worker by mistake)."""
    return os.environ.get("C2_FORGE_WORKER") != "1"


def _score_from_msg(msg: dict) -> Score:
    """Reconstruct a :class:`Score` from a worker reply."""
    return Score(
        ok=bool(msg.get("ok")),
        bytes=int(msg.get("bytes", -1)),
        size=int(msg.get("size", 0)),
        size_delta=int(msg.get("size_delta", 0)),
        shape=msg.get("shape") or {},
        error=str(msg.get("error", "")),
        ledger=msg.get("ledger"),
    )

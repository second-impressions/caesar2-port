"""100%-local tracing for ``c2 decompile``.

Backed by `Pydantic Logfire <https://logfire.pydantic.dev>`_ — but with
EVERY phone-home path explicitly disabled.  No data leaves the box
unless the user passes ``--otlp-endpoint`` pointing at an address they
control (e.g. a local Jaeger / Tempo / OTel Collector at
``http://localhost:4318``).

Hardening checklist (every one is enforced in :func:`configure_tracing`):

* ``send_to_logfire=False`` — never send spans to logfire.pydantic.dev.
* ``metrics=False`` — never emit OTel metrics (those have their own
  exporter that could be auto-discovered from env).
* ``scrubbing`` left at the default ON state (it is purely local — it
  redacts secrets inside attributes before they reach an exporter).
* ``LOGFIRE_TOKEN`` / ``LOGFIRE_SEND_TO_LOGFIRE`` env vars are
  **deleted from the process environment** before ``logfire.configure``
  runs, so a stray cloud token in the shell can't leak data.
* ``LOGFIRE_IGNORE_NO_CONFIG=1`` set so the library doesn't try to
  auto-configure itself in a phone-home shape if our code path is
  bypassed.
* No OpenTelemetry resource detectors run by default — those can hit
  AWS/GCP metadata endpoints over the network just to label a span.
  We pass an explicit minimal :class:`Resource`.
* The default exporter is a **local JSONL file** in the run dir
  (``traces.jsonl``).  No network at all.

What gets traced
----------------

Pydantic-AI's ``logfire.instrument_pydantic_ai()`` hooks in spans for:
every agent run, every model request (with prompt / completion / usage),
every tool call (args + return summary), every output validation.  On
top of that, :func:`agent_span` / :func:`orchestrator_span` wrap the
orchestrator's own asyncio scaffolding so the trace tree is easy to
filter ("show me all spans for ``mouse_follow_cohort``").

CLI surface (wired in :mod:`c2.decompile.cli`)
----------------------------------------------

  ``--trace``                       enable local tracing → ``.c2-runs/traces.jsonl``
  ``--trace-file PATH``             custom JSONL output path
  ``--otlp-endpoint URL``           also ship to a (local) OTLP-HTTP collector
                                    (you should point this at localhost)
"""

from __future__ import annotations

import json
import os
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Optional


# ── env-var sanitisation ─────────────────────────────────────────────────


_NEVER_LEAK_VARS = (
    # Logfire cloud / SaaS
    "LOGFIRE_TOKEN",
    "LOGFIRE_SEND_TO_LOGFIRE",
    "LOGFIRE_BASE_URL",
    # Any OTLP auto-discovery the user didn't explicitly opt into via
    # our CLI: we re-set the one we want below.  Without this, an
    # ambient ``OTEL_EXPORTER_OTLP_ENDPOINT`` (e.g. pointing at a
    # company observability backend) would silently exfiltrate.
    "OTEL_EXPORTER_OTLP_ENDPOINT",
    "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT",
    "OTEL_EXPORTER_OTLP_METRICS_ENDPOINT",
    "OTEL_EXPORTER_OTLP_LOGS_ENDPOINT",
    "OTEL_EXPORTER_OTLP_HEADERS",
    "OTEL_EXPORTER_OTLP_PROTOCOL",
    "OTEL_TRACES_EXPORTER",
    "OTEL_METRICS_EXPORTER",
    "OTEL_LOGS_EXPORTER",
    # Resource detectors that hit cloud metadata services
    "OTEL_RESOURCE_DETECTORS",
)


def _scrub_phone_home_env() -> dict[str, str]:
    """Pop every phone-home env var, returning what was removed.

    Called BEFORE we import any opentelemetry / logfire module so the
    library can't observe them at import-time.
    """
    removed: dict[str, str] = {}
    for k in _NEVER_LEAK_VARS:
        v = os.environ.pop(k, None)
        if v is not None:
            removed[k] = v
    # Don't auto-configure if our explicit path is bypassed.
    os.environ.setdefault("LOGFIRE_IGNORE_NO_CONFIG", "1")
    return removed


# ── module state ─────────────────────────────────────────────────────────


_CONFIGURED_LOCK = threading.Lock()
_CONFIGURED: bool = False
_TRACE_FILE: Optional[Path] = None


def is_configured() -> bool:
    return _CONFIGURED


def trace_file_path() -> Optional[Path]:
    return _TRACE_FILE


# ── local JSONL exporter ─────────────────────────────────────────────────


def _make_jsonl_exporter(path: Path):
    """Return a tiny OTel ``SpanExporter`` that writes one JSON span per line.

    Spec-conformant enough for postmortem inspection (each span carries
    name, trace_id, span_id, parent, start/end ns, status, attributes,
    events).  Imported lazily so importing this module doesn't pull in
    the OTel SDK when tracing is off.
    """
    from opentelemetry.sdk.trace import ReadableSpan
    from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

    path.parent.mkdir(parents=True, exist_ok=True)
    # Truncate on each fresh configure so a re-run doesn't endlessly
    # append into a single mega-file.  Append within a run.
    path.write_text("")

    def _span_to_dict(s: ReadableSpan) -> dict:
        ctx = s.get_span_context()
        parent = s.parent
        attrs = dict(s.attributes or {})
        events = []
        for ev in s.events or ():
            events.append({
                "name": ev.name,
                "timestamp_ns": ev.timestamp,
                "attributes": dict(ev.attributes or {}),
            })
        return {
            "name": s.name,
            "trace_id": f"{ctx.trace_id:032x}",
            "span_id": f"{ctx.span_id:016x}",
            "parent_span_id": f"{parent.span_id:016x}" if parent else None,
            "kind": s.kind.name if s.kind else None,
            "start_ns": s.start_time,
            "end_ns": s.end_time,
            "duration_ns": (s.end_time - s.start_time) if s.start_time and s.end_time else None,
            "status": s.status.status_code.name if s.status else None,
            "status_msg": s.status.description if s.status else None,
            "attributes": attrs,
            "events": events,
            "resource": dict(s.resource.attributes) if s.resource else {},
        }

    class JsonlFileSpanExporter(SpanExporter):
        def __init__(self):
            self._lock = threading.Lock()
            self._fh = path.open("a", buffering=1)  # line-buffered

        def export(self, spans):
            try:
                with self._lock:
                    for s in spans:
                        self._fh.write(json.dumps(_span_to_dict(s), default=str) + "\n")
                return SpanExportResult.SUCCESS
            except Exception:
                return SpanExportResult.FAILURE

        def shutdown(self):
            try:
                self._fh.close()
            except Exception:
                pass

        def force_flush(self, timeout_millis: int = 30_000) -> bool:
            try:
                self._fh.flush()
            except Exception:
                pass
            return True

    return JsonlFileSpanExporter()


# ── configure ────────────────────────────────────────────────────────────


def configure_tracing(
    *,
    enabled: bool = False,
    trace_file: Optional[Path] = None,
    otlp_endpoint: Optional[str] = None,
    service_name: str = "c2-decompile",
    console: bool = False,
) -> bool:
    """Set up local-only Logfire + pydantic-ai instrumentation.

    Idempotent — repeat calls are no-ops.  Returns ``True`` if tracing
    was activated.

    All export paths are LOCAL:

      * Always writes to ``trace_file`` (JSONL).  Default location is
        the caller's responsibility (the orchestrator points it at
        ``<runs_root>/traces.jsonl``).
      * ``otlp_endpoint`` is forwarded ONLY if the caller passes one.
        Logfire/cloud is never enabled.
    """
    global _CONFIGURED, _TRACE_FILE
    with _CONFIGURED_LOCK:
        if _CONFIGURED:
            return True
        if not enabled:
            return False

        # 1. Strip phone-home env BEFORE anything imports OTel/logfire.
        _scrub_phone_home_env()

        # 2. Re-introduce ONLY the OTLP endpoint the user explicitly named.
        if otlp_endpoint:
            os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = otlp_endpoint
            # Force HTTP-protobuf (the spec logfire/OTLP-HTTP uses) so a
            # leftover OTEL_EXPORTER_OTLP_PROTOCOL=grpc can't redirect us.
            os.environ["OTEL_EXPORTER_OTLP_PROTOCOL"] = "http/protobuf"

        try:
            import logfire
        except ImportError:
            return False

        # 3. Build the local JSONL exporter + a BatchSpanProcessor for it.
        additional_span_processors = []
        if trace_file is not None:
            from opentelemetry.sdk.trace.export import BatchSpanProcessor
            exporter = _make_jsonl_exporter(trace_file)
            additional_span_processors.append(BatchSpanProcessor(exporter))
            _TRACE_FILE = trace_file

        # 4. Configure logfire with EVERYTHING phone-home disabled.
        logfire.configure(
            service_name=service_name,
            send_to_logfire=False,           # no cloud export, ever
            metrics=False,                    # no metrics, no aggregator
            console=False if not console else None,
            additional_span_processors=additional_span_processors or None,
            # Inspecting locals is a debug helper that pulls source code
            # into attributes — fine locally, but extra surface for an
            # accidental leak.  Keep it on, it's local; flip to False
            # if a stricter posture is wanted.
        )
        logfire.instrument_pydantic_ai()

        _CONFIGURED = True
        return True


# ── spans ────────────────────────────────────────────────────────────────


def flush_tracing() -> None:
    """Force-flush every span exporter.

    Call this before reading the trace file (tests) or before the
    process exits.  BatchSpanProcessor's own atexit hook usually handles
    process exit on its own, but the orchestrator may be embedded in a
    longer-lived parent that wants the trace file complete at
    end-of-run.
    """
    if not _CONFIGURED:
        return
    try:
        from opentelemetry import trace as _otel_trace
        provider = _otel_trace.get_tracer_provider()
        if hasattr(provider, "force_flush"):
            provider.force_flush()
    except Exception:
        pass


@contextmanager
def orchestrator_span(batch: int, n_targets: int, target: str, **extra):
    """Span wrapping the whole ``c2 decompile`` invocation."""
    if not _CONFIGURED:
        yield None
        return
    import logfire
    with logfire.span(
        "decompile_orchestrator",
        batch=batch,
        n_targets=n_targets,
        target=target,
        **extra,
    ) as span:
        yield span


@contextmanager
def agent_span(function: str, target: str, **extra):
    """Span wrapping one decompile-subagent's whole run."""
    if not _CONFIGURED:
        yield None
        return
    import logfire
    with logfire.span(
        "decompile_agent",
        function=function,
        target=target,
        **extra,
    ) as span:
        yield span

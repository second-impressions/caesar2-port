"""``c2 decompile`` — pydantic-ai-powered subagent orchestrator.

Drives N parallel decompilation subagents against still-diffing Caesar II
functions.  Each subagent is a pydantic-ai :class:`Agent` running in its
own sandboxed working directory; the orchestrator owns the run-dir
metadata, history, and best-snapshot bookkeeping and streams progress
back to stdout.

This package is self-contained — it does NOT import from the legacy
``c2_ext`` package, so ``c2_ext`` can be removed once this path proves
out.

Entry point: ``c2 decompile`` (the typer subcommand), wired in
``c2/app.py``.
"""

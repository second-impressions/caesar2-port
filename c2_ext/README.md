# `c2_ext` — DEPRECATED legacy harness

This package was the original per-function decompilation harness used
by the now-disabled `.pi/extensions/c2/` pi extension and its
`c2-decompile` subagent.  It has been **superseded** by the
[`c2/decompile/`](../c2/decompile/) subpackage, exposed via the
[`c2 decompile`](../c2/decompile/cli.py) typer subcommand.

## What replaced it

| old | new |
|---|---|
| `.pi/extensions/c2/` pi extension (TS, `c2call → c2.toolapi`) | `c2/decompile/tools.py` (pure python `@agent.tool` wrappers) |
| `.pi/agents/c2-decompile.md` pi subagent definition | `c2/decompile/agent.py` (pydantic-ai `Agent`) + `c2/decompile/prompt.py` |
| `c2-ext compose / verify / disasm / …` CLI | `c2 decompile` (the typer subcommand orchestrating N parallel subagents) |
| `c2_ext.bundle` / `c2_ext.verify` / `c2_ext.toolchains.*` etc. | `c2/decompile/_engine/` (vendored, owns the code; concurrent-safe — no global container state) |

The new package is **independent of `c2_ext`** — nothing in
`c2/decompile/` imports from here.  `c2_ext` is kept around only
because:

1. its CLI entry point (`c2-ext`) is still referenced by
   `pyproject.toml` and may still work as a manual escape hatch,
2. removing it cleanly is a separate cleanup pass.

For the current per-function / per-file decompile workflow see the
**"Parallel subagent runs: `c2 decompile`"** section of
[`AGENTS.md`](../AGENTS.md) and `c2 decompile --help`.

## What's still here (snapshot at the time of deprecation)

* `compose` / `harvest`     — run-dir lifecycle
* `verify`                  — wraps the Watcom / MSVC compile + byte-diff + shape-distance
* `info` / `bundle`         — function context + scratch.c builder
* `apply`                   — splice scratch.c back into `decomp/src/`
* `toolchains/{base,watcom,msvc}.py` — compile + disasm seam
* `format/{asm,diff}.py`    — L+N line-numbering + diff alignment
* `normalize/{tail_merge,statics}.py` — un-elide PS's tail-merge / detect file-static gates
* `parsers/omf_lines.py`    — OMF LINNUM (Watcom `-d1`) parser
* `embed/`                  — jina embedding index (used by `c2 sibling` not `c2_ext`)
* `cli.py`                  — `c2-ext` argparse entry point

All of the above was copied (with minor adjustments) into
`c2/decompile/_engine/`, which is where future fixes should land.
This module is in maintenance mode.

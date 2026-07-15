"""c2_ext — focused per-function decompilation harness.

A narrow, agent-shaped surface over the existing c2 toolkit:

  * Composes a self-contained run directory for ONE function
  * Compiles a minimal TU and byte-compares against a target binary
  * Renders objdiff-style asm diffs with line numbers normalized to L+0
  * Provides embedding-based nearest-neighbor search over the byte-exact pool

The package is toolchain-agnostic at the interface (:class:`Toolchain` ABC);
v1 ships :class:`WatcomToolchain` for the Caesar II PS.EXE corpus.

See ``.c2-extension.yml`` at the project root for configuration and the
TS extensions under ``.pi/extensions/c2-{subagent,orchestrator}/`` for the
pi-agent surface.
"""

__version__ = "0.1.0"

"""Vendored engine for ``c2 decompile``.

This subpackage is the **owned** reimplementation of what used to live
in :mod:`c2_ext`.  It started life as a literal copy of the c2_ext
modules with imports rewritten to live here; over time it diverges to
fit the orchestrator's needs (in particular: concurrent-safe verify
without globals, no warm-container reach into ``c2.commands.decomp_verify``).

External callers should NOT import from here directly — go through the
public surface in ``c2.decompile`` (the typed tool wrappers around the
agent), which is the only stable boundary.  ``c2_ext`` can be deleted
once this engine has fully proven out.
"""

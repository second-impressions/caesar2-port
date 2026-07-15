"""Asm + diff rendering layer (toolchain-agnostic).

The :mod:`c2_ext.format.asm` module turns a list of :class:`Insn` into
strings with the ``L+N`` line column applied; :mod:`c2_ext.format.diff`
renders the objdiff-style side-by-side table.

These modules KNOW about the result of :class:`Toolchain.disassemble`
but never the toolchain itself — pure transformation.
"""

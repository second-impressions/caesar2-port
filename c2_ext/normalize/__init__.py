"""Target-byte normalization layer.

Two transforms run between :meth:`Toolchain.function_bytes` and
:func:`verify`:

* :mod:`c2_ext.normalize.tail_merge` un-merges Watcom's cross-function
  tail-merge optimization so a standalone-TU compile can produce
  matching bytes (the dependent's emitted ``jmp donor+N`` is replaced
  with the donor's actual shared-tail bytes inline).
* :mod:`c2_ext.normalize.statics` detects file-scope-static references
  the standalone TU cannot satisfy; we bail out with a clear message
  rather than producing a confusingly-impossible-to-match scratch.
"""

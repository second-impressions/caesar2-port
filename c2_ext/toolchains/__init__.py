"""Toolchain registry — pluggable per-compiler backends.

Ships two backends out of the box:

* :class:`watcom.WatcomToolchain` (``watcom-10.0a``) — the DOS
  ``PS.EXE`` byte oracle, compiled with Watcom C/C++ 10.0a.
* :class:`msvc.MSVCToolchain` (``msvc-4.0``) — the Windows
  ``CAESAR2.EXE`` byte oracle, compiled with MSVC 4.0 ``/Od``.

New toolchains register via the ``@register`` decorator from
:mod:`c2_ext.toolchains.base` and become available by name in the
``toolchain.name:`` field of ``.c2-extension.yml``.
"""

# Import side-effect: register every shipped toolchain.
from c2_ext.toolchains import watcom  # noqa: F401
from c2_ext.toolchains import msvc    # noqa: F401

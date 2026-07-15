"""Toolchain abstract base class + registry.

The :class:`Toolchain` interface is the seam where compiler-specific
knowledge lives.  Everything in :mod:`c2_ext` above it (run-dir
composition, format layer, embedding search, the agent tools) is
toolchain-agnostic.

To add support for a new toolchain (e.g. MSVC 4.0 against
``CAESAR2.EXE``), subclass :class:`Toolchain`, decorate the class with
:func:`register`, and reference it by name in ``.c2-extension.yml``::

    @register("msvc-4.0")
    class MSVCToolchain(Toolchain):
        ...
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from c2.decompile._engine.project import ProjectConfig


#  Public datatypes returned by toolchain methods

@dataclass(frozen=True)
class FunctionInfo:
    """Where a function lives in the target binary."""

    name: str
    address: int            # virtual address (target's load base + offset)
    size: int               # bytes, exclusive of trailing alignment padding
    source_file: str | None # original .c file name from -d1 debug info, if known
    signature: str | None   # 'int barbarian_in_region(int dirc, int from_sea)' if known


@dataclass(frozen=True)
class Insn:
    """One disassembled instruction, pre-rendered with symbols resolved."""

    offset: int             # byte offset within the function
    size: int               # instruction byte length
    line: int | None        # -d1 source line number (None if no mark + no carry)
    is_donor: bool          # True if this insn came from a tail-merge donor's tail
    mnemonic: str
    op_str: str             # operands with symbols/globals resolved
    raw: bytes              # raw instruction bytes
    is_relocation: bool     # True if displacement contains a relocation byte


@dataclass(frozen=True)
class CompileResult:
    """Output of compiling a scratch TU and extracting a function's bytes."""

    ok: bool
    stderr: str
    function_bytes: bytes | None      # None if compile failed
    fixup_offsets: frozenset[int]     # byte offsets within function_bytes that are relocations
    line_marks: tuple[tuple[int, int], ...] = ()
    """``((offset_in_function, scratch_c_line), ...)`` mapping each
    instruction's offset back to the line in ``scratch.c`` that emitted
    it.  Empty when debug info is unavailable.
    """


@dataclass(frozen=True)
class NormalizedTarget:
    """Result of un-eliding a target function's bytes for verify-time compare.

    Some toolchains fuse neighboring functions in ways a standalone-TU
    recompile cannot reproduce (Watcom's tail-merge / shared-ret /
    forward fall-through being the canonical example).  Each toolchain
    returns a :class:`NormalizedTarget` from
    :meth:`Toolchain.normalize_target`; toolchains with no elision tricks
    return a pass-through with all donor / fallthrough fields zeroed.
    """

    bytes_: bytes                              # normalized byte sequence
    fixup_offsets: frozenset[int]              # fixup offsets within bytes_
    line_marks: tuple[tuple[int, int], ...]    # ((offset, source_line), ...)
    extra_reloc_offsets: frozenset[int] = frozenset()
    """Synthetic relocation bytes (e.g. backward shared-ret jcc displacements
    that the diff classifier must treat as encoding-equivalent)."""
    donor_name: str | None = None
    donor_boundary: int | None = None
    donor_first_line: int | None = None
    donor_tail_size: int = 0
    fallthrough_callee: str | None = None
    fallthrough_added_bytes: int = 0
    raw_dependent_size: int = 0


#  Registry

_REGISTRY: dict[str, type["Toolchain"]] = {}


def register(name: str) -> Callable[[type["Toolchain"]], type["Toolchain"]]:
    """Decorator: register a Toolchain subclass under the given name."""
    def _wrap(cls: type["Toolchain"]) -> type["Toolchain"]:
        _REGISTRY[name] = cls
        return cls
    return _wrap


def get_toolchain(name: str) -> type["Toolchain"]:
    """Look up a registered Toolchain class by name."""
    try:
        return _REGISTRY[name]
    except KeyError:
        avail = ", ".join(sorted(_REGISTRY)) or "<none>"
        raise KeyError(f"Unknown toolchain {name!r}; registered: {avail}") from None


#  ABC

class Toolchain(ABC):
    """One toolchain instance, bound to a project."""

    def __init__(self, project: "ProjectConfig"):
        self.project = project

    #  Identity

    @property
    def name(self) -> str:
        return self.project.toolchain_spec.name

    @property
    def arch(self) -> str:
        return self.project.toolchain_spec.arch

    @property
    def cflags(self) -> tuple[str, ...]:
        return self.project.toolchain_spec.cflags

    #  Target binary inspection

    @abstractmethod
    def function_info(self, name: str) -> FunctionInfo:
        """Return :class:`FunctionInfo` for the named function.

        Raises :class:`KeyError` if no such function is in the target binary.
        """

    @abstractmethod
    def function_bytes(self, name: str) -> bytes:
        """Return the raw bytes of the named function from the target binary.

        Does NOT apply tail-merge normalization — that's done by
        :mod:`c2_ext.normalize.tail_merge` as a separate layer.
        """

    @abstractmethod
    def function_fixups(self, name: str) -> frozenset[int]:
        """Return relocation byte offsets within the function's bytes.

        These are the bytes whose displacement values differ between the
        target and a recompile because they encode link-time positions.
        Used to mask comparison so "excluding relocations" is honored.
        """

    @abstractmethod
    def line_numbers(self, name: str) -> tuple[tuple[int, int], ...]:
        """Return ``((offset, source_line), ...)`` marks for the function.

        ``offset`` is relative to the function's start.  Empty if no
        debug info (e.g. release builds compiled without ``-d1``).
        """

    @abstractmethod
    def resolve_data_ref(self, addr: int) -> tuple[str, int] | None:
        """Resolve a data address to ``(name, displacement)`` or None."""

    @abstractmethod
    def resolve_code_ref(self, addr: int) -> tuple[str, int] | None:
        """Resolve a code address to ``(function_name, displacement)`` or None."""

    @abstractmethod
    def existing_source(self, name: str) -> tuple[str, str] | None:
        """Return ``(filename, body_text)`` for the function's existing decomp
        source, or None if the function has no decomp yet (stub).

        ``body_text`` should include the signature and ``{...}``.
        """

    #  Compilation

    @abstractmethod
    def compile_scratch(self, run_dir: Path, function_name: str) -> CompileResult:
        """Compile ``run_dir/scratch.c`` and extract the named function's bytes.

        ``run_dir`` is the deterministic per-run directory; ``scratch.c``
        is the agent's editable source; ``include/`` holds project
        headers; compilation must respect :attr:`cflags`.
        """

    #  Disassembly + symbol resolution

    @abstractmethod
    def disassemble(
        self, code: bytes, base_addr: int,
        fixup_offsets: frozenset[int] | None = None,
    ) -> list[Insn]:
        """Disassemble ``code`` starting at virtual address ``base_addr``,
        rendering operands with symbols resolved (via
        :meth:`resolve_code_ref` / :meth:`resolve_data_ref`).

        When ``fixup_offsets`` is given (byte offsets WITHIN ``code``
        that are link-time relocations), instructions overlapping a
        relocation byte are tagged ``is_relocation=True`` so the diff
        layer can compare them by mnemonic alone.
        """

    #  Embedding-time asm normalization

    @abstractmethod
    def normalize_asm_for_embedding(self, asm_text: str) -> str:
        """Strip ISA / toolchain noise so embeddings cluster by semantics."""

    #  Status pool

    @abstractmethod
    def byte_exact_functions(self) -> frozenset[str]:
        """Return the set of function names known to be byte-exact in the
        current decomp tree.  Used as the ``nearest``/``fetch``/``disasm``
        pool when the project config asks for it.
        """

    #  Cross-function elision normalization (toolchain-specific)

    def normalize_target(
        self,
        target_bytes: bytes,
        target_address: int,
        target_fixups: frozenset[int],
        target_lines: tuple[tuple[int, int], ...],
    ) -> NormalizedTarget:
        """Return a :class:`NormalizedTarget` for one target function.

        Default implementation is a pass-through: the target's bytes,
        fixups, and line marks are returned unchanged, with all donor /
        fallthrough fields zeroed.  Watcom overrides this with its
        tail-merge / shared-ret / fall-through normalizer; MSVC keeps
        the default since its codegen doesn't fuse neighbouring
        functions the same way.
        """
        return NormalizedTarget(
            bytes_=target_bytes,
            fixup_offsets=target_fixups,
            line_marks=target_lines,
            raw_dependent_size=len(target_bytes),
        )

    #  Optional per-function structural info (toolchain capability)

    def detect_cross_function_elision(
        self, name: str,
    ) -> tuple[str | None, str | None]:
        """Return ``(tail_merge_donor_name, fallthrough_callee_name)``.

        Both default to ``None`` for toolchains that don't fuse
        neighboring functions.  Watcom overrides this to surface its
        tail-merge donor + fall-through callee in :mod:`c2_ext.info`.
        """
        return None, None

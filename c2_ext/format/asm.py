"""Render an ``Insn`` stream with normalized ``L+N`` line numbers.

The disassembler hands us raw :class:`Insn` objects with no line marks
(``line=None`` on every row).  This module applies the toolchain's
``line_numbers(name)`` table and carries forward marks across
unmarked instructions, then computes ``L+N`` relative to the function's
first emitted source line.

For tail-merge donors (``is_donor=True``), the line column renders as
``D+N`` against the donor's first-emitted-line baseline instead of the
dependent's — making the boundary visible in the diff view.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable

from c2_ext.toolchains.base import Insn


@dataclass(frozen=True)
class Row:
    """One pre-formatted asm row, ready for diff layout."""

    offset: int
    size: int
    line_label: str             # 'L+3' / 'D+0' / '' if no line
    mnemonic: str
    op_str: str
    raw: bytes
    is_donor: bool
    is_relocation: bool
    scratch_line: int | None = None
    """For the YOUR side of a diff: the line in ``scratch.c`` that emitted
    this instruction (None when no debug mark covers it)."""

    @property
    def text(self) -> str:
        ops = f"{self.mnemonic:<6} {self.op_str}".rstrip()
        return ops


def apply_line_numbers(
    insns: Iterable[Insn],
    line_marks: tuple[tuple[int, int], ...],
    *,
    donor_first_line: int | None = None,
    donor_boundary: int | None = None,
    scratch_marks: tuple[tuple[int, int], ...] = (),
) -> list[Row]:
    """Annotate each insn with a normalized line label.

    Parameters
    ----------
    insns
        Disassembled instructions (offsets relative to function start).
    line_marks
        ``((offset, source_line), ...)`` from
        :meth:`Toolchain.line_numbers` for the dependent function.
    donor_first_line
        First emitted line of the donor function (if a tail-merge
        boundary is present), used as the ``D+0`` baseline.
    donor_boundary
        Offset within the (un-merged) function bytes where the donor's
        tail begins.  Every insn at offset >= this uses the ``D+N``
        baseline.
    """
    marks = sorted(line_marks)
    first_dep_line = marks[0][1] if marks else None

    sc_marks = sorted(scratch_marks)
    sc_n = len(sc_marks)

    rows: list[Row] = []
    current_line: int | None = None
    current_scratch_line: int | None = None
    mi = 0
    smi = 0
    n = len(marks)

    for ins in insns:
        # Advance mark pointer past any marks at or before this offset
        while mi < n and marks[mi][0] <= ins.offset:
            current_line = marks[mi][1]
            mi += 1
        while smi < sc_n and sc_marks[smi][0] <= ins.offset:
            current_scratch_line = sc_marks[smi][1]
            smi += 1

        is_donor = (
            donor_boundary is not None
            and ins.offset >= donor_boundary
        )

        label = ""
        if is_donor and donor_first_line is not None and current_line is not None:
            label = f"D+{current_line - donor_first_line}"
        elif not is_donor and first_dep_line is not None and current_line is not None:
            label = f"L+{current_line - first_dep_line}"

        rows.append(Row(
            offset=ins.offset,
            size=ins.size,
            line_label=label,
            mnemonic=ins.mnemonic,
            op_str=ins.op_str,
            raw=ins.raw,
            is_donor=is_donor,
            is_relocation=ins.is_relocation,
            scratch_line=current_scratch_line,
        ))
    return rows


def render_rows(
    rows: list[Row],
    *,
    show_bytes: bool = False,
    show_offset: bool = True,
) -> list[str]:
    """Render a list of :class:`Row` as a flat list of lines.

    Used by ``disasm()`` to write ``target/asm.txt`` and the
    agent-facing single-side disassembly view.
    """
    out: list[str] = []
    prev_donor = False
    for r in rows:
        if r.is_donor and not prev_donor:
            out.append(" tail-merge boundary ")
        prev_donor = r.is_donor

        parts: list[str] = []
        parts.append(f"{r.line_label:<5}")
        if show_offset:
            parts.append(f"{r.offset:04x}")
        if show_bytes:
            parts.append(f"{r.raw.hex():<14}")
        parts.append(r.text)
        out.append(" ".join(parts))
    return out

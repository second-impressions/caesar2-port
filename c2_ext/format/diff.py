"""objdiff-style side-by-side diff renderer.

Aligns target rows against your rows by offset, computes per-row diff
classifications (unchanged / changed / target-only / your-only),
emits a compact context-only or full view.

Diff classification uses *text equality* on the rendered mnemonic+ops
string AFTER both sides went through symbol resolution and operand
fixup masking.  Relocation rows (``is_relocation=True``) are compared
as if their displacement is the same — we want to count them as
equal so the model isn't distracted by link-time noise.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Literal

from c2_ext.format.asm import Row


DiffMarker = Literal[" ", "!", "-", "+"]


@dataclass(frozen=True)
class DiffRow:
    """One side-by-side row in the diff view."""

    marker: DiffMarker                  # ' ' = same, '!' = changed, '-' = target-only, '+' = your-only
    target: Row | None
    yours: Row | None

    @property
    def line_label(self) -> str:
        if self.target is not None:
            return self.target.line_label
        if self.yours is not None:
            return self.yours.line_label
        return ""


def align_and_classify(target: list[Row], yours: list[Row]) -> list[DiffRow]:
    """Align two row streams by offset and classify per row.

    Walks both lists in parallel by offset.  When offsets match, the
    rows are paired and compared.  When offsets diverge, the row with
    the smaller offset is reported as one-sided.

    This is intentionally simple (greedy LCS-by-offset) since the two
    compiles share a function entry-point and tend to drift in bounded
    ways.  Doesn't try to find optimal alignment past a major insertion;
    we accept some false `-`/`+` runs to keep the renderer dumb.
    """
    rows: list[DiffRow] = []
    i = j = 0
    while i < len(target) and j < len(yours):
        ti, yi = target[i], yours[j]
        if ti.offset == yi.offset:
            same = _rows_equal(ti, yi)
            marker: DiffMarker = " " if same else "!"
            rows.append(DiffRow(marker=marker, target=ti, yours=yi))
            i += 1
            j += 1
        elif ti.offset < yi.offset:
            rows.append(DiffRow(marker="-", target=ti, yours=None))
            i += 1
        else:
            rows.append(DiffRow(marker="+", target=None, yours=yi))
            j += 1
    while i < len(target):
        rows.append(DiffRow(marker="-", target=target[i], yours=None))
        i += 1
    while j < len(yours):
        rows.append(DiffRow(marker="+", target=None, yours=yours[j]))
        j += 1
    return rows


# Inverse pairs of x86 conditional-jump mnemonics.  Watcom inverts the
# last conditional branch when the fall-through path is an unconditional
# `call`+`ret` (saves a `jmp`).  Treating je/jne, jl/jge etc. as
# equivalent at relocation sites matches the standalone-TU compile.
_INVERSE_JCC = {
    "je": "jne", "jne": "je",
    "jl": "jge", "jge": "jl",
    "jg": "jle", "jle": "jg",
    "jb": "jae", "jae": "jb",
    "ja": "jbe", "jbe": "ja",
    "js": "jns", "jns": "js",
    "jo": "jno", "jno": "jo",
    "jp": "jnp", "jnp": "jp",
    "jc": "jnc", "jnc": "jc",
    "jz": "jnz", "jnz": "jz",
}


def _rows_equal(a: Row, b: Row) -> bool:
    # Fast path: identical mnemonic + identical op_str.
    if a.mnemonic == b.mnemonic and a.op_str == b.op_str:
        return True
    same_mnemonic = a.mnemonic == b.mnemonic
    inverse_jcc_pair = _INVERSE_JCC.get(a.mnemonic) == b.mnemonic
    # When EITHER side is a relocation site, the operand text legitimately
    # differs by link-time choice; matching mnemonic (or inverse jcc pair
    # for fall-through optimization) is enough to call the rows equivalent.
    if a.is_relocation or b.is_relocation:
        return same_mnemonic or inverse_jcc_pair
    if not same_mnemonic:
        return False
    return a.op_str == b.op_str


def render_diff(
    rows: list[DiffRow],
    *,
    full: bool = False,
    context: int = 3,
) -> list[str]:
    """Render diff rows as a list of output lines.

    When ``full=False`` (default), elides long runs of equal rows
    keeping ``context`` lines on each side of each non-equal row.
    """
    if not rows:
        return []

    if full:
        keep = list(range(len(rows)))
    else:
        keep = _windowed_keep(rows, context=context)

    out: list[str] = []
    prev_donor = False
    last_kept = -2
    for idx in keep:
        if idx != last_kept + 1 and last_kept >= 0:
            out.append("        \u2026")
        r = rows[idx]
        donor_now = (r.target is not None and r.target.is_donor) or (r.yours is not None and r.yours.is_donor)
        if donor_now and not prev_donor:
            out.append(" tail-merge boundary ")
        prev_donor = donor_now
        out.append(_render_row(r))
        last_kept = idx
    return out


def _windowed_keep(rows: list[DiffRow], *, context: int) -> list[int]:
    """Return the sorted set of row indices to render."""
    keep: set[int] = set()
    for idx, r in enumerate(rows):
        if r.marker == " ":
            continue
        for k in range(max(0, idx - context), min(len(rows), idx + context + 1)):
            keep.add(k)
    return sorted(keep)


def _render_row(r: DiffRow) -> str:
    """One row: [target L+N, off, asm]  [yours L+N, off, asm].

    BOTH sides show ``L+N`` (source-line offset from the function's
    first emitted line).  Left side's L+N is anchored to PS's source
    line numbers; right side's L+N is anchored to YOUR scratch.c
    source line numbers.  When the function structures match, the
    L+N labels on each side advance in lockstep — a row where PS's
    L+N != yours' L+N (or where one side has more rows under the same
    L+N than the other) means one statement of your source emits more
    or fewer instructions than PS's equivalent.  Drive that count to
    match.
    """
    target_off = f"{r.target.offset:04x}" if r.target else "    "
    yours_off = f"{r.yours.offset:04x}" if r.yours else "    "
    target_text = r.target.text if r.target else ""
    yours_text = r.yours.text if r.yours else ""
    target_label = r.target.line_label if r.target else ""
    yours_label = r.yours.line_label if r.yours else ""
    return (
        f"{r.marker}{target_label:<6} {target_off}  {target_text:<40}"
        f"  {yours_label:<6} {yours_off}  {yours_text}"
    )

def count_real_diffs(rows: list[DiffRow]) -> int:
    """Count rows that represent a real disagreement."""
    return sum(1 for r in rows if r.marker != " ")

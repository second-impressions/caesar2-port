"""Lift a run dir's scratch.c back into the real project source tree.

The agent's ``scratch.c`` has the bundled types/externs/prototypes at
the top plus the function definition itself.  ``apply`` extracts just
the function definition (via brace match), then splices it over the
matching function in ``decomp/src/<file>.c``, preserving everything
else in the TU (the FUNCTION: / WIN: / Lines comments above, sibling
functions before and after).

Always returns a :class:`ApplyResult` describing what changed.  Pass
``dry_run=True`` to compute the diff without writing.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from c2.decompile._engine.project import ProjectConfig
from c2.decompile._engine.runs import load_meta
from c2.decompile._engine.toolchains.watcom import _find_function_span


class ApplyError(Exception):
    """Raised when the splice can't be performed."""


@dataclass(frozen=True)
class ApplyResult:
    function: str
    source_file: str            # basename, e.g. "controls.c"
    tu_path: str                # full path of the real TU
    bytes_before: int
    bytes_after: int
    bytes_changed: int          # |before_fn_text| + |after_fn_text| diff
    wrote: bool


def apply(project: ProjectConfig, run_dir: Path,
          *, dry_run: bool = False) -> ApplyResult:
    meta = load_meta(run_dir)
    fn_name = meta.function
    src_file = meta.source_file
    if not src_file:
        raise ApplyError(
            "meta.json has no source_file; can't determine which TU to splice into"
        )
    tu_path = project.sources_dir / src_file
    if not tu_path.is_file():
        raise ApplyError(f"TU file not found: {tu_path}")

    scratch_text = (run_dir / "scratch.c").read_text()
    scratch_span = _find_function_span(scratch_text, fn_name)
    if scratch_span is None:
        raise ApplyError(
            f"function {fn_name!r} not found in scratch.c (renamed? signature broken?)"
        )
    sc_start, sc_end = scratch_span
    scratch_fn_text = scratch_text[sc_start:sc_end]

    tu_text = tu_path.read_text()
    tu_span = _find_function_span(tu_text, fn_name)
    if tu_span is None:
        raise ApplyError(
            f"function {fn_name!r} not found in {tu_path}"
        )
    tu_start, tu_end = tu_span

    new_tu = tu_text[:tu_start] + scratch_fn_text + tu_text[tu_end:]
    bytes_changed = abs(len(scratch_fn_text) - (tu_end - tu_start))

    wrote = False
    if not dry_run:
        tu_path.write_text(new_tu)
        wrote = True

    return ApplyResult(
        function=fn_name,
        source_file=src_file,
        tu_path=str(tu_path),
        bytes_before=len(tu_text),
        bytes_after=len(new_tu),
        bytes_changed=bytes_changed,
        wrote=wrote,
    )

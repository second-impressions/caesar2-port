"""Run-directory lifecycle: ``compose`` and ``harvest``.

A run dir is the agent's universe.  Layout::

    <runs_root>/<slug>-<timestamp>/
    \u251c scratch.c           \u2190 editable, lifted from existing source or blank
    \u2514 meta.json           \u2190 extension-internal metadata

``compose`` populates a fresh run dir from a function name; ``harvest``
reads ``scratch.c`` (the result) and optionally runs a final verify.

The scratch is ALWAYS bundled for the **watcom 10.0a** compile target
(PS.EXE is the project's primary byte oracle).  The agent can still
verify against the MSVC/CAESAR2.EXE oracle on demand by passing
``target="msvc"`` to ``verify`` (the same scratch.c is then compiled
with MSVC 4.0 ``/Od`` and byte-compared against CAESAR2.EXE).  Target
bytes / target disassembly are no longer pre-cached \u2014 every
``verify`` and ``disasm`` call fetches them fresh from the appropriate
binary, so the agent picks which oracle to inspect per-call.

Composition errors (file-scope statics, unknown function, etc.) raise
:class:`ComposeError` with a message intended for the orchestrator.
"""

from __future__ import annotations

import json
import shutil
import time
import unicodedata
from dataclasses import dataclass, asdict
from pathlib import Path

from c2_ext.normalize import statics as statics_check
from c2_ext.project import ProjectConfig
from c2_ext.toolchains.base import NormalizedTarget, Toolchain


#  Errors


class ComposeError(Exception):
    """Raised when a run dir cannot be composed for the given function."""


#  Metadata schema


@dataclass(frozen=True)
class RunMeta:
    """Captured at compose-time, read by every later tool invocation."""

    function: str
    address_hex: str
    target_size: int           # bytes in the (possibly normalized) target
    raw_target_size: int       # bytes in the un-normalized target
    toolchain: str             # toolchain id (e.g. 'watcom-10.0a', 'msvc-4.0')
    cflags: tuple[str, ...]
    source_file: str | None
    signature: str | None
    line_marks: tuple[tuple[int, int], ...]   # ((offset, line), ...)
    tail_merge_donor: str | None
    tail_merge_boundary: int | None
    tail_merge_donor_first_line: int | None
    started_at: float
    body_origin: str           # 'existing' | 'blank'
    project_root: str          # repo root, so later tools can re-load ProjectConfig
    target: str = "default"    # named target from .c2-extension.yml (e.g. 'watcom', 'msvc')

    def to_dict(self) -> dict:
        d = asdict(self)
        d["line_marks"] = [list(m) for m in self.line_marks]
        d["cflags"] = list(self.cflags)
        return d

    @property
    def project_root_path(self) -> Path:
        return Path(self.project_root)

    @classmethod
    def from_dict(cls, d: dict) -> "RunMeta":
        return cls(
            function=d["function"],
            address_hex=d["address_hex"],
            target_size=int(d["target_size"]),
            raw_target_size=int(d["raw_target_size"]),
            toolchain=d["toolchain"],
            cflags=tuple(d["cflags"]),
            source_file=d.get("source_file"),
            signature=d.get("signature"),
            line_marks=tuple((int(o), int(l)) for o, l in d["line_marks"]),
            tail_merge_donor=d.get("tail_merge_donor"),
            tail_merge_boundary=d.get("tail_merge_boundary"),
            tail_merge_donor_first_line=d.get("tail_merge_donor_first_line"),
            started_at=float(d["started_at"]),
            body_origin=d["body_origin"],
            project_root=d.get("project_root", ""),
            target=d.get("target", "default"),
        )


#  compose


def compose(
    project: ProjectConfig,
    function_name: str,
    *,
    blank: bool = False,
    out_dir: Path | None = None,
) -> Path:
    """Build a fresh run directory for ``function_name``.

    If ``out_dir`` is None, picks ``<runs_root>/<slug>-<unix_ms>``.

    Returns the run dir path.

    Raises :class:`ComposeError` for any failure that prevents a useful
    run (unknown function, file-scope-static block, etc.).
    """
    tc = project.toolchain()

    # 1. Look up the function
    try:
        info = tc.function_info(function_name)
    except KeyError as e:
        raise ComposeError(str(e)) from None

    # 2. Pull target bytes / fixups / lines, normalize tail-merge
    target_bytes = tc.function_bytes(function_name)
    target_fixups = tc.function_fixups(function_name)
    target_lines = tc.line_numbers(function_name)
    norm = tc.normalize_target(
        target_bytes, info.address, target_fixups, target_lines,
    )

    # 3. File-static gate (bail-out per design)
    sc = statics_check.check(tc, function_name, target_bytes, target_fixups)
    if not sc.ok:
        raise ComposeError(sc.message)

    # 4. Pick the body (existing or blank)
    body_origin = "blank"
    body_text: str
    src_file_name: str | None = info.source_file
    if not blank:
        src = tc.existing_source(function_name)
        if src is not None:
            src_file_name, body_text = src
            body_origin = "existing"
        else:
            body_text = _blank_body(function_name, info.signature)
    else:
        body_text = _blank_body(function_name, info.signature)

    # Identify system #include lines from the original TU so we bring
    # in stdlib bits the function actually uses (e.g. free, NULL).
    system_includes: list[str] = []
    if src_file_name:
        getter = getattr(tc, "source_includes", None)
        if callable(getter):
            for line in getter(src_file_name):
                if line.lstrip().startswith("#include <"):
                    system_includes.append(line)

    # 5. Pick the run-dir path
    if out_dir is None:
        slug = _slug(function_name)
        stamp = int(time.time() * 1000)
        out_dir = project.runs_root / f"{slug}-{stamp}"
    out_dir = out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    # No `target/` subdir: byte oracles + target disassembly are now
    # fetched on demand by `verify` and `disasm`.  No `include/` dir: every type / extern / prototype the function
    # needs is inlined directly into scratch.c by the bundler.  Spares
    # the agent from reading 100KB project headers \u2014 they see ONE file.

    # Symlink the vendored Open Watcom v1 source tree into the run dir
    # as `open-watcom/` so the agent can browse the codegen-source
    # ORACLE for `how does Watcom do X?` questions.  HINT only \u2014 OW
    # v1 (2002) is several years newer than Watcom 10.0a (1995) which
    # built PS.EXE, and codegen evolved across releases (see
    # AGENTS.md / vendor/README.md).
    ow_src = project.root / "vendor" / "open-watcom"
    ow_link = out_dir / "open-watcom"
    if ow_src.is_dir() and not ow_link.exists():
        try:
            ow_link.symlink_to(ow_src.resolve(), target_is_directory=True)
        except OSError:
            # Non-fatal: symlink creation can fail on exotic FSes;
            # the agent just won't have the OW oracle handy.
            pass

    # 7. Write scratch.c — fully self-contained.  Types, externs,
    # and prototypes the function references are inlined at the top so
    # the agent never has to read the project's 100KB headers to find
    # a struct definition or a callee signature.
    note = (
        f"/* Function:  {function_name}\n"
        f" * Toolchain: {project.toolchain_spec.name}    "
        f"{project.toolchain_spec.cc} {' '.join(project.toolchain_spec.cflags)}\n"
        f" * Target:    {len(norm.bytes_)} bytes"
    )
    if norm.donor_name:
        note += (
            f"  (tail-merge-normalized: +{norm.donor_tail_size} bytes "
            f"from `{norm.donor_name}` donor)"
        )
    if norm.fallthrough_callee:
        note += (
            f"  (fall-through-normalized: +{norm.fallthrough_added_bytes} bytes "
            f"— PS fell through into `{norm.fallthrough_callee}`)"
        )
    note += (
        "\n *\n"
        " * Self-contained: every type, extern, and prototype the function\n"
        " * needs is inlined below.  If you add a NEW call or global to the\n"
        " * body, the compile will tell you what's missing — add the\n"
        " * declaration here yourself.\n"
        " *\n"
        " * Edit the function body below.  Run verify() to check progress.\n"
        " */\n"
    )

    from c2_ext.bundle import (
        build_symbol_table, merge_symbol_tables, render_bundled_scratch,
        tu_local_symbols,
    )
    symbols = build_symbol_table(str(project.headers_dir))
    # If the original TU has supplementary declarations that aren't in
    # the project headers (e.g. inline forward-declarations for
    # ``__far`` / ``__interrupt`` functions the header generator can't
    # represent), pick them up so the bundler can inline them too.
    if src_file_name:
        tu_path = project.sources_dir / src_file_name
        if tu_path.is_file():
            tu_syms = tu_local_symbols(tu_path.read_text(), src_file_name)
            symbols = merge_symbol_tables(symbols, tu_syms)

    # Tail-merge donor inclusion.  If the target function ends in a
    # ``jmp donor+N`` that the verifier normalises by splicing the
    # donor's shared tail, we ALSO want the donor's body present in
    # the same .obj so the standalone-TU compile can reproduce the
    # ComTail merge that PS's full-TU build performed.  Without this,
    # the recompile inlines its own ``call+ret`` epilogue and diverges
    # in the last 5-10 bytes — a residue no per-function source edit
    # can fix.  Inclusion only feeds the linker; the verifier still
    # extracts ONLY ``function_name``'s bytes for byte-comparison.
    additional_functions: list[tuple[str, str]] = []
    if norm.donor_name:
        donor_src = tc.existing_source(norm.donor_name)
        if donor_src is not None:
            _donor_file, donor_body = donor_src
            additional_functions.append((norm.donor_name, donor_body))
            note = note.rstrip("*/\n") + (
                f"\n * Tail-merge donor `{norm.donor_name}` body is included\n"
                " * below so wcc386 + wlink can reproduce PS's ComTail merge\n"
                " * of the shared epilogue.\n"
                " */\n"
            )

    scratch_text = render_bundled_scratch(
        header_comment=note,
        function_text=body_text,
        function_name=function_name,
        symbols=symbols,
        extra_includes=system_includes,
        additional_functions=additional_functions,
    )
    (out_dir / "scratch.c").write_text(scratch_text)

    # 10. Pre-render info.md so the agent starts with structural context
    try:
        from c2_ext.info import info as build_info, render_info_md
        fi = build_info(project, function_name)
        (out_dir / "info.md").write_text(render_info_md(fi))
    except Exception:
        # Info is a convenience; don't fail compose if it can't render
        (out_dir / "info.md").write_text(
            f"# {function_name}\n\n(info brief unavailable; use the `info` tool)\n"
        )

    # 11. Write meta.json
    meta = RunMeta(
        function=function_name,
        address_hex=f"0x{info.address:x}",
        target_size=len(norm.bytes_),
        raw_target_size=norm.raw_dependent_size,
        toolchain=project.toolchain_spec.name,
        target=project.active_target,
        cflags=project.toolchain_spec.cflags,
        source_file=info.source_file,
        signature=info.signature,
        line_marks=norm.line_marks,
        tail_merge_donor=norm.donor_name,
        tail_merge_boundary=norm.donor_boundary,
        tail_merge_donor_first_line=norm.donor_first_line,
        started_at=time.time(),
        body_origin=body_origin,
        project_root=str(project.root),
    )
    (out_dir / "meta.json").write_text(json.dumps(meta.to_dict(), indent=2))

    return out_dir


#  harvest


def harvest(run_dir: Path) -> dict:
    """Read back a run dir's outputs after the agent has finished.

    Returns ``{"function": ..., "scratch": <text>, "meta": <dict>, "exists": True}``
    """
    run_dir = run_dir.resolve()
    scratch = run_dir / "scratch.c"
    meta_path = run_dir / "meta.json"
    if not scratch.is_file() or not meta_path.is_file():
        return {"exists": False, "run_dir": str(run_dir)}
    meta = json.loads(meta_path.read_text())
    return {
        "exists": True,
        "run_dir": str(run_dir),
        "function": meta["function"],
        "meta": meta,
        "scratch": scratch.read_text(),
    }


#  helpers


def _slug(name: str) -> str:
    """Filesystem-safe slug for a function name."""
    s = unicodedata.normalize("NFKD", name)
    s = "".join(c if c.isalnum() or c in "-_." else "_" for c in s)
    return s or "fn"


def _blank_body(name: str, signature: str | None) -> str:
    """Construct an empty-body placeholder for ``name``."""
    sig = signature or f"void {name}(void)"
    return f"{sig}\n{{\n    /* TODO */\n}}\n"


def load_meta(run_dir: Path) -> RunMeta:
    """Load ``meta.json`` from a run dir as a :class:`RunMeta`."""
    return RunMeta.from_dict(
        json.loads((Path(run_dir) / "meta.json").read_text())
    )

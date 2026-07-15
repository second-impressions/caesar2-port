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

from c2.decompile._engine.bundle import (
    _find_function_span, _find_header_block_end, _scan_tu_function_spans,
)
from c2.decompile._engine.normalize import statics as statics_check
from c2.decompile._engine.project import ProjectConfig
from c2.decompile._engine.toolchains.base import NormalizedTarget, Toolchain


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
        " * Compose: split-TU.  scratch.c is laid out as:\n"
        " *\n"
        " *     1. this comment\n"
        " *     2. the source TU's HEADER BLOCK inlined verbatim --\n"
        " *        every #include, #pragma, typedef, extern decl,\n"
        " *        and file-scope static / global variable, in the\n"
        " *        original source order.  This is the TU's contract;\n"
        " *        you can read it right here.\n"
        " *     3. #include \"tu-body.c\"  -- sibling defs BEFORE target\n"
        " *     4. the target function body -- where most edits land\n"
        " *     5. #include \"tu-post.c\" -- sibling defs AFTER target\n"
        " *\n"
        " * The two sibling-bodies files are pulled in by the\n"
        " * preprocessor so wcc386 sees the FULL TU and produces byte-\n"
        " * equivalent output to the real-project build.  They are\n"
        " * LARGE (often hundreds of KB); do NOT load them in full --\n"
        " * use search() or read(offset/limit) for targeted lookups.\n"
        " *\n"
        " * Typical edits modify the function body in (4); editing the\n"
        " * header block (2) is fine when it's actually required (a\n"
        " * missing prototype, wrong extern type, etc.) -- just keep\n"
        " * those edits minimal and re-verify.  Run verify() to check\n"
        " * progress.\n"
        " */\n"
    )

    # ---- Three-file include-split compose:
    #
    #   tu-pre.c    -- the source TU's HEADER BLOCK (everything before
    #                  the first function definition: includes, pragmas,
    #                  typedefs, extern decls, file-scope statics).
    #                  This is the small file the agent is encouraged
    #                  to read freely -- it is the TU's contract.
    #   tu-body.c   -- function definitions BEFORE the target.
    #   target body -- inlined directly into scratch.c.
    #   tu-post.c   -- function definitions AFTER the target.
    #
    # scratch.c chains them with #include directives so the preprocessor
    # reassembles the full TU before wcc386 sees it.  Compile-equivalent
    # to the real-project build; agent-readable surface is the lean
    # scratch.c + the small tu-pre.c.
    #
    # This requires that every TU's declarations live BEFORE the first
    # function definition (no mid-file extern decls).  Audited and
    # hoisted in commit 1ac8dfc5; tu-pre.c then carries the FULL
    # declaration surface.
    if src_file_name:
        tu_path = project.sources_dir / src_file_name
    else:
        tu_path = None

    composed_via_split = False
    if tu_path is not None and tu_path.is_file():
        tu_text = tu_path.read_text()
        # ONE pycparser scan; reuse for both the function span and the
        # header-block end (parsing a 250KB TU twice was costing ~1s
        # per workspace at corpus scale).
        spans = _scan_tu_function_spans(tu_text)
        span = spans.get(function_name, (None,))[0] if spans else None
        header_end = _find_header_block_end(tu_text, spans=spans)
        if span is not None and header_end is not None:
            pre_header = tu_text[:header_end]
            pre_body = tu_text[header_end:span[0]]
            body = tu_text[span[0]:span[1]]
            post_body = tu_text[span[1]:]
            # tu-pre.c content is INLINED into scratch.c (no separate
            # file).  The agent sees the TU's contract right at the top
            # of the file they're editing -- one less hop to learn what
            # prototypes / globals are available.
            (out_dir / "tu-body.c").write_text(pre_body)
            (out_dir / "tu-post.c").write_text(post_body)
            scratch_text = (
                note
                + "\n"
                + pre_header.rstrip() + "\n\n"
                + '#include "tu-body.c"\n\n'
                + body
                + '\n#include "tu-post.c"\n'
            )
            (out_dir / "scratch.c").write_text(scratch_text)
            composed_via_split = True

    if not composed_via_split:
        # Fallback for functions with no project .c file (orphans /
        # pure stubs): synthesise a minimal self-contained scratch.c
        # via the legacy bundler so verify still has something to
        # build.
        from c2.decompile._engine.bundle import (
            build_symbol_table, render_bundled_scratch,
        )
        symbols = build_symbol_table(str(project.headers_dir))
        scratch_text = render_bundled_scratch(
            header_comment=note,
            function_text=body_text,
            function_name=function_name,
            symbols=symbols,
            extra_includes=system_includes,
            additional_functions=[],
            pragma_lines=[],
        )
        (out_dir / "scratch.c").write_text(scratch_text)

    # Copy project headers into the run dir so ``#include "foo.h"`` in
    # the stripped TU resolves to the project's real headers.  Watcom's
    # warm container mounts ``out_dir`` at ``/src`` and looks for
    # includes there.
    if project.headers_dir.is_dir():
        for h in project.headers_dir.glob("*.h"):
            try:
                (out_dir / h.name).write_bytes(h.read_bytes())
            except OSError:
                pass

    # 10. Pre-render info.md so the agent starts with structural context
    try:
        from c2.decompile._engine.info import info as build_info, render_info_md
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

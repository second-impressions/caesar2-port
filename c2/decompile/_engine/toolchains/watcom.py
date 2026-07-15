"""Watcom 10.0a toolchain implementation.

Delegates to the existing :mod:`c2` toolkit for the heavy lifting:

* ``c2.commands.tail_merge._load_symbols`` for the symbol DB
* ``c2.commands.decomp_verify._load_le_code_and_fixups`` for the target
  binary's code section + fixup map
* ``c2.parsers.omf.parse_obj_functions`` for parsing the freshly
  compiled ``.obj``

What this module *adds*:

* A self-contained standalone-TU compile (no podman/dosemu container —
  native ``wcc386`` works fine for one TU)
* C-source body extraction from ``decomp/src/<file>.c`` via a simple
  brace matcher
* Symbol-resolved disassembly via capstone + the c2 symbol DB
* A normalizer that strips Ghidra/operand noise for embedding clustering
* A byte-exact pool read from ``.c2-cache/verify.json``
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import re
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING

import capstone

from c2.decompile._engine.toolchains.base import (
    CompileResult,
    FunctionInfo,
    Insn,
    NormalizedTarget,
    Toolchain,
    register,
)

if TYPE_CHECKING:
    from c2.decompile._engine.project import ProjectConfig


def _run_in_warm_container(
    warm_name: str,
    command: str,
    *,
    timeout: int = 120,
) -> tuple[bool, str]:
    """Concurrent-safe ``podman exec`` into one agent's warm container.

    Mirrors the wibo-wrapper protocol used by
    :func:`c2.commands.decomp_verify._run_in_container`'s warm path but
    takes the container name as an argument rather than a module global,
    so two ``c2 decompile`` agents running in parallel never race on the
    same exec slot.
    """
    import shlex
    cmd = [
        "podman", "exec", warm_name,
        "/usr/local/bin/watcom", *shlex.split(command),
    ]
    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=timeout,
    )
    combined = result.stdout + "\n" + result.stderr
    filtered = "\n".join(
        ln for ln in combined.splitlines()
        if not any(skip in ln for skip in (
            "Running dosemu2", "recommended with",
            "dosemu -s", "DOSEMU",
        ))
    ).strip()
    return result.returncode == 0, filtered


@register("watcom-10.0a")
class WatcomToolchain(Toolchain):
    """Watcom C/C++ 10.0a, targeting DOS/4GW LE executables."""

    #  Caches (built once per instance)

    @cached_property
    def _sym_ctx(self):
        from c2.commands.tail_merge import _load_symbols
        return _load_symbols(self.project.symbols_json)

    @cached_property
    def _ps_code_and_fixups(self) -> tuple[bytes, frozenset[int]]:
        from c2.commands.decomp_verify import _load_le_code_and_fixups
        code, fix = _load_le_code_and_fixups(self.project.target_binary)
        return code, frozenset(fix)

    @cached_property
    def _ps_le_fixup_map(self) -> dict[int, tuple[int, int]]:
        """Code-segment fixup map: byte_off_in_code -> (tgt_obj_idx, tgt_off_in_obj).

        Lets us resolve data references inside instructions back to the
        symbolic name that the linker would have patched in at load time.
        """
        from c2.commands.fixups import parse_le_fixups
        from c2.parsers.exe import parse_exe
        _, _bw, le = parse_exe(self.project.target_binary)
        code_fix, _data_fix = parse_le_fixups(
            self.project.target_binary,
            le.le_offset,
            le.page_size,
            le.num_pages,
            le.objects[0].num_pages,
            le.objects[1].num_pages,
        )
        return code_fix

    @cached_property
    def _le_bases(self) -> tuple[int, int]:
        """(code_base, data_base) virtual addresses for the two LE objects."""
        raw = json.loads(self.project.symbols_json.read_text())
        objs = raw["memory_map"]["objects"]
        return objs[0]["base_address_int"], objs[1]["base_address_int"]

    @cached_property
    def _line_numbers_by_addr(self) -> dict[int, list[tuple[int, int, str]]]:
        """address → list of (offset_within_code, line, source_file)."""
        raw = json.loads(self.project.symbols_json.read_text())
        # Cluster line marks by which function range they belong to.
        # Use address (vaddr) as the join key; the func_ranges table is sorted.
        out: dict[int, list[tuple[int, int, str]]] = {}
        for ln in raw["line_numbers"]:
            addr = ln["address"]
            fn = self._function_at(addr)
            if fn is None:
                continue
            _, start, _end = fn
            out.setdefault(start, []).append((addr - start, ln["line"], ln["file"]))
        # Sort marks within each function by offset.
        for marks in out.values():
            marks.sort()
        return out

    @cached_property
    def _byte_exact_pool(self) -> frozenset[str]:
        cache = self.project.root / ".c2-cache" / "verify.json"
        if not cache.is_file():
            return frozenset()
        try:
            data = json.loads(cache.read_text())
        except (json.JSONDecodeError, OSError):
            return frozenset()
        return frozenset(f["name"] for f in data.get("functions", []) if f.get("exact"))

    @cached_property
    def _sources_by_basename(self) -> dict[str, Path]:
        """basename.c → absolute path."""
        out: dict[str, Path] = {}
        for src in self.project.sources_dir.glob("*.c"):
            out[src.name] = src
        return out

    #  Symbol helpers

    def _function_at(self, vaddr: int) -> tuple[str, int, int] | None:
        from c2.commands.tail_merge import _function_at
        return _function_at(self._sym_ctx, vaddr)

    #  Toolchain interface

    def function_info(self, name: str) -> FunctionInfo:
        addr = self._sym_ctx.name_to_addr.get(name)
        if addr is None:
            raise KeyError(f"function {name!r} not in symbols.json")
        # Find size from func_ranges (sorted by start).
        info = self._function_at(addr)
        if info is None:
            raise KeyError(f"function {name!r} has no code range")
        _name, start, end = info
        size = end - start
        # Trim trailing alignment padding (0x90 / 0xcc) — pragmatic guess; the
        # corpus shows Watcom doesn't right-pad past the next function's start,
        # but `end_exclusive` from the symbol DB just uses the next symbol's
        # start, so trim trailing 0x90 NOPs we recognise as padding.
        ps_code, _fix = self._ps_code_and_fixups
        off = addr - self._sym_ctx.code_base
        body = ps_code[off : off + size]
        # Trim only obvious trailing 0x90 padding (single NOPs); keep 0xcc
        # since Watcom uses it less predictably.
        while size > 1 and body[size - 1] == 0x90:
            size -= 1

        # Find source file from line marks
        marks = self._line_numbers_by_addr.get(start, [])
        source_file = marks[0][2] if marks else None

        # Signature: try lifting from existing source
        sig = None
        existing = self.existing_source(name)
        if existing:
            _, body_text = existing
            sig = _extract_signature(body_text)

        return FunctionInfo(
            name=name, address=addr, size=size,
            source_file=source_file, signature=sig,
        )

    def function_bytes(self, name: str) -> bytes:
        info = self.function_info(name)
        ps_code, _ = self._ps_code_and_fixups
        off = info.address - self._sym_ctx.code_base
        return ps_code[off : off + info.size]

    def function_fixups(self, name: str) -> frozenset[int]:
        info = self.function_info(name)
        _ps_code, fix = self._ps_code_and_fixups
        off = info.address - self._sym_ctx.code_base
        return frozenset(o - off for o in fix if off <= o < off + info.size)

    def line_numbers(self, name: str) -> tuple[tuple[int, int], ...]:
        info = self.function_info(name)
        marks = self._line_numbers_by_addr.get(info.address, [])
        # Return (offset, line) tuples — drop the file column (single-TU here).
        return tuple((off, line) for off, line, _file in marks)

    def resolve_data_ref(self, addr: int) -> tuple[str, int] | None:
        """Resolve a data address to (name, displacement).

        Caesar2 data lives at base 0x90000; symbols.json carries every named
        global with its full address.  For sub-field accesses we pick the
        NEAREST named symbol within a sane window \u2014 either preceding
        (positive displacement, e.g. ``foo+0xC``) or following (negative
        displacement, e.g. ``foo-3``).  Negative displacements arise from
        pointer-arithmetic patterns the compiler folds into the
        instruction displacement, e.g.
        ``(*(struct cell*)(base + (idx - 4))).figure_at_+1`` becomes
        ``[base - 3 + idx]`` at the asm level.
        """
        sym = self._sym_ctx
        # Direct hit
        if addr in sym.addr_to_name:
            return sym.addr_to_name[addr], 0
        idx, names = self._data_index
        import bisect
        pos = bisect.bisect_right(idx, addr) - 1
        WINDOW = 0x4000  # 16 KiB sub-field window (sane upper bound)
        candidates: list[tuple[int, str, int]] = []  # (abs_delta, name, signed_delta)
        if pos >= 0:
            d = addr - idx[pos]
            if 0 <= d <= WINDOW:
                candidates.append((d, names[pos], d))
        next_pos = pos + 1
        if 0 <= next_pos < len(idx):
            d = idx[next_pos] - addr   # how far BEFORE the next symbol we are
            if 0 < d <= 0x100:         # negative-displacement window: 256 B
                candidates.append((d, names[next_pos], -d))
        if not candidates:
            return None
        candidates.sort()
        _, name, signed_delta = candidates[0]
        return name, signed_delta

    @cached_property
    def _data_index(self) -> tuple[list[int], list[str]]:
        raw = json.loads(self.project.symbols_json.read_text())
        data_syms = sorted(
            ((s["address"], s["name"]) for s in raw["symbols"] if not s.get("is_code")),
            key=lambda p: p[0],
        )
        if not data_syms:
            return [], []
        idxs, names = zip(*data_syms)
        return list(idxs), list(names)

    def resolve_code_ref(self, addr: int) -> tuple[str, int] | None:
        fn = self._function_at(addr)
        if fn is None:
            return None
        name, start, _end = fn
        return name, addr - start

    def existing_source(self, name: str) -> tuple[str, str] | None:
        """Lift ``name``'s function definition from its source file via brace matching.

        Strips project-bookkeeping leading comments from the function body
        (residue/parked/floor/CLASSIFIED claims etc.) \u2014 those reflect prior
        sessions' verdicts and would mislead a fresh agent.  Per the project's
        Hard Rule #6, such comments are unreliable.

        Two lookup paths:
        1. Primary: walk ``_line_numbers_by_addr`` (PS.EXE ``-d1`` debug
           info) -> ``source_file_name``.  Works for every function that
           has its own line-number record in PS.EXE.
        2. Fallback (for tail-merged dependents like ``clear_unit`` whose
           line-number record was merged into the donor's address): brute-
           force search every project ``.c`` file for the function's
           definition.  Without this fallback the bundler emits a
           ``/* TODO */`` stub body for these functions and the standalone
           compile produces wildly different bytes than the real-TU build.
        """
        info_lines = self._line_numbers_by_addr.get(
            self._sym_ctx.name_to_addr.get(name, -1), []
        )
        source_file_name = info_lines[0][2] if info_lines else None
        src_path = (
            self._sources_by_basename.get(source_file_name)
            if source_file_name else None
        )
        if src_path is not None:
            text = src_path.read_text()
            body = _extract_function_body(text, name)
            if body is not None:
                return source_file_name, _strip_leading_body_comments(body)
        # Fallback: brute-force scan every project .c file.
        for basename, candidate in self._sources_by_basename.items():
            text = candidate.read_text()
            body = _extract_function_body(text, name)
            if body is not None:
                return basename, _strip_leading_body_comments(body)
        return None

    def source_includes(self, source_file_name: str) -> list[str]:
        """Return the original TU's ``#include`` lines (system + project)
        so the scratch can replicate them verbatim.
        """
        src_path = self._sources_by_basename.get(source_file_name)
        if src_path is None:
            return []
        out: list[str] = []
        for line in src_path.read_text().splitlines():
            s = line.strip()
            if s.startswith("#include"):
                out.append(s)
            elif s and not s.startswith("//") and not s.startswith("/*") \
                    and not s.startswith("*") and not s.startswith("#"):
                # First non-include non-comment non-cpp line: stop scanning.
                break
        return out

    # File-scope ``#pragma`` directives in effect at a function's
    # source line.  Watcom honours pragmas like
    # ``on(check_stack)`` / ``off(check_stack)`` (toggle the
    # prologue ``call __CHK`` insertion) and
    # ``aux _ds "*"`` (reserve a register globally) at file scope
    # CUMULATIVELY -- every function defined BELOW the pragma in
    # the source picks up the new setting.  The bundler's
    # scratch.c only carries the function body, so without
    # pragma propagation the standalone compile sees a DIFFERENT
    # toolchain configuration than the real-TU build -- e.g.
    # lib32.c:1591 ``#pragma on(check_stack)`` affects every
    # function below it; ``to_upper`` (line 2139) gets the
    # ``push 8; call __CHK`` prologue in PS but not standalone.
    _PRAGMA_LINE_RE = re.compile(r"^\s*#\s*pragma\b[^\n]*$", re.MULTILINE)

    def pragmas_before(self, source_file_name: str, function_name: str) -> list[str]:
        """Return ``#pragma`` lines from ``source_file_name`` that
        appear BEFORE ``function_name``'s definition.

        Returns ``[]`` if either the file or the function can't be
        located.  Lines are returned in source order so cumulative
        toggles (``off`` then ``on``) replay correctly.
        """
        src_path = self._sources_by_basename.get(source_file_name)
        if src_path is None:
            return []
        text = src_path.read_text()
        span = _find_function_span(text, function_name)
        if span is None:
            return []
        cutoff = span[0]
        return [
            m.group(0).strip()
            for m in self._PRAGMA_LINE_RE.finditer(text, 0, cutoff)
        ]

    # Tail-merge DEPENDENTS: functions that have ``name`` as their
    # donor.  Symmetric to the existing donor-of-X lookup in
    # ``compose``.  When PS's wcc386 emits ``clear_army`` it
    # ComTail-merges ``clear_unit``'s tail into the same byte
    # range, and the verifier extracts ``clear_army``'s full byte
    # range (which INCLUDES ``clear_unit``'s tail).  The standalone
    # compile must therefore also have ``clear_unit`` present so
    # wcc386 can reproduce the merged form.
    #
    # The reverse map is built lazily on first call by scanning
    # every function's bytes for a tail-merge donor; cached after
    # that.
    def tail_merge_dependents(self, name: str) -> list[str]:
        """Return the names of functions whose tail-merge donor is ``name``.

        Slow on first call (scans every PS function); cached.
        """
        if self._tm_dependents_cache is None:
            self._build_tm_dependents_cache()
        return list(self._tm_dependents_cache.get(name, ()))  # type: ignore[union-attr]

    # On-disk cache path for the donor->[dependents] map.  Avoids
    # rescanning every PS.EXE function (~7000 entries, ~5-10s) on every
    # fresh process.  Invalidated by PS.EXE mtime so a swapped binary
    # forces a rebuild.
    @staticmethod
    def _tm_dependents_cache_path(project) -> Path:
        return project.root / ".c2-cache" / "tail-merge-dependents.json"

    def _build_tm_dependents_cache(self) -> None:
        from c2.commands.tail_merge import scan_tail_merge_donor
        cache_path = self._tm_dependents_cache_path(self.project)
        exe = self.project.root / "data" / "PS.EXE"
        exe_mtime = exe.stat().st_mtime if exe.exists() else 0.0

        # Load from disk if fresh.
        if cache_path.exists():
            try:
                blob = json.loads(cache_path.read_text())
                if blob.get("exe_mtime") == exe_mtime:
                    self._tm_dependents_cache = {
                        k: list(v) for k, v in blob.get("map", {}).items()
                    }
                    return
            except (json.JSONDecodeError, OSError):
                pass

        cache: dict[str, list[str]] = {}
        for fn_name, addr in self._sym_ctx.name_to_addr.items():
            try:
                fn_bytes = self.function_bytes(fn_name)
            except (KeyError, ValueError):
                continue
            if not fn_bytes:
                continue
            hint = scan_tail_merge_donor(
                fn_bytes, addr,
                symbols_json=(
                    self.project.root / "data" / "out" / "symbols.json"
                ),
            )
            if hint and hint.donor_name and hint.donor_name != fn_name:
                cache.setdefault(hint.donor_name, []).append(fn_name)
        self._tm_dependents_cache = cache

        # Persist for next process.  Best-effort -- a write failure (e.g.
        # parallel writers racing) is silently swallowed; the next process
        # will just rebuild.
        try:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(json.dumps(
                {"exe_mtime": exe_mtime, "map": cache}, indent=2,
            ))
        except OSError:
            pass

    #  Compilation via wibo container (same path as decomp-verify)
    #
    # The native Nix-packaged wcc386 is byte-divergent from the
    # canonical 10.0a build under wibo in subtle ways; for byte
    # equivalence we use the exact same image (`localhost/watcom-
    # 10.0a-wibo`) the project uses for `c2 decomp-verify`.  See
    # `c2.commands.decomp_verify._run_in_container` for the
    # container conventions.
    #
    # Per-run-dir warm container: we lazy-start one sleep-forever
    # container per run dir on the first compile, reuse it for every
    # subsequent compile in that run, and the orchestrator is
    # expected to call :meth:`stop_warm_container` (or just let
    # podman reap on parent exit) when the run ends.  This brings
    # per-compile cost from ~300 ms (fresh `podman run`) to ~50 ms
    # (`podman exec` into a warm container), matching
    # `decomp-verify`'s warm-exec performance profile.

    _warm_containers: "dict[str, str]" = {}

    # Lazy-built reverse map for tail-merge dependents: donor name
    # -> [dependent fn names].  ``None`` until first access.  Stored
    # as a class attribute (process-global) -- the underlying scan
    # walks PS.EXE symbols + bytes which are immutable for the life
    # of the process; sharing the cache across toolchains is safe.
    _tm_dependents_cache: "dict[str, list[str]] | None" = None

    @property
    def _wibo_image(self) -> str:
        # Project config wins over env var wins over a hardcoded default —
        # so a user with a custom image name can switch via either.
        if self.project.toolchain_spec.compiler_image:
            return self.project.toolchain_spec.compiler_image
        return os.environ.get("C2_VERIFY_IMAGE", "localhost/watcom-10.0a-wibo")

    def _ensure_warm_container(self, run_dir: Path) -> str:
        """Return a warm container name for ``run_dir``; start one if needed."""
        key = str(run_dir.resolve())
        name = WatcomToolchain._warm_containers.get(key)
        if name is not None:
            # Verify still running
            ck = subprocess.run(
                ["podman", "container", "exists", name],
                capture_output=True, timeout=10,
            )
            if ck.returncode == 0:
                return name
            # Stale, fall through to start a fresh one
            WatcomToolchain._warm_containers.pop(key, None)
        from c2.commands.decomp_verify import start_warm_container
        name = start_warm_container(run_dir, self._wibo_image)
        WatcomToolchain._warm_containers[key] = name
        return name

    def stop_warm_container(self, run_dir: Path) -> None:
        """Force-stop the warm container associated with ``run_dir``."""
        key = str(run_dir.resolve())
        name = WatcomToolchain._warm_containers.pop(key, None)
        if name is None:
            return
        from c2.commands.decomp_verify import stop_warm_container
        stop_warm_container(name)

    def compile_scratch(self, run_dir: Path, function_name: str) -> CompileResult:
        """Compile ``run_dir/scratch.c`` as a standalone TU.

        The agent's scratch is its OWN file in its own world; we never
        splice it into the project source tree.  Trade-off: Watcom's
        output for the function may differ from the real-TU compile when
        sibling functions in the original .c file influenced regalloc /
        scheduling decisions.  The verify oracle's ground truth is still
        PS.EXE's bytes; standalone-exact + real-TU-diff means the agent's
        SOURCE happens to standalone-match PS even though it isn't
        semantically equivalent in the real-TU context.  We accept this
        coherence-vs-precision trade because the agent's mental model
        ("edits to scratch.c → changes to compile output") stays sound.
        """
        scratch = run_dir / "scratch.c"
        if not scratch.is_file():
            return CompileResult(ok=False, stderr=f"scratch.c not found at {scratch}",
                                 function_bytes=None, fixup_offsets=frozenset())

        warm = self._ensure_warm_container(run_dir)
        # meta carries source_file (the TU basename), needed to skip the
        # target's own .obj when staging the LE link (scratch.obj stands
        # in for it).
        from c2.decompile._engine.runs import load_meta
        meta = load_meta(run_dir)
        cflags = " ".join(self.cflags)
        # scratch.c is fully self-contained (bundler inlines project decls).
        # No `-i=` flag: Watcom system headers come from the container image's
        # default INCLUDE path.
        cmd = f"wcc386 {cflags} -fo=scratch.obj scratch.c"

        # Concurrent-safe warm-container exec: bypass
        # ``c2.commands.decomp_verify._EXEC_CONTAINER`` (a module-level
        # global that races between parallel agents) and dispatch
        # straight to ``podman exec <warm>`` using the per-run container
        # we started above.  Each agent has its own warm container
        # keyed on its run_dir, so this path is fully independent
        # across parallel ``c2 decompile`` workers.
        try:
            ok, output = _run_in_warm_container(warm, cmd, timeout=120)
        except subprocess.TimeoutExpired:
            return CompileResult(
                ok=False, stderr="compiler timeout (120s)",
                function_bytes=None, fixup_offsets=frozenset(),
            )

        if not ok:
            return CompileResult(
                ok=False, stderr=output,
                function_bytes=None, fixup_offsets=frozenset(),
            )

        obj_path = run_dir / "scratch.obj"
        if not obj_path.is_file():
            return CompileResult(
                ok=False, stderr=f"compiler returned 0 but no .obj produced\n{output}",
                function_bytes=None, fixup_offsets=frozenset(),
            )

        # Pull the function's name + length + scratch.c-relative line
        # marks straight out of the freshly-compiled OMF .obj.  These
        # line marks are what the LE linker carries into out.exe too
        # (it does not rewrite scratch.c line numbers), so they stay
        # valid for the L+N columns after the carve below.
        from c2.parsers.omf import parse_obj_functions
        funcs = parse_obj_functions(obj_path)
        mangled = function_name + "_"
        match_idx = next(
            (i for i, f in enumerate(funcs) if f[0] == mangled or f[0] == function_name),
            None,
        )
        if match_idx is None:
            names = ", ".join(f[0] for f in funcs[:20])
            return CompileResult(
                ok=False,
                stderr=f"function {function_name!r} not found in obj.\n"
                       f"Have: {names}\n{output}",
                function_bytes=None, fixup_offsets=frozenset(),
            )
        scratch_name, scratch_code_bytes, _scratch_fixup_set = funcs[match_idx]
        scratch_fn_len = len(scratch_code_bytes)
        text_off = sum(len(funcs[i][1]) for i in range(match_idx))
        from c2.decompile._engine.parsers.omf_lines import function_line_map
        try:
            line_marks = function_line_map(obj_path, text_off, scratch_fn_len)
        except Exception:
            line_marks = ()

        # Link scratch.obj against the verifier's staged sibling .objs
        # and carve the function from the resulting LE binary.  This is
        # the SAME path the verifier (c2 decomp-verify) and forge
        # mode="le" use, so our bytes + reloc mask match the real-TU
        # oracle byte-for-byte.  The standalone OMF carve above only
        # gave us line_marks; the byte/fixup truth comes from the link.
        source_file = (getattr(meta, "source_file", None) or "")
        le = self._wlink_and_carve_le(
            run_dir=run_dir, warm=warm,
            function_name=function_name, source_file=source_file,
            fallback_code=bytes(scratch_code_bytes),
            build_output=output,
        )
        if le is None:
            # LE path unavailable (no .c2-cache/build/, or wlink
            # failed).  Fall back to the standalone OMF bytes rather
            # than abort the whole verify -- the agent still gets a
            # (less accurate) number.  Marked via stderr note.
            scratch_fix = frozenset(_scratch_fixup_set)
            return CompileResult(
                ok=True,
                stderr=(output.strip() +
                        "\n[LE link unavailable; fell back to OMF carve -- "
                        "byte_diff may be over-counted]"),
                function_bytes=bytes(scratch_code_bytes),
                fixup_offsets=scratch_fix,
                line_marks=line_marks,
            )
        le_code, le_fixups, le_note = le
        return CompileResult(
            ok=True, stderr=(output.strip() + le_note),
            function_bytes=le_code, fixup_offsets=le_fixups,
            line_marks=line_marks,
        )


    # --- LE link + carve (matches the verifier's byte oracle) ------------

    # Mirror of c2.forge.build.ForgeBuilder's LE path: stage the
    # verifier's sibling .objs, wlink scratch.obj against them, then
    # carve the function from out.exe.  Lets the sandbox verify see
    # the SAME bytes the real-TU c2 decomp-verify sees (links resolve
    # relocations the standalone OMF carve leaves as placeholders, so
    # the reloc-mask no longer over-counts byte_diff on cross-module
    # functions).
    _VERIFIER_BUILD_DIR = Path(".c2-cache/build")

    def _wlink_and_carve_le(
        self, *, run_dir: Path, warm: str,
        function_name: str, source_file: str | None,
        fallback_code: bytes, build_output: str,
    ) -> tuple[bytes, frozenset[int], str] | None:
        """Link scratch.obj against .c2-cache/build/*.obj and carve
        ``function_name`` from the linked LE.  Returns (code, fixups,
        stderr-note) or None to signal the caller to fall back to the
        OMF bytes.
        """
        if not self._VERIFIER_BUILD_DIR.is_dir():
            return None
        friend_objs = sorted(self._VERIFIER_BUILD_DIR.glob("*.obj"))
        if not friend_objs:
            return None
        # scratch.obj defines EVERY function in the target TU (it's the
        # standalone compile of the whole .c), so it replaces the build
        # dir's copy of that TU's .obj.  Drop the matching friend so the
        # linker doesn't see two definitions.
        target_stem = (source_file or "").removesuffix(".c")
        friends = [o for o in friend_objs if o.stem != target_stem]

        # Stage siblings into run_dir (hard-link, else copy).  scratch.obj
        # is already there (compiled above) -- it goes FIRST in the link
        # line so its definition of the target wins over any leftover.
        staged: list[str] = ["scratch.obj"]
        for obj in friends:
            dst = run_dir / obj.name
            src = obj.resolve()
            try:
                # If an earlier verify in this same work_dir already
                # staged this friend, and it still points at the current
                # source inode, reuse it.  If it is STALE (the verifier
                # rebuilt .c2-cache/build/*.obj under us, giving a new
                # inode) or a dangling link, drop it and re-stage.
                if dst.exists() or dst.is_symlink():
                    try:
                        if dst.exists() and dst.samefile(src):
                            staged.append(obj.name)
                            continue
                    except OSError:
                        pass
                    dst.unlink()
                dst.hardlink_to(src)
            except OSError:
                # Cross-device link (.c2-runs and .c2-cache on different
                # filesystems) or a lost race: fall back to a copy, but
                # NEVER copy a file onto itself (that raises
                # shutil.SameFileError and killed the agent).
                try:
                    if dst.exists() and dst.samefile(src):
                        staged.append(obj.name)
                        continue
                    if dst.exists() or dst.is_symlink():
                        dst.unlink()
                    shutil.copy2(src, dst)
                except (OSError, shutil.SameFileError):
                    # Last resort: if a same-named obj is already present
                    # (from any prior attempt), link against it as-is
                    # rather than aborting the whole verify.
                    if not dst.exists():
                        raise
            staged.append(obj.name)

        lnk = run_dir / "decompile.lnk"
        lines = [
            "DEBUG ALL\n",
            "FORMAT os2 le\n",
            "OPTION QUIET\n",
            "OPTION MAP=out.map\n",
            "NAME out.exe\n",
            "LIBPATH Z:\\opt\\watcom\\lib386;"
            "Z:\\opt\\watcom\\lib386\\dos\n",
            "LIBRARY clib3r.lib\n",
        ]
        for n in staged:
            lines.append(f"FILE {n}\n")
        lnk.write_text("".join(lines))

        import shlex
        cmd = [
            "podman", "exec", "--workdir", "/src", warm,
            "/usr/local/bin/watcom", "wlink", "@decompile.lnk",
        ]
        try:
            cp = subprocess.run(cmd, capture_output=True, text=True,
                                timeout=120)
        except subprocess.TimeoutExpired:
            return None
        out = (cp.stdout or "") + ((cp.stderr or "").strip()
                                   and ("\n" + cp.stderr) or "")
        out_exe = run_dir / "out.exe"
        if cp.returncode != 0 or "Error!" in out or not out_exe.exists():
            return None

        from c2.commands.decomp_verify import _load_le_code_and_fixups
        try:
            load = getattr(_load_le_code_and_fixups, "__wrapped__",
                           _load_le_code_and_fixups)
            if hasattr(_load_le_code_and_fixups, "__wrapped__"):
                code_full, fixups_abs = load(
                    str(out_exe), out_exe.stat().st_mtime_ns,
                    out_exe.stat().st_size,
                )
            else:
                code_full, fixups_abs = load(out_exe)
        except Exception:
            return None

        fn_off, fn_len = self._fn_offset_in_le(
            run_dir / "out.map", function_name)
        if fn_off is None:
            return None
        # Truncate to the function's real size.  The .map's next-symbol
        # offset (fn_len) INCLUDES inter-function linker padding; the
        # byte oracle compares against PS.EXE's symbol-table size, which
        # is the meaningful body length.  meta.target_size carries that
        # (the normalized target bytes length, = PS symbol size for
        # non-tail-merge functions).  Without this, trailing linker
        # padding leaks into the compare and inflates byte_diff.
        from c2.decompile._engine.runs import load_meta
        try:
            tmeta = load_meta(run_dir)
            cmp_len = int(getattr(tmeta, "raw_target_size", 0)
                          or getattr(tmeta, "target_size", 0) or 0)
        except Exception:
            cmp_len = 0
        if cmp_len <= 0:
            cmp_len = fn_len or 0x10000
        end = min(fn_off + cmp_len, len(code_full))
        code = bytes(code_full[fn_off:end])
        fixups = frozenset(f - fn_off for f in fixups_abs
                            if fn_off <= f < end)
        note = f"\n[LE-linked carve: out.exe {len(code_full)}b code @0x{fn_off:x}+{len(code)}]"
        return code, fixups, note

    @staticmethod
    def _fn_offset_in_le(map_path: Path, function: str
                        ) -> tuple[int | None, int | None]:
        """Parse out.map to find ``function``'s offset + size in the
        linked LE binary's _TEXT segment.  Offset is into the
        code-section bytes _load_le_code_and_fixups returns.
        """
        if not map_path.exists():
            return None, None
        candidates = (function + "_", function)
        ordered: list[tuple[str, int]] = []
        for line in map_path.read_text(errors="replace").splitlines():
            # The Watcom .map format: ``0001:HEXOFFSET[+*]?  symbol``.
            # ``+`` marks a library symbol's offset; ``*`` marks a
            # non-preferred (duplicate) definition -- both can trailing
            # the offset, so accept either before the required whitespace.
            m = re.match(
                r"\s*0001:([0-9a-fA-F]+)[+*]?\s+([A-Za-z_]\w*)", line)
            if m:
                ordered.append((m.group(2), int(m.group(1), 16)))
        if not ordered:
            return None, None
        ordered.sort(key=lambda x: x[1])
        for i, (name, off) in enumerate(ordered):
            if name in candidates:
                nxt = ordered[i + 1][1] if i + 1 < len(ordered) else None
                size = (nxt - off) if nxt is not None else None
                return off, size
        return None, None

    # Disassembly
    @cached_property
    def _cs(self) -> capstone.Cs:
        cs = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
        cs.detail = True
        return cs

    def disassemble(
        self, code: bytes, base_addr: int,
        fixup_offsets: frozenset[int] | None = None,
    ) -> list[Insn]:
        out: list[Insn] = []
        # Function bounds: always [base_addr, base_addr + len(code)) because
        # the caller passes the bytes they want disassembled.  Using PS.EXE's
        # symbol-table fn_end would mis-classify intra-function jumps in any
        # recompile whose size differs from the target's.
        fn_start = base_addr
        fn_end = base_addr + len(code)

        for ins in self._cs.disasm(code, base_addr):
            offset = ins.address - fn_start
            mnemonic = ins.mnemonic
            op_str = ins.op_str
            resolved = self._resolve_operands(ins, fn_start, fn_end)
            if resolved is not None:
                op_str = resolved

            # An instruction is a 'relocation' insn (its disp differs by
            # link-time positioning) if either:
            #   (a) it's a rel32/rel8 call/jmp/jcc whose displacement
            #       targets an address OUTSIDE the function (intra-fn
            #       branches resolve at assembly time and are NOT
            #       relocations -- conflating them lets the inverse-jcc
            #       relax accept `je`/`jne` flips at intra-fn jumps, a
            #       real shape error), or
            #   (b) any of its bytes is in the supplied fixup set.
            is_reloc = _is_reloc_insn(ins, fn_start, fn_end)
            if not is_reloc and fixup_offsets:
                for k in range(ins.size):
                    if (offset + k) in fixup_offsets:
                        is_reloc = True
                        break

            out.append(Insn(
                offset=offset,
                size=ins.size,
                line=None,
                is_donor=False,
                mnemonic=mnemonic,
                op_str=op_str,
                raw=bytes(ins.bytes),
                is_relocation=is_reloc,
            ))
        return out

    def _resolve_operands(
        self, ins: capstone.CsInsn, fn_start: int, fn_end: int,
    ) -> str | None:
        """Render instruction operands with code/data symbols resolved."""
        try:
            ops = list(ins.operands)
        except (AttributeError, capstone.CsError):
            return None

        code_base = self._le_bases[0]
        #  Calls / jumps with immediate target (rel32 / rel8)
        if ins.mnemonic in ("call", "jmp") or ins.mnemonic.startswith("j"):
            for op in ops:
                if op.type == capstone.x86.X86_OP_IMM:
                    target = op.value.imm
                    if fn_start <= target < fn_end:
                        return f".L_{target - fn_start:x}"
                    code_ref = self.resolve_code_ref(target)
                    if code_ref:
                        name, delta = code_ref
                        return name if delta == 0 else f"{name}+0x{delta:x}"
                    return None

        #  Memory operands: consult the LE fixup map for the real symbol
        fn_off_in_code = fn_start - code_base
        insn_off_in_code = ins.address - code_base
        for k in range(ins.size):
            rec = self._ps_le_fixup_map.get(insn_off_in_code + k)
            if rec is None:
                continue
            tgt_obj, tgt_off = rec
            if tgt_obj == 1:
                vaddr = code_base + tgt_off
                ref = self.resolve_code_ref(vaddr)
            else:
                vaddr = self._le_bases[1] + tgt_off
                ref = self.resolve_data_ref(vaddr)
            if ref is None:
                continue
            name, delta = ref
            symbolic = name if delta == 0 else f"{name}+0x{delta:x}"
            # Replace the raw displacement value in op_str.  The raw
            # encoded displacement is `tgt_off` (the segment-internal
            # offset), which capstone surfaces as a hex literal.
            return _replace_disp_in_op(ins.op_str, tgt_off, symbolic)
        return None

    #  Embedding noise stripper

    def normalize_asm_for_embedding(self, asm_text: str) -> str:
        """Strip x86/Watcom toolchain noise from disasm text so embeddings
        cluster by code semantics rather than format.

        Folds: hex-address prefixes, raw-byte columns, intra-function
        jump targets to ``.L``, data offsets to ``[DATA]``, immediate
        constants > 0xff to ``IMM``, and stack frame slots to ``[ESP]``.
        """
        out_lines: list[str] = []
        for line in asm_text.splitlines():
            s = line
            # Strip leading offset / line-number columns
            s = re.sub(r"^\s*[+D]?\+?\d+\s+", "", s)         # L+N / D+N column
            s = re.sub(r"^\s*[0-9a-fA-F]+\s+", "", s)        # offset column
            s = re.sub(r"^\s*([0-9a-fA-F]{2}\s)+\s+", "", s) # raw bytes column
            # Fold intra-function jumps
            s = re.sub(r"\.L_[0-9a-f]+", ".Lx", s)
            # Fold data displacements to [DATA] / [DATA+N] form
            s = re.sub(r"\[[a-zA-Z_][a-zA-Z0-9_]*(\+0x[0-9a-fA-F]+)?\]", "[DATA]", s)
            s = re.sub(r"\[0x[0-9a-fA-F]+\]", "[DATA]", s)
            # Fold large immediates
            s = re.sub(r"\b0x[0-9a-fA-F]{3,}\b", "IMM", s)
            out_lines.append(s)
        return "\n".join(out_lines)

    #  Pool

    def byte_exact_functions(self) -> frozenset[str]:
        return self._byte_exact_pool

    #  Cross-function elision normalization (Watcom-specific)

    def normalize_target(
        self,
        target_bytes: bytes,
        target_address: int,
        target_fixups: frozenset[int],
        target_lines: tuple[tuple[int, int], ...],
    ) -> NormalizedTarget:
        from c2.decompile._engine.normalize.tail_merge import normalize as _watcom_normalize
        return _watcom_normalize(
            target_bytes, target_address, target_fixups, target_lines, self,
        )

    def detect_cross_function_elision(
        self, name: str,
    ) -> tuple[str | None, str | None]:
        from c2.decompile._engine.normalize.tail_merge import detect_fallthrough
        from c2.commands.tail_merge import scan_tail_merge_donor
        info = self.function_info(name)
        fb = self.function_bytes(name)
        tm_hint = scan_tail_merge_donor(
            fb, info.address, is_vaddr=True,
            symbols_json=self.project.symbols_json,
        )
        tm_donor = tm_hint.donor_name if tm_hint else None
        ft_callee = detect_fallthrough(fb, info.address, self)
        return tm_donor, ft_callee


def _find_function_span(text: str, name: str) -> tuple[int, int] | None:
    """Return (start, end) byte indices of ``name``'s full definition."""
    pat = re.compile(_DEF_RE_TMPL.format(name=re.escape(name)), re.MULTILINE | re.DOTALL)
    m = pat.search(text)
    if not m:
        return None
    open_brace = m.end() - 1
    depth = 1
    i = open_brace + 1
    n = len(text)
    in_str = in_chr = in_lcom = in_bcom = False
    while i < n and depth > 0:
        c = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        if in_lcom:
            if c == "\n":
                in_lcom = False
            i += 1
            continue
        if in_bcom:
            if c == "*" and nxt == "/":
                in_bcom = False
                i += 2
                continue
            i += 1
            continue
        if in_str:
            if c == "\\":
                i += 2
                continue
            if c == '"':
                in_str = False
            i += 1
            continue
        if in_chr:
            if c == "\\":
                i += 2
                continue
            if c == "'":
                in_chr = False
            i += 1
            continue
        if c == "/" and nxt == "/":
            in_lcom = True
            i += 2
            continue
        if c == "/" and nxt == "*":
            in_bcom = True
            i += 2
            continue
        if c == '"':
            in_str = True
            i += 1
            continue
        if c == "'":
            in_chr = True
            i += 1
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        i += 1
    if depth != 0:
        return None
    return m.start(), i


#  Source body extraction


_DEF_RE_TMPL = (
    # Match function definition opener: optional storage class, return type,
    # function name, parenthesized params, then `{` on this or a following line.
    r"^(?:(?:static|extern|inline|__watcall|__cdecl|__fastcall)\s+)*"
    r"[\w\s\*]+\b{name}\s*\([^;]*?\)\s*(?:/\*[^*]*\*+(?:[^/*][^*]*\*+)*/\s*)*\{{"
)


def _extract_function_body(text: str, name: str) -> str | None:
    """Find ``name``'s definition in ``text`` via regex + brace matching."""
    span = _find_function_span(text, name)
    if span is None:
        return None
    start, end = span
    return text[start:end]


def _strip_leading_body_comments(func_text: str) -> str:
    """Remove leading comment-only / blank lines from the function body.

    The function body starts after the first unbalanced ``{``.  We walk
    forward consuming whitespace, line comments (``//``), and block
    comments (``/* ... */``) one logical token at a time, until we hit
    a real C token.  The result preserves the signature header, the
    opening brace, and the substantive body \u2014 but drops residue/parked
    /floor/CLASSIFIED claims that prior sessions left as inline notes.
    """
    open_brace = func_text.find("{")
    if open_brace < 0:
        return func_text
    after_brace = open_brace + 1

    i = after_brace
    n = len(func_text)
    while i < n:
        c = func_text[i]
        if c in " \t\r\n":
            i += 1
            continue
        if c == "/" and i + 1 < n and func_text[i + 1] == "/":
            # Line comment: skip to end of line (including the newline)
            nl = func_text.find("\n", i)
            i = n if nl < 0 else nl + 1
            continue
        if c == "/" and i + 1 < n and func_text[i + 1] == "*":
            # Block comment: skip to */
            end = func_text.find("*/", i + 2)
            if end < 0:
                break
            i = end + 2
            continue
        break

    if i == after_brace:
        return func_text
    # Reassemble: keep signature + `{\n`, drop everything up to the first
    # real token.  Re-insert a single newline + matching indentation
    # (defaulting to four spaces) so the body still reads naturally.
    head = func_text[: after_brace]
    tail = func_text[i:]
    return head + "\n    " + tail.lstrip(" \t")


def _extract_signature(body_text: str) -> str | None:
    """Extract the function signature (up to but not including `{`)."""
    brace = body_text.find("{")
    if brace < 0:
        return None
    sig = body_text[:brace].strip()
    # Strip trailing whitespace / newlines
    return sig


#  Helpers


def _replace_disp_in_op(op_str: str, disp: int, replacement: str) -> str:
    """Replace a hex displacement in an operand string with a symbolic form."""
    hex_form = f"0x{disp & 0xFFFFFFFF:x}"
    hex_form_alt = f"0x{disp & 0xFFFFFFFF:08x}"  # zero-padded
    for h in (hex_form, hex_form_alt):
        if h in op_str:
            return op_str.replace(h, replacement)
    # Capstone sometimes uses signed decimal form like '-0x10' or '+0x10';
    # try a regex-based catch-all
    return re.sub(r"-?0x[0-9a-fA-F]+", replacement, op_str, count=1)


def _is_reloc_insn(
    ins: capstone.CsInsn,
    fn_start: int = 0,
    fn_end: int = 0,
) -> bool:
    """Heuristic: True if the instruction's displacement field is a fixup.

    For rel32/rel8 call/jmp/jcc we additionally require the target to
    lie OUTSIDE [fn_start, fn_end) -- intra-function branches resolve at
    assembly time and are NOT relocations.  When ``fn_start == fn_end``
    (legacy callers that don't pass bounds) we conservatively treat all
    such branches as relocations as before.
    """
    if not ins.bytes:
        return False
    b0 = ins.bytes[0]
    is_rel_branch = False
    disp_size = 0
    if b0 == 0xE8 or b0 == 0xE9:  # call rel32 / jmp rel32
        is_rel_branch = True
        disp_size = 4
    elif b0 == 0x0F and len(ins.bytes) > 1 and (ins.bytes[1] & 0xF0) == 0x80:
        # 0F 8x rel32 (Jcc long form)
        is_rel_branch = True
        disp_size = 4
    if not is_rel_branch:
        # Otherwise we rely on the fixup_offsets set from OMF / LE.
        return False
    if fn_start == fn_end:
        # No bounds info -- preserve legacy conservative behaviour.
        return True
    # Decode the rel32 displacement to find the branch target.
    disp_bytes = bytes(ins.bytes[-disp_size:])
    disp = int.from_bytes(disp_bytes, "little", signed=True)
    target = ins.address + ins.size + disp
    # Intra-function = resolved at assembly time, NOT a relocation.
    return not (fn_start <= target < fn_end)

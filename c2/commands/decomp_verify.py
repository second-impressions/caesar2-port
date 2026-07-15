"""Verify decompiled C functions produce byte-identical code.

Approach
────────
All .c files in decomp/src/ are compiled together into a single LE
executable with a unified stubs file providing all unresolved externals.
Function bytes are then compared against the original PS.EXE.

Output can be filtered by source file pattern(s) and/or function name(s).

Build cache (mtime fast path + wmake-driven)
────────────────────────────────────────────
Two tiers of caching:

  0. **make-style up-to-date fast path (in-process, no container).**
     Before any staging, if the cached ``out.exe`` exists, the build
     config (cflags + image, stored in ``.build_config``) is unchanged,
     and ``out.exe`` is newer than every build input (``decomp/src/*.c``,
     ``decomp/include/*.h``, ``decomp/src/*.asm``), the binary is already
     current — ``_build_all`` returns immediately, skipping ALL Python
     staging (stub-strip + pycparser parse ≈ 5 s) AND the podman/wmake
     round trip (≈ 0.3 s).  A no-op verify drops from ~6 s to ~1.7 s.
     After every successful build ``out.exe`` is stamped to the build's
     start instant (wmake leaves it untouched on a content-stable no-op
     build, so without the stamp a touched-but-unchanged source would
     look perpetually newer and defeat the fast path).

  1. When a source DID change, fall through to the wmake build below.

The build runs in a *persistent* directory at ``.c2-cache/build/`` so
Watcom's native ``wmake`` can do incremental rebuilds based on file
mtimes — exactly what every other Watcom project does.  Per call:

  1. Regenerate stripped .c sources + auto-generated stubs.c, but
     only write to disk when content differs (preserves mtime → wmake
     correctly skips unchanged files).
  2. Copy headers into the build dir the same way.
  3. Drop a generated ``makefile`` listing every .c → .obj rule with
     "depends on every header" coupling (pessimistic but correct).
  4. Invoke ``wmake`` inside the container.  When nothing changed
     this is ~280 ms (container startup + wmake banner); when one
     .c file changed it adds ~70 ms for that wcc386 call.

Switching cflags or the image tag automatically invalidates the cache
because they end up in the makefile body, which is mtime-checked
against every .obj rule.  ``--no-cache`` rebuilds in a fresh tempdir
exactly like the previous behaviour.
"""

from __future__ import annotations

import contextlib
import fcntl
import io
import json
from functools import lru_cache
import os
import re
import shutil
import socket
import struct
import subprocess
import tempfile
import time
import uuid
from pathlib import Path
from typing import Annotated, Optional

import capstone
import typer
from rich.console import Console
from rich.markup import escape

_CS = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
_CS.detail = False

# The instrumented compiler image: byte-identical .obj to the stock 10.0a
# compiler (read-only printf hooks), but emits a `~WV1 ...` register-allocation
# trace on stdout that the regalloc hint layer consumes (c2.regalloc). Using it
# by default never perturbs a verify -- the `~WV1` lines are filtered where the
# build output is parsed. See watcom10.0a repo docs/wcc386-re/regalloc-trace-image.md.
# The instrumented `-trace` image is the default: byte-identical .obj plus a
# ~WV1 regalloc trace that the hint layer parses (the active build trace). A
# full 37-file build is ~13 s. (Earlier this looked like ~6 min, but that was a
# bug in the trace hook -- an uncapped def-line walk infinite-looping on the
# circular DOS instruction list, now fixed with a 64-iteration cap.) Set
# C2_VERIFY_IMAGE=localhost/watcom-10.0a-wibo for the stock compiler (~6 s,
# no trace -> regalloc hints then use the on-demand per-file fallback).
_STOCK_IMAGE = "localhost/watcom-10.0a-wibo"
_TRACE_IMAGE = "localhost/watcom-10.0a-wibo-trace"
_DEFAULT_IMAGE = os.environ.get("C2_VERIFY_IMAGE", _TRACE_IMAGE)


def _final_link_failure_reasons(report: dict | None) -> list[str]:
    """Return the real, non-debug divergences in a rebuild comparison.

    The final link intentionally permits the comparison's two documented
    non-semantic classes: ``~alias`` code-start labels and bytes beyond a
    function's final RET (``tail``).  Everything else represented here is a
    loaded-image difference or a relocation with different semantics.
    """
    if not report:
        return ["final-link comparison produced no report"]

    failures: list[str] = []
    for bucket, stats in report.get("code", {}).items():
        parts = []
        if stats.get("diff"):
            parts.append(f"{stats['diff']} diff")
        if stats.get("missing"):
            parts.append(f"{stats['missing']} unmatched")
        if parts:
            failures.append(f"{bucket} code: " + ", ".join(parts))

    data = report.get("data", {})
    data_parts = []
    if data.get("diff"):
        data_parts.append(f"{data['diff']} diff")
    if data.get("missing"):
        data_parts.append(f"{data['missing']} unmatched")
    if data_parts:
        failures.append("initialized data: " + ", ".join(data_parts))

    strict_bytes = report.get("strict_code_bytes", 0)
    if strict_bytes:
        failures.append(f"{strict_bytes} strict code byte(s) differ")

    pre_debug_bytes = report.get("pre_debug_byte_diff", 0)
    if pre_debug_bytes:
        failures.append(
            f"{pre_debug_bytes} pre-debug container byte(s) differ"
        )

    whole_file_bytes = report.get("whole_file_byte_diff", 0)
    if whole_file_bytes:
        failures.append(f"{whole_file_bytes} whole-file byte(s) differ")

    for kind, audit in report.get("fixups", {}).items():
        ps_only = len(audit.get("only_ps", []))
        rc_only = len(audit.get("only_rc", []))
        targets = len(audit.get("target_mismatches", []))
        parts = []
        if ps_only:
            parts.append(f"{ps_only} PS-only site(s)")
        if rc_only:
            parts.append(f"{rc_only} RC-only site(s)")
        if targets:
            parts.append(f"{targets} target mismatch(es)")
        if parts:
            failures.append(f"{kind} fixups: " + ", ".join(parts))

    placement = report.get("placement", {})
    real_start_breaks = [
        item for item in placement.get("starts_breaks", [])
        if not str(item).startswith("~")
    ]
    if real_start_breaks:
        failures.append(
            f"{len(real_start_breaks)} code symbol start(s) misplaced")
    if placement.get("data_misplaced"):
        failures.append(
            f"{len(placement['data_misplaced'])} data symbol(s) misplaced")

    sizes = report.get("sizes", {})
    for label, orig_key, rc_key in (
        ("code vsize", "o_code", "r_code"),
        ("data file size", "o_dfile", "r_dfile"),
        ("data vsize", "o_dvsize", "r_dvsize"),
    ):
        orig = sizes.get(orig_key)
        rebuilt = sizes.get(rc_key)
        if orig is not None and rebuilt is not None and orig != rebuilt:
            failures.append(f"{label}: PS {orig} != RC {rebuilt}")

    return failures


def _final_link_json(report: dict, failures: list[str]) -> dict:
    """Compact JSON projection; omit the thousands of per-symbol rows."""
    return {
        "ok": not failures,
        "failures": failures,
        "code": report.get("code", {}),
        "data": report.get("data", {}),
        "strict_code_bytes": report.get("strict_code_bytes", 0),
        "pre_debug_byte_diff": report.get("pre_debug_byte_diff", 0),
        "whole_file_byte_diff": report.get("whole_file_byte_diff", 0),
        "debug_grafted": report.get("debug_grafted", False),
        "generated_debug": report.get("generated_debug", {}),
        "strict_sites": report.get("strict_sites", []),
        "fixups": report.get("fixups", {}),
        "placement": report.get("placement", {}),
        "sizes": report.get("sizes", {}),
    }


def _final_link_relocations_by_address(
    report: dict | None,
    code_symbols: list[dict],
) -> dict[int, list[dict]]:
    """Attribute final-link code-fixup target defects to PS functions."""
    import bisect

    if not report or not code_symbols:
        return {}
    starts = [symbol["offset"] for symbol in code_symbols]
    result: dict[int, list[dict]] = {}
    mismatches = (
        report.get("fixups", {}).get("code", {}).get(
            "target_mismatches", [])
    )
    for mismatch in mismatches:
        site = mismatch["site"]
        index = bisect.bisect_right(starts, site) - 1
        if index < 0:
            continue
        symbol = code_symbols[index]
        end = symbol.get(
            "_end",
            starts[index + 1] if index + 1 < len(starts) else site + 1,
        )
        if site >= end:
            continue
        item = dict(mismatch)
        item["function_offset"] = site - symbol["offset"]
        result.setdefault(symbol["address"], []).append(item)
    return result

# ── Verbose-output depth toggle ───────────────────────────────────────────────
# `-v` prints a focused diagnostic header + a WINDOWED diff disasm (diff rows
# plus a few lines of context) by default.  Several heavy, lower-signal blocks
# are suppressed unless the caller passes `--full-hints` (or sets the env var):
#   * the per-source-line regalloc table (`regalloc by source line` / the long
#     conflict/birth dumps) -- the compact summary + `Regalloc:` verdict stay,
#   * the raw `binary-IR signatures (PS vs RC): PS={...} RC={...}` dict line
#     (the readable `PS-only`/`RC-only` lines below it carry the same signal),
#   * the FULL instruction-by-instruction disasm (windowing collapses long
#     runs of byte-identical rows into a `… N unchanged rows …` marker).
# Everything stripped is one flag away -- see the footer note in the rendered
# output and AGENTS.md Hard Rule #5.  Set via `--full-hints` or C2_FULL_HINTS=1.
_DIAG_FULL = bool(os.environ.get("C2_FULL_HINTS"))
# PS-only/RC-only op kinds that ARE the function's source lever (each maps to
# a named rule).  These are ALWAYS shown -- never elided by the drill-down cap
# -- so the lever for a function with many low-signal asymmetries isn't hidden.
_LEVER_KINDS = frozenset({
    "loop_rotation_entry", "loop_rotation_test_back",   # Rule 134 (while->for)
    "mid_func_epilogue",                                # Rule 135 (goto-shared)
    "regpair_const_exit",                               # Rule 85 (far-ptr exit)
    "r5c_idiv_pair",                                    # Rule 5c (div/mod CSE)
})
# Rows of byte-identical context kept on each side of a diff run when windowing
# the side-by-side disasm (only consulted when _DIAG_FULL is False).
_DIAG_CONTEXT = 6

# ── Canonical PS.EXE compiler flags ───────────────────────────────────────────
# The proven Watcom 10.0a command line PS.EXE was built with.  Every tool that
# compiles for byte-comparison (verifier, oracle, cgex, compiler-id) MUST use
# this exact set so their bytes are identical.  Each token is proven by an
# UNCONFOUNDED fingerprint — a compiler-determined codegen choice the source
# cannot fake — NOT by the byte-exact count (which is confounded because the
# source was hand-tuned against these flags):
#   -bt=dos -mf : DOS/4GW flat LE target (binary format)
#   -4r         : 486 register calling (__watcall).  Idiom `xor ah,ah;
#                 mov [m],ah` for literal-zero byte stores is the 8-byte form
#                 only -4/-5/-6 emit; -3r emits the 7-byte `mov byte [m],0`.
#   -s          : no stack-overflow checks (no __STK probe prologues).
#   -d1         : line-number debug info.  symbols.json has has_lines=true,
#                 has_locals=false for all modules (=-d1, not -d2/-d2 which
#                 would force -od + frame pointers).  -d1 adds debug records to
#                 the OBJ but does NOT change code-section bytes.
#   default OptSize=50 (no -os/-ot): the ONLY two flags that write OptSize are
#                 -os(100)/-ot(0) (cc/coptions.c Set_OS/Set_OT; default 50 in
#                 cmodel.c).  PS's strength-reduction ratio shl/(shl+imul)=0.59
#                 matches 50 (=0.60), not -os(0.26) or -ot(0.38).
#   default unsigned char (no -j): PROVEN by cross-build witness, not just the
#                 movsx/(movsx+movzx) byte ratio (0.85 = unsigned, not -j's
#                 0.91).  Definitive proof: a bare `char` (a string ptr IS a
#                 `char *`, type-independent of any binary) diverges across the
#                 three shipped builds of the SAME source: get_string_width's
#                 `*src` is ZERO-extended in PS.EXE (`and 0xff`) but SIGN-
#                 extended on the Mac (CodeWarrior: `lbz; extsb`).  A bare
#                 char's signedness IS the compiler default, so PS landing on
#                 the unsigned side means Watcom's default was unsigned => no -j
#                 (with -j that bare char would movsx like the Mac).  The Mac
#                 also excludes the `unsigned char *src` loophole (it would be
#                 lbz-only, no extsb).  (MSVC's default is signed too, but its
#                 /Od spills this deref to a stack local, so the Mac is the
#                 clean witness.)  Mechanism: cc SetPlainCharType ->
#                 TYPE_UCHAR -> CGDataType T_UINT_1 -> movzx/and.  See
#                 docs/char-signedness-proof.md.
#   inline 387 (-fpi87 is the -4r default): 4769 D8-DF bytes; -fp* flags are
#                 all byte-identical to baseline so the default already inlines.
PS_CFLAGS = "-bt=dos -mf -4r -s -d1"

# ── Source file annotation parser ─────────────────────────────────────────────


_mac_hint_cache: dict = {}


def _mac_hint(name: str) -> None:
    """One-line pointer to the Mac PPC source-shape oracle for a diffing
    function (MAC/ANALYSIS.md; house style §10).  Silent when the Mac
    binaries aren't extracted or the name is absent from both builds."""
    if name in _mac_hint_cache:
        msg = _mac_hint_cache[name]
        if msg:
            typer.echo(msg)
        return
    msg = None
    try:
        from c2 import macref
        for build in ("fr", "demo"):
            try:
                b = macref.get(build)
            except FileNotFoundError:
                continue
            rng = b.lookup(name)
            if rng:
                msg = (f"     mac: {rng[1] - rng[0]}b in {build} -- "
                       f"`c2 mac-fn {name}` (PPC disasm) / "
                       f"`c2 mac-decompile {name}` (Ghidra C, source-shape)")
                break
    except Exception:
        pass
    _mac_hint_cache[name] = msg
    if msg:
        typer.echo(msg)


def _win_hint(name: str, tu: str | None = None) -> None:
    """One-line CAESAR2.EXE pointer for a diffing function -- the second byte
    oracle.  Mirrors `_mac_hint`: prints whether a Windows mapping exists so
    the agent knows `c2 win-verify <fn>` / `c2 win-decompile <fn>` are usable.
    """
    try:
        from c2.win_bytes import win_hint, tu_of
        h = win_hint(name, tu or tu_of(name))
    except Exception:
        return
    if h.get("available"):
        typer.echo(f"     win: CAESAR2.EXE {h['win_va']} ({h['confidence']}) -- "
                   f"`c2 win-verify {name}` (2nd byte oracle) / "
                   f"`c2 win-decompile {name}` (MSVC /Od source-shape)")


def _mac_decompile_block(name: str) -> str | None:
    """Render the Mac PPC Ghidra decompile (AST-cleaned) for a diffing
    function.  Returns None if pyghidra/PEF aren't available or the function
    isn't found in the Mac binary.  Best-effort -- swallows all errors."""
    try:
        # Only show if the function exists in the Mac binary -- avoid spinning
        # up Ghidra for unrelated callees.
        from c2 import macref
        for build in ("fr", "demo"):
            try:
                b = macref.get(build)
            except FileNotFoundError:
                continue
            if b.lookup(name):
                break
        else:
            return None
        # Lazy import: only spin up the JVM if asked
        import mac as macmod
        if macmod.prog is None:
            macmod.open()
        return macmod.decompile_clean(name)
    except Exception as e:
        return f"(mac-decompile failed: {e})"


def _win_decompile_block(name: str) -> str | None:
    """Render the Windows MSVC /Od decompile (CAESAR2.EXE) for a diffing
    function -- the x86 source-shape oracle.  Returns None if there's no
    Windows mapping for ``name`` (short-circuits before spinning the JVM, like
    the Mac block).  Best-effort -- swallows all errors."""
    try:
        # Cheap func-map short-circuit: don't open the project for callees
        # that aren't even mapped in the Win build.
        from c2.win_bytes import win_hint, tu_of
        h = win_hint(name, tu_of(name))
        if not h.get("available"):
            return None
        import c2win
        # decompile_cached is cache-or-fetch: cache hit instant (no JVM),
        # cache miss opens the project (~60s first call) + persists the result.
        return c2win.decompile_cached(name)
    except Exception as e:
        return f"(win-decompile failed: {e})"


# session from the AST (classify_source), never a regex.
_SRC_FUNC_CACHE: dict[str, tuple] | None = None


def _build_src_func_cache() -> dict[str, tuple]:
    global _SRC_FUNC_CACHE
    if _SRC_FUNC_CACHE is None:
        # AST, not regex: classify_source (pycparser) gives the real top-level
        # FuncDefs, so the name->file map can't be fooled by prototypes, macro
        # bodies, or multi-line signatures.  Memoised by content, so this reuses
        # the build's own parse of each file (near-free).
        from c2.commands.c_source import classify_source
        _SRC_FUNC_CACHE = {}
        for p in sorted(Path("decomp/src").glob("*.c")):
            try:
                decls = classify_source(p.read_text(errors="replace"), p.name)
            except Exception:
                continue
            for fd in decls.func_defs:
                nm = getattr(fd.decl, "name", None)
                if nm:
                    _SRC_FUNC_CACHE.setdefault(nm, (p, fd))
    return _SRC_FUNC_CACHE


def _decomp_src_lines(name: str) -> dict[int, str] | None:
    """Return ``{line_number: text}`` for the decomp/src/*.c file that DEFINES
    ``name`` (fr line numbers are absolute within that .c file), or None."""
    rec = _build_src_func_cache().get(name)
    if rec is None:
        return None
    try:
        lines = rec[0].read_text(errors="replace").splitlines()
    except OSError:
        return None
    return {i + 1: t for i, t in enumerate(lines)}


def _rover_src_structure(name: str) -> dict | None:
    """AST-derived control-flow facts the rover hint needs to name an ACCURATE
    +k host (no guessing).  From the function's pycparser FuncDef:

      * ``dup_hosts``  {tail_store_line: if_line} -- a constant store to a global
        that FOLLOWS an if/else (or if/else-if) in the same block: the Rule 121 /
        start_smacking duplicated-tail host (push it into both arms -> +1).
      * ``guard_stores`` {line, ...} -- a constant store inside an
        ``if (cond) { ...; return; }`` guard with NO else: NOT a dup host (there
        are no "both arms" to push into).
      * ``const_stores`` {line, ...} -- every constant-to-global store line.

    Returns None when the function AST is unavailable."""
    rec = _build_src_func_cache().get(name)
    if rec is None:
        return None
    from pycparser import c_ast

    def _line(node):
        return getattr(getattr(node, "coord", None), "line", None)

    def _is_const_store(st):
        # `global = <int literal>;` (the RISCified const-store form).
        return (isinstance(st, c_ast.Assignment) and st.op == "="
                and isinstance(st.rvalue, c_ast.Constant)
                and isinstance(st.lvalue, (c_ast.ID, c_ast.StructRef,
                                           c_ast.ArrayRef)))

    def _block(node):
        if isinstance(node, c_ast.Compound):
            return node.block_items or []
        return [node] if node is not None else []

    def _ends_with_return(node):
        items = _block(node)
        return bool(items) and isinstance(items[-1], c_ast.Return)

    dup_hosts: dict[int, int] = {}
    guard_stores: set[int] = set()
    const_stores: set[int] = set()

    def walk(items):
        for i, st in enumerate(items):
            if _is_const_store(st):
                ln = _line(st)
                if ln:
                    const_stores.add(ln)
            if isinstance(st, c_ast.If):
                if st.iffalse is None and _ends_with_return(st.iftrue):
                    for s in _block(st.iftrue):
                        if _is_const_store(s) and _line(s):
                            guard_stores.add(_line(s))
                if st.iffalse is not None:
                    # statements AFTER this if/else in the block are its shared
                    # tail; a const-store there is a duplicated-tail host.
                    for tail in items[i + 1:]:
                        if _is_const_store(tail) and _line(tail):
                            dup_hosts[_line(tail)] = _line(st) or 0
                walk(_block(st.iftrue))
                walk(_block(st.iffalse))
            elif isinstance(st, (c_ast.For, c_ast.While, c_ast.DoWhile)):
                walk(_block(st.stmt))
            elif isinstance(st, c_ast.Compound):
                walk(st.block_items or [])
    try:
        walk(_block(rec[1].body))
    except Exception:
        return None
    return {"dup_hosts": dup_hosts, "guard_stores": guard_stores,
            "const_stores": const_stores}


def _visible_dword_picks(rc_insns, rc_off: int,
                         rc_line_map: dict[int, int] | None) -> set | None:
    """``(decomp_line, reg)`` set of the disasm-VISIBLE dword rover picks in the
    recompiled function -- real ``mov reg,[g]`` loads and ``mov [g],reg`` register
    stores (xor'd const-stores).  These survive LdStCompress and put a register
    in the bytes; everything the rover RISCified that got compressed back to a
    direct memory operand (``cmp [g],0`` / ``mov [g],imm``) is NOT here.  Feeds
    rover_hints.closeability's CompressIns model.  None when no line map."""
    if not rc_line_map:
        return None
    _load = re.compile(r"mov (e[a-d]x|e[sd]i|ebp), \[0x[0-9a-f]+\]$")
    _store = re.compile(r"mov \[0x[0-9a-f]+\], (e[a-d]x|e[sd]i|ebp)$")
    vis: set = set()
    cur: int | None = None
    for ins in rc_insns:
        abs_off = rc_off + ins[0]
        if abs_off in rc_line_map:
            cur = rc_line_map[abs_off]
        if cur is None:
            continue
        m = _load.match(ins[3]) or _store.match(ins[3])
        if m:
            vis.add((cur, m.group(1)))
    return vis


def _parse_annotations(c_file: Path) -> tuple[set[int], set[int]]:
    """Return (function_addrs, stub_addrs) from FUNCTION/STUB markers."""
    from c2.commands.c_source import classify_source
    src = c_file.read_text(errors="replace")
    decls = classify_source(src, c_file.name)
    func_addrs = {
        int(ann.address, 16)
        for ann in decls.annotations.values()
        if ann.kind == "FUNCTION"
    }
    stub_addrs = {
        int(ann.address, 16)
        for ann in decls.annotations.values()
        if ann.kind == "STUB"
    }
    return func_addrs, stub_addrs


# ── Imports from c_source ─────────────────────────────────────────────────────

from c2.commands.c_source import (
    generate_stubs as _generate_stubs_ast,
    strip_stub_bodies as _strip_stub_bodies,
    parse_c as _parse_c,
    classify as _classify,
    decl_to_stub as _decl_to_stub,
    scan_calling_conventions as _scan_calling_conventions,
    scan_pointer_qualifiers as _scan_pointer_qualifiers,
    _get_generator,
)
from c2.commands.rule_hints import detect_hints, histogram
from c2.commands.tail_merge import (
    scan_tail_merge_donor as _scan_tail_merge_donor,
    render_tail_merge_hint as _render_tail_merge_hint,
    render_donor_status_tag as _render_donor_status_tag,
    donor_blocking_status as _donor_blocking_status,
)


def _print_tail_merge(console, tm_hint, escape, rc_insns=None):
    """Print the Tail-merge hint line(s) with proper Rich markup.

    The body of the hint is escaped (donor names / disasm may contain
    Rich-special characters); the DONOR-BLOCKED warning is colored
    red and the donor-byte-exact note is dimmed.  Centralised here so
    all three call sites (compact + verbose + diff renderers) format
    the donor-blocking warning identically.

    When ``rc_insns`` is supplied, the cross-function epilogue CHAIN is
    traced (partial stubs hop: ``pop ebp; jmp …`` → final pops+ret) and
    the required callee-save suffix is compared against RC's prologue —
    the missing/extra saves are the actual lever (Rule 110/126 value
    holders), not the jmp encodings.
    """
    _ds = _donor_blocking_status(tm_hint.donor_name)
    console.print(
        f"  [yellow]Tail-merge[/]: "
        f"{escape(_render_tail_merge_hint(tm_hint))}",
        highlight=False,
    )
    tag = _render_donor_status_tag(tm_hint, _ds)
    if tag is not None:
        color = "red" if _ds == "diff" else "dim"
        console.print(f"      [{color}]{escape(tag)}[/]", highlight=False)
    try:
        from c2.commands.tail_merge import trace_epilogue_chain, render_epilogue_chain
        chain = trace_epilogue_chain(tm_hint)
        if chain is not None and chain.restores:
            rc_saves = None
            if rc_insns:
                from c2.commands.frame_hints import prologue_pushes
                rc_saves = prologue_pushes(rc_insns)
            for ln in render_epilogue_chain(chain, rc_saves):
                console.print(f"      [dim]{escape(ln)}[/]", highlight=False)
    except Exception:
        pass

_INCLUDE_CAESAR2_RE = re.compile(r'#\s*include\s+["<]caesar2\.h[>"]')

# ── PS-module link order ─────────────────────────────────────────────────────
#
# PS.EXE's linker concatenated module _TEXT contributions in link order, and
# each decomp/src/*.c mirrors exactly one PS module (contiguous address
# range).  A file's LOWEST `// FUNCTION: C2 0x…` annotation therefore orders
# the TUs exactly as PS's link placed them.  Annotation-less files (pure-data
# TUs: c2_vars.c, datainit.c, smackinp.c, sndail.c, sndnull.c) contribute no
# comparable code but may carry deliberate layout bytes (smackinp.c's Rule 45
# SYM_TEMP pad must stay IMMEDIATELY after smacker.obj); they inherit their
# alphabetical predecessor's key so their relative slot is unchanged from the
# old alphabetical order.
_FUNC_ANN_RE = re.compile(r"^// FUNCTION: C2 0x([0-9A-Fa-f]+)", re.M)


def _ps_link_order(c_files: list[Path]) -> list[Path]:
    """Return ``c_files`` sorted into PS module order for the wlink FILE
    list (see block comment above).  ``c_files`` must be alphabetically
    sorted (it is: ``sorted(src_dir.glob("*.c"))``)."""
    keyed: list[tuple[float, Path]] = []
    prev_key = -1.0
    for i, cf in enumerate(c_files):
        try:
            addrs = _FUNC_ANN_RE.findall(cf.read_text(errors="replace"))
        except OSError:
            addrs = []
        if addrs:
            key = float(min(int(a, 16) for a in addrs))
            prev_key = key
        else:
            # data-only TU: keep it glued right behind its alphabetical
            # predecessor (fractional bump preserves suborder among
            # several consecutive annotation-less files).
            key = prev_key + (i + 1) / (10.0 * len(c_files))
        keyed.append((key, cf))
    return [cf for _k, cf in sorted(keyed, key=lambda t: t[0])]

# Where the verifier looks up which symbols the Watcom CRT (clib3r.lib)
# already provides.  When an `extern foo` from a .c file matches one of
# these, we skip the auto-generated stub so the real library entry wins
# at link time — critical for `<stdio.h>` / `<stdlib.h>` / `<string.h>`
# bodies (printf, exit, free, memcpy, …) to behave like in PS.EXE.
_CLIB3R_SYMBOLS_CACHE = Path("decomp/lib/clib3r-symbols.txt")

# ── ASM-side declaration parsing ──────────────────────────────────────────────
#
# The 7 hand-written C2 .asm modules (library.asm, sprites.asm, dia_ptrs.asm,
# dialarga.asm, dialargb.asm, dia_medi.asm, dia_smal.asm) are assembled with
# 10.0a wasm and linked into the verifier build alongside the .c objects.
# Each module declares its exported functions with ``PUBLIC <name>`` and its
# external data references with ``EXTRN <name>: BYTE``.
_PUBLIC_RE = re.compile(r"^\s*PUBLIC\s+(\S+)\s*$")
_EXTRN_BYTE_RE = re.compile(r"^\s*EXTRN\s+(\S+)\s*:\s*BYTE\s*$")
_EXTRN_PROC_RE = re.compile(r"^\s*EXTRN\s+(\S+)\s*:\s*PROC\s*$")


def _parse_asm_decls(asm_file: Path) -> tuple[set[str], set[str], set[str]]:
    """Return (publics, extern_data, extern_proc) declared by ``asm_file``.

    Names are returned exactly as they appear in the .asm file (i.e. the
    Watcom-mangled linker-level symbol with leading/trailing underscores).
    """
    publics: set[str] = set()
    extern_data: set[str] = set()
    extern_proc: set[str] = set()
    for line in asm_file.read_text(errors="replace").splitlines():
        if (m := _PUBLIC_RE.match(line)):
            publics.add(m.group(1))
        elif (m := _EXTRN_BYTE_RE.match(line)):
            extern_data.add(m.group(1))
        elif (m := _EXTRN_PROC_RE.match(line)):
            extern_proc.add(m.group(1))
    return publics, extern_data, extern_proc



# ── Container runner ──────────────────────────────────────────────────────────

# ── Container reuse hook ─────────────────────────────────────────────────────
#
# By default, every `_run_in_container` invocation starts a fresh
# `podman run --rm`, which adds ~200-300 ms of startup per call.
# Long-lived workflows (e.g. `c2 sweep` trying dozens of variants
# against the same source tree) can avoid that overhead by starting
# a single sleep-forever container up front and `exec`-ing into it.
#
# The hook is a module-level slot rather than a per-call argument so
# the existing decomp-verify call chain (which goes through several
# layers) doesn't need a plumbing change.  Callers register a
# container name with `set_exec_container(name)`; subsequent
# `_run_in_container` calls then use `podman exec` against that name.
# Passing `None` clears it.
_EXEC_CONTAINER: Optional[str] = None


def set_exec_container(name: Optional[str]) -> None:
    """Direct subsequent `_run_in_container` calls to `podman exec`
    into the named long-lived container.  Pass `None` to restore the
    default `podman run --rm` behaviour.
    """
    global _EXEC_CONTAINER
    _EXEC_CONTAINER = name


def reap_orphan_warm_containers() -> int:
    """Force-remove leftover ``c2vrf_*`` / ``c2_forge_*`` containers (the
    verify warm pool, per-call ``c2vrf_<uuid>`` build containers, AND the
    forge worker pool) whose OWNER process is no longer alive.  These leak when a run is SIGKILLed (e.g. a
    wrapping timeout that kills python before the cleanup handler runs): a
    ``podman run --rm`` build container keeps grinding ``wmake`` headless, and
    one of those alone holds the build lock / pins a CPU so every later run
    crawls or blocks (the "hung compiles" pathology).  Self-healing: each
    container is tagged ``--label c2_owner_pid=<pid>``; we reap only those whose
    owner pid is dead, so concurrent live runs are never touched.  #reaped.
    """
    try:
        out = subprocess.run(
            ["podman", "ps", "-a", "--filter", "name=c2vrf_",
             "--filter", "name=c2_forge_",
             "--format", "{{.Names}} {{.Label \"c2_owner_pid\"}}"],
            capture_output=True, text=True, timeout=10).stdout
    except Exception:
        return 0
    reaped = 0
    for line in out.splitlines():
        parts = line.split()
        if not parts:
            continue
        cname = parts[0]
        owner = parts[1] if len(parts) > 1 else ""
        alive = False
        if owner.isdigit():
            try:
                os.kill(int(owner), 0)      # raises if the pid is gone
                alive = True
            except ProcessLookupError:
                alive = False
            except PermissionError:
                alive = True                # exists, just not ours -> keep
        # No/blank owner label (legacy container) -> treat as orphan.
        if not alive:
            # -t 0: SIGKILL immediately (a stuck dosemu2 ignores graceful stop
            # and would otherwise block for the stop-timeout). Never let a slow
            # or failing reap crash the caller's startup.
            try:
                subprocess.run(["podman", "rm", "-f", "-t", "0", cname],
                               capture_output=True, timeout=30)
                reaped += 1
            except Exception:
                pass
    return reaped


def start_warm_container(work: Path | None, image: str) -> str:
    """Start a sleep-forever container with the verifier's build dir
    mounted at ``/src``.  Returns the container name; pair with
    `stop_warm_container`.

    Pass ``work`` to override which host directory becomes /src.  The
    default uses the same persistent ``.c2-cache/build/`` that ad-hoc
    ``podman run`` calls would mount, so the warm container observes
    identical paths.
    """
    # Self-heal first: drop any orphans left by a previously-killed run so
    # their stuck dosemu2 processes stop starving the CPU.
    reap_orphan_warm_containers()
    if work is None:
        work = _BUILD_DIR
    # Ensure the dir exists before mounting it (otherwise podman binds
    # an empty parent and the verifier's later writes won't show up).
    work.mkdir(parents=True, exist_ok=True)
    name = f"c2vrf_warm_{uuid.uuid4().hex[:12]}"
    # Override the image's ENTRYPOINT to a do-nothing loop so the
    # container stays alive and we can `podman exec` real commands
    # through the wrapper at will.
    #
    # ``--init`` is REQUIRED: each `podman exec /usr/local/bin/watcom`
    # forks a `dosemu2.bin` that is re-parented to PID 1 when it exits.
    # Without an init, PID 1 is bare `sleep infinity`, which never calls
    # wait() — so every exec leaves a permanent <defunct> dosemu2
    # zombie.  Over a long-lived warm container these accumulate into
    # the hundreds (PID-slot leak).  ``--init`` makes podman run
    # catatonit as PID 1, which reaps re-parented children.
    subprocess.run(
        ["podman", "run", "-d", "--rm", "--init",
         "--name", name,
         "--label", f"c2_owner_pid={os.getpid()}",
         "-v", f"{work.resolve()}:/src",
         "--entrypoint", "sleep",
         image, "infinity"],
        check=True, capture_output=True, timeout=30,
    )
    return name


def stop_warm_container(name: str) -> None:
    """Force-stop the named warm container; ignore errors."""
    subprocess.run(["podman", "kill", name],
                   capture_output=True, timeout=10)
    subprocess.run(["podman", "rm", "-f", name],
                   capture_output=True, timeout=10)


def _run_in_container(
    work: Path,
    image: str,
    command: str,
    timeout: int = 120,
) -> tuple[bool, str]:
    """Run a single DOS command inside the container.

    Returns (success, filtered_output).

    Notes:
      * The container is given an explicit ``--name`` so we can
        force-kill it on Python-side timeout — ``--rm`` alone does
        not stop a running container when ``podman run`` is killed
        from outside (the container keeps running headless until
        its work completes), which previously left zombies behind.
      * ``wmake`` *interactively prompts* "Should this file be
        deleted [Yes/No]?" when a compile target's command fails.
        That prompt blocks forever in our headless dosemu2 setup.
        Callers that invoke wmake should pass the ``-e`` option
        (erase failed targets without prompting) — see _build_all.
      * When `set_exec_container(name)` has been called, this routes
        the command through `podman exec` into the existing warm
        container instead of spawning a new one.
    """
    if _EXEC_CONTAINER is not None:
        # The image's ENTRYPOINT (/usr/local/bin/watcom) runs the
        # DOSemu wrapper that interprets the DOS command.  podman
        # exec bypasses ENTRYPOINT, so we invoke the wrapper
        # explicitly with the same `command` arg that podman run
        # would have appended as CMD.
        # The wibo shim takes argv (TOOL=$1; shift), not one command
        # string like the retired dosemu2 wrapper -- split here.
        import shlex
        cmd = [
            "podman", "exec", _EXEC_CONTAINER,
            "/usr/local/bin/watcom", *shlex.split(command),
        ]
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            raise
        combined = result.stdout + "\n" + result.stderr
        filtered = "\n".join(
            ln for ln in combined.splitlines()
            if not any(skip in ln for skip in (
                "Running dosemu2", "recommended with",
                "dosemu -s", "DOSEMU",
            ))
        ).strip()
        return result.returncode == 0, filtered

    container_name = f"c2vrf_{uuid.uuid4().hex[:12]}"
    cmd = [
        "podman", "run", "--rm",
        "--name", container_name,
        # owner pid so a build container leaked by an EXTERNAL SIGKILL (e.g. a
        # wrapping timeout that kills python before the handler below runs) can
        # be reaped on the next startup by reap_orphan_warm_containers().
        "--label", f"c2_owner_pid={os.getpid()}",
        "-v", f"{work}:/src",
        image,
        # wibo shim convention: argv, not a single command string
        *__import__("shlex").split(command),
    ]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
    except subprocess.TimeoutExpired:
        # ``podman run`` died (Python killed it) but the container
        # itself is still running.  Force-stop and clean up.
        subprocess.run(
            ["podman", "kill", container_name],
            capture_output=True, timeout=10,
        )
        subprocess.run(
            ["podman", "rm", "-f", container_name],
            capture_output=True, timeout=10,
        )
        raise
    combined = result.stdout + "\n" + result.stderr
    filtered = "\n".join(
        ln for ln in combined.splitlines()
        if not any(skip in ln for skip in (
            "Running dosemu2", "recommended with", "dosemu -s", "DOSEMU",
        ))
    ).strip()
    return result.returncode == 0, filtered

# ── clib3r symbol probe ──────────────────────────────────────────────────────
#
# `wlib clib3r.lib` prints a two-column listing of every public symbol
# next to its owning .obj module:
#
#     exit_...................exit             abort_.................abort
#     printf_...............printf             ...
#
# We parse this once and cache the symbol set in
# ``decomp/lib/clib3r-symbols.txt`` (one name per line) so subsequent
# verifier runs skip the container round-trip.

_CLIB3R_LINE_RE = re.compile(
    r"\b([A-Za-z_]\w{0,31})\.{2,}([A-Za-z_]\w{0,31})\b"
)


def _probe_clib3r_symbols(image: str) -> set[str]:
    """Run ``wlib`` in the container and return clib3r's public-symbol set.

    Symbol names are returned exactly as the linker sees them — i.e.
    with the trailing ``_`` that Watcom adds for ``__watcall`` mangling
    (so ``exit`` in C source becomes ``exit_`` in the library).
    """
    work = Path(tempfile.mkdtemp(prefix="c2_clib3r_"))
    try:
        # wibo shim takes argv; wlib writes the listing to stdout when no
        # output file is given -- capture it instead of the old bat redirect.
        ok, _txt = _run_in_container(
            work, image,
            "wlib Z:\\opt\\watcom\\lib386\\dos\\clib3r.lib", timeout=60)
        (work / "probe.txt").write_text(_txt if ok else "")
        out_path = work / "probe.txt"
        if not ok or not out_path.exists():
            return set()
        text = out_path.read_text(errors="replace")
    finally:
        shutil.rmtree(work, ignore_errors=True)

    return {sym for sym, _mod in _CLIB3R_LINE_RE.findall(text)}


def _load_clib3r_symbols(image: str) -> set[str]:
    """Return clib3r.lib's public-symbol set, populating the cache file
    on first call (or if the cache is empty / missing)."""
    cache = _CLIB3R_SYMBOLS_CACHE
    if cache.exists() and cache.stat().st_size > 0:
        return {ln.strip() for ln in cache.read_text().splitlines() if ln.strip()}

    syms = _probe_clib3r_symbols(image)
    if syms:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text("\n".join(sorted(syms)) + "\n")
    return syms


def _is_clib3r_provided(name: str, clib3r: set[str]) -> bool:
    """Does the CRT already provide a body for *name*?

    Checks both the literal name (for ``#pragma aux NAME "*"`` symbols
    like ``_AIL_shutdown``) and the watcall-mangled ``NAME_`` form.
    """
    return name in clib3r or (name + "_") in clib3r



# ── Persistent build directory ────────────────────────────────────────────────
#
# Watcom ships ``wmake``, which does mtime-based incremental rebuilds
# for free.  We keep all build artefacts in a single, persistent
# directory at ``.c2-cache/build/`` between calls so wmake sees the
# previous .obj files and only recompiles what actually changed.
#
# The only Python responsibility on top of that is "don't bump the
# .c file's mtime when its content is unchanged" — without that wmake
# would rebuild every translation unit every call.

_BUILD_DIR = Path(".c2-cache/build")


def _write_if_changed(path: Path, content: bytes) -> bool:
    """Write *content* to *path* only when it differs from the existing
    file.  Returns True if a write happened (mtime now newer).

    DOS 2-SECOND-BUCKET STALENESS FIX (root-caused 2026-07-09): wmake
    runs INSIDE dosemu, whose redirector presents Linux mtimes truncated
    to absolute 2-second DOS FAT buckets, and wmake treats an EQUAL
    timestamp as up-to-date.  A changed .c staged < 2 s after its .obj
    was written -- same even-second bucket -- was therefore silently
    NOT recompiled (the long-standing \"rarely goes stale, wrong diff
    count\" build-cache bug; deterministic repro: obj@T+0.2 c@T+1.8
    skips, c@T+2.1 rebuilds).  Fix: after a real write, if any sibling
    .obj lives in the same-or-later DOS bucket, bump this file's mtime
    to the start of the NEXT bucket (< 2 s into the future -- harmless,
    and strictly newer in DOS time).  Sibling scan: this file's own
    .obj for sources; ALL .obj for shared deps (headers / makefile,
    which every rule depends on)."""
    if path.exists() and path.read_bytes() == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    objs = ([path.with_suffix(".obj")] if path.suffix in (".c", ".asm")
            else list(path.parent.glob("*.obj")))
    try:
        latest = max((o.stat().st_mtime for o in objs if o.exists()),
                     default=None)
        if latest is not None:
            my_bucket = int(path.stat().st_mtime) // 2
            obj_bucket = int(latest) // 2
            if my_bucket <= obj_bucket:
                t = (obj_bucket + 1) * 2
                os.utime(path, (t, t))
    except OSError:
        pass
    return True


def _cleanup_work(work: Path) -> None:
    """Remove *work* unless it is the persistent build dir."""
    try:
        if work.resolve() == _BUILD_DIR.resolve():
            return
    except OSError:
        pass
    shutil.rmtree(work, ignore_errors=True)


# ── Build-dir lock (concurrency guard) ────────────────────────────────────────
#
# The persistent ``.c2-cache/build/`` is shared by every cache-mode verify.
# Two verifies running at once would have their ``wasm`` / ``wcc386`` /
# ``wlink`` invocations write the same .obj/.exe files concurrently,
# interleaving bytes into corrupt object files (observed in the wild:
# oversized objs, ``invalid record type 0x0000``, duplicate symbols) which
# then make ``wlink`` error in a loop and wedge dosemu.  We serialise
# cache-mode builds with an advisory ``flock`` on a sibling lock file.
#
# Properties:
#   * **Blocking wait** — a second verify waits for the first to finish
#     rather than racing or erroring out (prints a one-line notice).
#   * **Self-healing** — ``flock`` is tied to the open file description, so
#     the kernel releases it automatically when the holding process exits,
#     INCLUDING on SIGKILL / crash.  A dead holder never blocks anyone; no
#     stale-lock detection or manual cleanup is ever needed.
#   * **PID visible** — the holder writes ``pid / host / acquired-time`` into
#     the lock file purely for diagnostics (``cat .c2-cache/build.lock``
#     shows who holds it).  Correctness comes from flock, not the file
#     contents, so a stale PID left by a crash is harmless and is
#     overwritten by the next acquirer.

_BUILD_LOCK = _BUILD_DIR.parent / (_BUILD_DIR.name + ".lock")


@contextlib.contextmanager
def _build_dir_lock(lock_path: Path = _BUILD_LOCK):
    """Serialise access to the shared persistent build dir.

    Blocks until the advisory lock is acquired (printing a one-line notice
    naming the current holder if we have to wait), records this process's
    pid in the lock file for visibility, and releases on exit.  Released
    automatically by the kernel if this process dies while holding it, so
    a crashed verify can never leave the lock stuck.
    """
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o644)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            # Contended: surface who holds it, then block until free.
            holder = ""
            try:
                lines = os.pread(fd, 256, 0).decode("utf-8", "replace").splitlines()
                holder = lines[0] if lines else ""
            except OSError:
                pass
            who = f" (held by PID {holder})" if holder else ""
            typer.echo(f"  Waiting for build lock{who} …", err=True)
            fcntl.flock(fd, fcntl.LOCK_EX)  # blocks; self-heals if holder dies
        # Acquired — stamp our identity for `cat`-level diagnostics.
        try:
            os.ftruncate(fd, 0)
            stamp = (f"{os.getpid()}\n{socket.gethostname()}\n"
                     f"{time.strftime('%Y-%m-%dT%H:%M:%S%z')}\n")
            os.pwrite(fd, stamp.encode(), 0)
        except OSError:
            pass
        yield
    finally:
        try:
            os.ftruncate(fd, 0)  # clear holder info on release
        except OSError:
            pass
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)


# ── Unified build ─────────────────────────────────────────────────────────────

def _inject_convention(stub_text: str, name: str, keyword: str) -> str:
    """Insert a calling-convention keyword before a stub's function name.

    The pycparser generator emits ``<rettype> <name>(...) { ... }`` with
    no convention modifier (it was stripped at parse time).  We splice
    ``keyword`` in immediately before the first occurrence of the
    function name followed by ``(`` so Watcom applies the right ABI /
    symbol mangling (e.g. ``void SmackToScreen(...)`` ->
    ``void __pascal SmackToScreen(...)``).
    """
    m = re.search(rf"\b{re.escape(name)}\s*\(", stub_text)
    if not m:
        return stub_text
    return stub_text[: m.start()] + keyword + " " + stub_text[m.start():]


def _inject_pointer_qualifier(stub_text: str, name: str, qualifier: str) -> str:
    """Insert a pointer qualifier before the `*` of a stub's pointer return.

    Companion to :func:`_inject_convention` for pointer-type qualifiers
    (``__far``/``__near``/``__huge``).  These go BETWEEN the base type and
    the `*` of a pointer-returning decl (``char __far *name(...)``), not
    before the function name.  pycparser re-emits ``char *name(...)``;
    we splice the qualifier in so the stub matches the header's pointer
    size — a far-pointer return occupies edx:eax (two registers), which
    is load-bearing for Watcom's register contract.  Without this the
    stub emits ``char *name(...)`` (near) and the build errors E1062
    (far-vs-near return mismatch) once the header declares the prototype
    far.  See ``docs/codegen-experiments/start_tune.py``.

    Anchored on the `*` immediately before ``name(``, so parameter
    pointers (which precede a different identifier) are not touched.
    """
    m = re.search(rf"\*\s*{re.escape(name)}\s*\(", stub_text)
    if not m:
        return stub_text
    star = m.start()  # position of the `*`
    return stub_text[:star] + qualifier + " " + stub_text[star:]


def _build_all(
    src_dir: Path,
    include_dir: Path,
    image: str,
    cflags: str,
    use_cache: bool = True,
    timings: bool = False,
) -> tuple[bool, str, Path]:
    """Locking wrapper around :func:`_build_all_impl`.

    Returns ``(ok, output, work, exe_path, map_path)`` where the exe/map
    paths point at a per-process SNAPSHOT taken while the build lock was
    held (cache mode) -- never read the shared ``work/out.exe`` after the
    lock is gone, a concurrent session may relink it.

    Cache-mode builds share the persistent ``.c2-cache/build/`` dir, so
    they are serialised under :func:`_build_dir_lock` to stop concurrent
    ``wasm``/``wlink`` writes from corrupting shared object files (the
    cause of the ``invalid object file`` linker wedge).  ``--no-cache``
    builds use a private tempdir and need no lock.
    """
    if not use_cache:
        ok, out, work = _build_all_impl(src_dir, include_dir, image, cflags,
                                        use_cache=False, timings=timings)
        return ok, out, work, work / "out.exe", work / "out.map"
    # ── LOCK-FREE up-to-date fast path ────────────────────────────────
    # The exclusive build lock can be held for ~30s by a concurrent
    # session's container build; an up-to-date reader must NOT wait on
    # it.  Optimistically check freshness, snapshot the artifacts, then
    # RE-CHECK that nothing moved underneath (mtime+size of exe/map
    # unchanged AND still newer than every input).  Any inconsistency ->
    # fall through to the locked path.
    work = _BUILD_DIR
    exe, mp = work / "out.exe", work / "out.map"
    try:
        if exe.exists() and mp.exists():
            config = f"{cflags}\x00{image}"
            cfg_file = work / ".build_config"
            if (cfg_file.exists()
                    and cfg_file.read_text(errors="replace") == config):
                inputs = (list(src_dir.glob("*.c"))
                          + list(include_dir.glob("*.h"))
                          + list(src_dir.glob("*.asm")))
                newest = max((f.stat().st_mtime for f in inputs), default=0.0)
                st_e0, st_m0 = exe.stat(), mp.stat()
                if st_e0.st_mtime >= newest:
                    import atexit
                    import shutil as _sh
                    import tempfile as _tf
                    snap = Path(_tf.mkdtemp(prefix="c2_exe_snap_"))
                    atexit.register(_sh.rmtree, snap, ignore_errors=True)
                    _sh.copy2(exe, snap / "out.exe")
                    _sh.copy2(mp, snap / "out.map")
                    st_e1, st_m1 = exe.stat(), mp.stat()
                    if ((st_e1.st_mtime, st_e1.st_size)
                            == (st_e0.st_mtime, st_e0.st_size)
                            and (st_m1.st_mtime, st_m1.st_size)
                            == (st_m0.st_mtime, st_m0.st_size)):
                        if timings:
                            typer.echo("  \u23f1  up-to-date (lock-free fast "
                                       "path)", err=True)
                        return (True, "(up-to-date; build skipped)", work,
                                snap / "out.exe", snap / "out.map")
    except OSError:
        pass
    with _build_dir_lock():
        ok, out, work = _build_all_impl(src_dir, include_dir, image, cflags,
                                        use_cache=True, timings=timings)
        # Snapshot the link products to a private per-process dir WHILE
        # STILL HOLDING THE LOCK: the shared out.exe can be relinked by a
        # concurrent session the moment we release it, and reading it
        # later would compare somebody else's build against our sources.
        exe, mp = work / "out.exe", work / "out.map"
        if ok and exe.exists() and mp.exists():
            import atexit
            import shutil as _sh
            import tempfile as _tf
            snap = Path(_tf.mkdtemp(prefix="c2_exe_snap_"))
            atexit.register(_sh.rmtree, snap, ignore_errors=True)
            _sh.copy2(exe, snap / "out.exe")
            _sh.copy2(mp, snap / "out.map")
            return ok, out, work, snap / "out.exe", snap / "out.map"
        return ok, out, work, exe, mp


def _build_all_impl(
    src_dir: Path,
    include_dir: Path,
    image: str,
    cflags: str,
    use_cache: bool = True,
    timings: bool = False,
) -> tuple[bool, str, Path]:
    """Compile all .c files in src_dir + unified stubs into one LE exe.

    Returns (success, build_output, work_dir).  *work_dir* is the
    persistent ``.c2-cache/build/`` when ``use_cache=True`` (the
    default) and a fresh tempdir otherwise.  The caller is expected
    to leave the persistent dir alone — it's reused across calls.

    With ``timings=True`` print per-phase wall-clock to stderr.
    """
    import pycparser
    import time
    from pycparser import c_ast

    def _t(label: str, t0: float) -> float:
        if timings:
            typer.echo(f"  ⏱  {label:<32} {time.perf_counter()-t0:5.2f}s",
                       err=True)
        return time.perf_counter()

    t0 = time.perf_counter()
    # Wall-clock at build entry.  After a successful build we stamp
    # ``out.exe`` to this instant so the make-style fast path treats the
    # binary as newer than every prerequisite that existed when the build
    # started — and any source edited DURING the build (mtime > this)
    # correctly triggers a rebuild next time.
    build_start_wall = time.time()

    if use_cache:
        work = _BUILD_DIR
        work.mkdir(parents=True, exist_ok=True)
    else:
        work = Path(tempfile.mkdtemp(prefix="c2_verify_"))

    c_files = sorted(src_dir.glob("*.c"))
    if not c_files:
        return False, "No .c files found", work

    # ── make-style up-to-date fast path ────────────────────────────────
    # If a cached ``out.exe`` already exists and is newer than EVERY build
    # input (the .c / .h / .asm sources) *and* the build config (cflags +
    # image) is unchanged, the binary is current — skip all staging,
    # pycparser parsing, stub generation, and the container/wmake round
    # trip entirely.  This mirrors ``make``'s timestamp check: the
    # expensive work (≈hundreds of ms of Python staging + ~280 ms podman
    # call) is only paid when a source actually changed.  ``--no-cache``
    # (use_cache=False) always rebuilds in a fresh tempdir.
    out_exe = work / "out.exe"
    if use_cache and out_exe.exists():
        config = f"{cflags}\x00{image}"
        cfg_file = work / ".build_config"
        cfg_ok = (cfg_file.exists()
                  and cfg_file.read_text(errors="replace") == config)
        if cfg_ok:
            inputs = (list(src_dir.glob("*.c"))
                      + list(include_dir.glob("*.h"))
                      + list(src_dir.glob("*.asm")))
            newest = max((f.stat().st_mtime for f in inputs), default=0.0)
            if out_exe.stat().st_mtime >= newest:
                _t("up-to-date — build skipped", t0)
                return True, "(up-to-date; build skipped)", work
    # Cache integrity guard: a previous wcc386 SIGSEGV (e.g. a buggy -trace
    # patch_trace hook) leaves the half-written .obj at 0 bytes -- wmake then
    # considers it built and the next wlink errors out with "is an invalid
    # object file".  Drop any 0-byte .obj so the next make rebuilds it instead
    # of trusting the corruption.
    if use_cache:
        for stale in work.glob("*.obj"):
            if stale.stat().st_size == 0:
                stale.unlink()

    # Discover the C2 hand-written .asm files.  Currently the eight
    # modules listed below; the set is fixed (driven by ``c2 decomp``
    # which only emits these).  Anything else in src_dir with a .asm
    # extension would be rejected by symbols.json lookups anyway.
    _C2_ASM_NAMES = {
        "library.asm", "sprites.asm", "dia_ptrs.asm",
        "dialarga.asm", "dialargb.asm", "dia_medi.asm", "dia_smal.asm",
        "palet.asm",
    }
    asm_files = sorted(
        f for f in src_dir.glob("*.asm") if f.name in _C2_ASM_NAMES
    )

    # Copy headers — write only if content differs so unchanged headers
    # don't trigger a full rebuild via the makefile dep on every .h.
    header_files = sorted(include_dir.glob("*.h"))
    n_h_changed = 0
    header_texts: list[str] = []
    for h in header_files:
        data = h.read_bytes()
        if _write_if_changed(work / h.name, data):
            n_h_changed += 1
        header_texts.append(data.decode("utf-8", "replace"))
    # Calling-convention map for external functions declared with a
    # convention keyword/macro (e.g. RAD's `RADEXPLINK == __pascal`).
    # pycparser strips these, so auto-generated stubs would otherwise
    # link as the wrong symbol; we re-inject the keyword below.
    conv_map = _scan_calling_conventions(header_texts)
    # Pointer-qualifier map (e.g. `char __far *_AIL_start_sequence`), for
    # far-pointer-returning stubs whose `__far` preprocess() stripped.
    # Re-injected below so the stub matches the header's pointer size.
    ptr_qual_map = _scan_pointer_qualifiers(header_texts)
    t0 = _t(f"copy headers ({n_h_changed}/{len(header_files)} changed)", t0)

    # Copy .asm files into the build dir for wasm to consume; same
    # mtime-stable copy as the .c files.  Each .asm assembles into a
    # standalone .obj that the linker pulls in next to the .c objects.
    n_asm_changed = 0
    for af in asm_files:
        if _write_if_changed(work / af.name, af.read_bytes()):
            n_asm_changed += 1
    t0 = _t(f"copy asm ({n_asm_changed}/{len(asm_files)} changed)", t0)

    # Pre-scan .asm declarations.  Their PUBLIC names are already
    # *defined* by the asm objects — we must not auto-stub them on
    # the C side.  Their EXTRN <name>: BYTE entries become extra
    # data symbols the unified stubs.c needs to provide.
    asm_publics: set[str] = set()
    asm_extern_data: set[str] = set()
    asm_extern_proc: set[str] = set()
    for af in asm_files:
        p, ed, ep = _parse_asm_decls(af)
        asm_publics |= p
        asm_extern_data |= ed
        asm_extern_proc |= ep

    # Collect defined symbols and all extern needs across all files
    defined: set[str] = set()
    all_extern_decls: dict[str, object] = {}  # name → AST Decl node
    gen = _get_generator()

    n_c_changed = 0
    t_strip = 0.0
    t_parse = 0.0
    for cf in c_files:
        source_text = cf.read_text(errors="replace")

        # Write stripped source (STUB bodies removed).  Stub bodies are
        # converted to forward declarations so the compiler can't see
        # an empty body and inline / tail-merge the call site away.
        # Conditional write keeps mtime stable for unchanged files →
        # wmake skips them.
        ts = time.perf_counter()
        stripped = _strip_stub_bodies(source_text)
        t_strip += time.perf_counter() - ts
        if _write_if_changed(work / cf.name, stripped.encode()):
            n_c_changed += 1

        # Parse the STRIPPED source to find which symbols are actually
        # *defined* in the compiled translation unit.  Stripped STUBs
        # become forward decls and therefore must be re-supplied by
        # the auto-generated stubs.c (or via clib3r), not skipped.
        ts = time.perf_counter()
        try:
            ast = _parse_c(stripped, cf.name)
            decls = _classify(ast)
            for d in decls.owned_vars:
                if d.name:
                    defined.add(d.name)
            for d in decls.func_defs:
                if d.decl.name:
                    defined.add(d.decl.name)
            for d in decls.extern_vars + decls.extern_fns + decls.forward_fns:
                if d.name and d.name not in all_extern_decls:
                    all_extern_decls[d.name] = d
        except pycparser.c_parser.ParseError:
            pass
        t_parse += time.perf_counter() - ts
    if timings:
        typer.echo(f"  ⏱  strip_stub_bodies all .c       {t_strip:5.2f}s",
                   err=True)
        typer.echo(f"  ⏱  pycparser-parse all .c         {t_parse:5.2f}s",
                   err=True)
        typer.echo(
            f"  ⏱  write stripped .c "
            f"({n_c_changed}/{len(c_files)} changed)",
            err=True,
        )
    t0 = time.perf_counter()

    # Also parse headers for extern declarations.
    # Hand-written headers take priority over the auto-generated
    # ``c2_data.h`` / ``c2_funcs.h`` -- they may provide struct-typed
    # declarations that override generic int[] types.
    _generated_headers = {"c2_data.h", "c2_funcs.h"}
    for h in include_dir.glob("*.h"):
        is_extra = (h.name not in _generated_headers)
        try:
            ast = _parse_c(h.read_text(), h.name)
            decls = _classify(ast)
            for d in decls.extern_vars + decls.extern_fns + decls.forward_fns:
                if d.name:
                    if is_extra or d.name not in all_extern_decls:
                        all_extern_decls[d.name] = d
        except pycparser.c_parser.ParseError:
            pass
    t0 = _t("pycparser-parse all headers", t0)

    # Look up which symbols the Watcom CRT (clib3r.lib) already
    # provides, so we don't redundantly auto-stub them.  The real
    # library bodies for printf/exit/free/memcpy/… then take effect
    # at link time when a .c file does `#include <stdio.h>` etc.
    # The first call probes the container; subsequent runs read the
    # cached symbol list from decomp/lib/clib3r-symbols.txt.
    clib3r = _load_clib3r_symbols(image)
    t0 = _t("load clib3r symbols", t0)

    # Generate unified stubs: everything extern that isn't defined
    stubs_parts: list[str] = [
        "/* Auto-generated unified stubs */\n",
    ]
    # Include hand-written headers for struct types (the auto-generated
    # ``c2_data.h`` is already pulled in by every source TU; the stubs
    # file only needs the rest).
    for h in include_dir.glob("*.h"):
        if h.name not in {"c2_data.h"}:
            stubs_parts.append(f'#include "{h.name}"')
    stubs_parts.append("")

    # ``__stub_log`` is the shared write target every STUB-annotated
    # function stores its PS.EXE address into (see strip_stub_bodies()).
    # The ``volatile`` qualifier prevents Watcom 10.0a from eliding the
    # write as dead code, and the per-stub immediate keeps every
    # compiled body unique so the linker can't fold them.  Definition
    # lives in this stubs.c — a separate TU — so callers in source
    # files only see the ``extern volatile int __stub_log`` decl that
    # ``strip_stub_bodies()`` re-emits inside each stub body.
    stubs_parts.append("volatile int __stub_log;\n")

    for name, decl_node in sorted(all_extern_decls.items()):
        if name in defined:
            continue
        # An asm module already defines this symbol — don't stub it
        # again on the C side.  C-name 'foo'  → linker 'foo_' (watcall)
        # or '_foo' (cdecl/data); both forms must be checked.
        if (
            (name + "_") in asm_publics
            or ("_" + name) in asm_publics
            or name in asm_publics
        ):
            continue
        if _is_clib3r_provided(name, clib3r):
            continue   # let the linker pull the real CRT body
        stub_node = _decl_to_stub(decl_node)
        if isinstance(stub_node, c_ast.FuncDef):
            text = gen.visit(stub_node)
            # Re-inject the calling-convention keyword that pycparser
            # discarded, so the stub links as the same symbol the call
            # site emits (e.g. __pascal SmackOpen → SMACKOPEN).
            kw = conv_map.get(name)
            if kw:
                text = _inject_convention(text, name, kw)
            pq = ptr_qual_map.get(name)
            if pq:
                text = _inject_pointer_qualifier(text, name, pq)
            stubs_parts.append(text)
        else:
            stubs_parts.append(gen.visit(stub_node) + ";")

    # Asm-side EXTRN data symbols whose base name isn't declared in
    # any header or .c file (e.g. ``_sndinit``: a file-scope variable
    # that lives in one of the still-undecompiled modules).  We emit a
    # 4-byte tentative definition here so the linker can resolve the
    # asm's ``EXTRN _name: BYTE``.  Watcom mangles ``int name;`` to
    # ``_name`` — matches the asm extern.
    for raw in sorted(asm_extern_data):
        # Strip the C-side leading underscore for the source declaration
        if not raw.startswith("_"):
            continue
        c_name = raw[1:]
        # Already defined (in .c source or stubs.c above)?  Skip.
        if c_name in defined or raw in asm_publics:
            continue
        # Already declared in any header?  Skip — the auto-stubs loop
        # above will have emitted a definition for it.
        if c_name in all_extern_decls:
            continue
        # Otherwise it's an asm-only base symbol.  Emit a 4-byte
        # tentative definition.
        stubs_parts.append(f"int {c_name};")

    stubs_text = "\n".join(stubs_parts) + "\n"
    stubs_changed = _write_if_changed(work / "stubs.c", stubs_text.encode())
    _write_if_changed(work / "entry.c", b"void _entry_(void) {}\n")
    t0 = _t(f"generate stubs.c (changed={stubs_changed})", t0)

    # Link script: all source .obj files (including .asm-derived ones)
    # + stubs + entry.  Pull in the Watcom 10.0a 386-register CRT
    # (clib3r.lib) so that compiler-emitted helper calls (__STOSB /
    # __STOSD / __CHK / __STK / etc.) resolve naturally instead of
    # becoming undefined symbols.
    #
    # The .c objects are listed in PS MODULE ORDER (not alphabetical):
    # wlink concatenates _TEXT in FILE order, and Watcom dumps a
    # function's switch/scan tables just before its entry label, so a
    # module's FIRST function's tables physically precede the module --
    # i.e. they land inside the PREVIOUS module's last symbol extent.
    # Matching PS's module adjacency makes those extents compare
    # naturally (worked example: stop_system, last fn of lib32.c, whose
    # extent holds sim_mouse's two scan tables -- hotkeys.c must follow
    # lib32.c like in PS).  See _ps_link_order for the key derivation
    # (annotation-less data-only TUs keep their alphabetical slot, which
    # preserves the Rule 45 smackinp-after-smacker SYM_TEMP pad).
    c_obj_files   = [cf.stem + ".obj" for cf in _ps_link_order(c_files)]
    asm_obj_files = [af.stem + ".obj" for af in asm_files]
    obj_files     = c_obj_files + asm_obj_files + ["stubs.obj", "entry.obj"]
    lnk_lines = [
        "DEBUG ALL",
        "FORMAT os2 le",
        "OPTION MAP=out.map",
        "OPTION QUIET",
        "NAME out.exe",
        "LIBPATH Z:\\opt\\watcom\\lib386;Z:\\opt\\watcom\\lib386\\dos",
        "LIBRARY clib3r.lib",
    ]
    for obj in obj_files:
        lnk_lines.append(f"FILE {obj}")
    lnk_text = "\n".join(lnk_lines) + "\n"
    _write_if_changed(work / "out.lnk", lnk_text.encode())

    # ── wmake driver ────────────────────────────────────────────────
    # Drop a makefile that:
    #   * declares every .obj as depending on its .c plus *every*
    #     header (pessimistic but simple — header edits invalidate
    #     every .obj, which matches our behaviour pre-cache);
    #   * declares out.exe as depending on every .obj plus the .lnk.
    #
    # ``wmake`` then builds only what's stale.  When nothing changed
    # the container call is just the wmake banner (~280 ms total).
    headers_str = " ".join(h.name for h in header_files)
    # ``makefile`` is listed as a dependency of every .obj rule so
    # that flipping cflags (which change the makefile body) forces a
    # full rebuild — wmake compares mtimes, and our _write_if_changed
    # only bumps the makefile mtime when content actually differs.
    mk_lines = [
        f"CFLAGS = {cflags}",
        "",
        "all : out.exe .SYMBOLIC",
        "",
        "out.exe : " + " ".join(obj_files) + " out.lnk",
        "    wlink @out.lnk",
        "",
    ]
    for cf in c_files:
        mk_lines.append(f"{cf.stem}.obj : {cf.name} {headers_str} makefile")
        mk_lines.append(f"    wcc386 $(CFLAGS) -fo=$^@ $[@")
        mk_lines.append("")
    mk_lines.append(f"stubs.obj : stubs.c {headers_str} makefile")
    mk_lines.append(f"    wcc386 $(CFLAGS) -fo=$^@ $[@")
    mk_lines.append("")
    mk_lines.append(f"entry.obj : entry.c makefile")
    mk_lines.append(f"    wcc386 $(CFLAGS) -fo=$^@ $[@")
    mk_lines.append("")
    # .asm rules.  WASM 10.0a rejects `-mf` / `-bt=dos` / `-3r`
    # because the .asm files declare `.MODEL FLAT` themselves, so we
    # invoke wasm with no flags — it's a 32-bit flat-model assembler
    # by default and matches what produced the original PS.EXE bytes.
    for af in asm_files:
        mk_lines.append(f"{af.stem}.obj : {af.name} makefile")
        mk_lines.append(f"    wasm -fo=$^@ $[@")
        mk_lines.append("")
    mk_text = "\n".join(mk_lines)
    _write_if_changed(work / "makefile", mk_text.encode())
    t0 = _t("write makefile + lnk", t0)

    # ── host-side build driver (wibo pivot, 2026-06-12) ────────────
    # NT wmake under wibo cannot enumerate directories (FindFirstFileA
    # "*.*" is a partial stub) so it never finds the makefile.  The
    # makefile above is still WRITTEN -- its mtime is the cflags stamp
    # (_write_if_changed bumps it only on content change) -- but the
    # dirty-set computation and the build loop now run HOST-side with
    # exactly wmake's dependency semantics:
    #   X.obj   : X.c <headers> makefile        (entry.obj: no headers)
    #   out.exe : <objs> out.lnk
    # Each step echoes its command line into the output (`wcc386 ... X.c`)
    # because parse_build_trace segments per-TU trace blocks by those
    # echo lines, exactly as wmake's command echo did.

    def _mtime(p: Path) -> int:
        # NANOSECOND mtimes: with sub-second probe->build turnarounds a
        # second-granularity comparison let a just-edited source look
        # no-newer than its obj (stale-build race, observed live on the
        # get_linked_page probe sequence).
        try:
            return p.stat().st_mtime_ns
        except OSError:
            return -1

    def _stale(obj: str, deps: list[Path]) -> bool:
        ot = _mtime(work / obj)
        return ot < 0 or any(_mtime(d) >= ot for d in deps)

    mk_dep = work / "makefile"
    hdr_deps = [work / h.name for h in header_files]
    steps: list[tuple[str, list[Path], str]] = []
    for cf in c_files:
        steps.append((f"{cf.stem}.obj", [work / cf.name, *hdr_deps, mk_dep],
                      f"wcc386 {cflags} -fo={cf.stem}.obj {cf.name}"))
    steps.append(("stubs.obj", [work / "stubs.c", *hdr_deps, mk_dep],
                  f"wcc386 {cflags} -fo=stubs.obj stubs.c"))
    steps.append(("entry.obj", [work / "entry.c", mk_dep],
                  f"wcc386 {cflags} -fo=entry.obj entry.c"))
    for af in asm_files:
        steps.append((f"{af.stem}.obj", [work / af.name, mk_dep],
                      f"wasm -fo={af.stem}.obj {af.name}"))

    def _host_build(timeout: int) -> tuple[bool, str]:
        out_parts: list[str] = []
        built_any = False
        for obj, deps, cmd in steps:
            if not _stale(obj, deps):
                continue
            built_any = True
            out_parts.append(cmd)               # the TU segmentation echo
            st_ok, st_out = _run_in_container(work, image, cmd,
                                              timeout=timeout)
            out_parts.append(st_out)
            if not st_ok or "Error!" in st_out:
                # wmake -e semantics: never leave a half-written target
                (work / obj).unlink(missing_ok=True)
                return False, "\n".join(out_parts)
        exe = work / "out.exe"
        if built_any or _stale("out.exe", [work / o for o in obj_files] +
                               [work / "out.lnk"]):
            out_parts.append("wlink @out.lnk")
            st_ok, st_out = _run_in_container(work, image, "wlink @out.lnk",
                                              timeout=timeout)
            out_parts.append(st_out)
            if not st_ok or "Error!" in st_out or not exe.exists():
                exe.unlink(missing_ok=True)
                return False, "\n".join(out_parts)
        return True, "\n".join(out_parts)

    # ``wmake -h``  : suppress the program header banner.
    # ``wmake -e``  : erase failed-build outputs *without* prompting
    #                 — without this, a wcc386 compile error makes
    #                 wmake interactively ask "Should this file be
    #                 deleted [Yes/No]?", which blocks forever in
    #                 the headless dosemu2 container.
    # WCGMEMORY hook: PROVEN NO-OP.  The compiler's low-memory path is
    # unreachable in this toolchain -- the W32RUN extender reports a fixed
    # pool regardless of WCGMEMORY / dosemu $_dpmi / qemu -m, so it cannot
    # be triggered (and it was never the cause of any codegen diff anyway;
    # see docs/watcom-codegen-patterns.md s memory).  Kept only as a
    # harmless opt-in placeholder; do not rely on it.  The SET still
    # propagates (a batch `set WCGMEMORY=#` makes wcc386 print "Maximum
    # WCGMEMORY=").
    # A COLD build compiles all ~37 files under the DOS extender (each wcc386
    # launch re-bootstraps the 540 KB TNT image -> ~3 s/file, ~2 min total).
    # The default 120 s timeout SIGKILLed it right before completion, so the
    # cache (out.exe) never got stamped -> EVERY run started cold again (the
    # "always busy 2 min" loop). Give the build room to finish once; after that
    # wmake rebuilds only changed files and runs are fast/incremental.
    _build_to = int(os.environ.get("C2_BUILD_TIMEOUT", "900"))
    if os.environ.get("C2_WCGMEMORY"):
        # retired with the dosemu2 images (bat execution; proven no-op hook)
        print("[!] C2_WCGMEMORY ignored: bat path retired with the DOS images")
    ok, all_output = _host_build(_build_to)
    t0 = _t("host build driver (wcc386/wlink)", t0)

    # Capture the register-allocation trace straight from THIS build (the
    # -trace image emits ~WV1 lines, segmented per TU by wmake's `wcc386 ... X.c`
    # command echo).  No duplicate compiles: the hint layer consumes the build's
    # own output, parsed once and persisted per function so incremental builds
    # only refresh the files that recompiled.  Then strip ~WV1 from the build log.
    try:
        from c2 import regalloc as _ra
        _rt_cache = _BUILD_DIR / "regtrace.json"
        if "~WV1 " in all_output:
            _sources = {cf.name: (work / cf.name).read_text(errors="replace")
                        for cf in c_files if (work / cf.name).exists()}
            _parsed = _ra.parse_build_trace(all_output, _sources)
            _data = _ra.update_cache(_rt_cache, _parsed)   # merge into persisted
            all_output = "\n".join(ln for ln in all_output.splitlines()
                                   if not ln.startswith("~WV1 "))
        elif "trace" in image:
            _data = _ra.load_cache(_rt_cache)   # trace-image no-op -> persisted full trace
        else:
            _data = None    # stock build -> no active trace; regalloc hints use
                            # the on-demand per-file fallback (always fresh)
        if _data:
            _ra.set_active(_ra.RegallocTrace(_data))
    except Exception as _e:
        # NEVER fully silent: a swallowed failure here kept the corpus trace
        # cache stale for days (IRForest json.dumps TypeError) while every
        # hint quietly fell back to slow per-file container compiles.
        typer.secho(f"  [!] build-trace capture failed ({_e!r}) -- regalloc "
                    "hints will fall back to per-file compiles",
                    fg="yellow", err=True)
        if os.environ.get("C2_DEBUG_REGALLOC"):
            import traceback
            traceback.print_exc()
    t0 = _t("capture regalloc trace", t0)

    # Check for actual errors in output
    if not ok or "Error!" in all_output:
        ok = False
    if "undefined symbol" in all_output:
        ok = False
    if ok and not (work / "out.exe").exists():
        ok = False

    # Concurrent-edit guard: if any build INPUT changed after we sampled
    # the sources (another session editing the shared tree, or the user
    # saving mid-build), the freshly-linked exe does NOT correspond to the
    # sources on disk -- comparing it would silently verify the WRONG code
    # (the get_battle_centuries_left staleness incident, 2026-06-10).
    # Fail loudly and force-stale the exe so the make fast path can never
    # trust it.
    if ok:
        changed = []
        try:
            inputs = (list(src_dir.glob("*.c")) + list(src_dir.glob("*.asm"))
                      + list(include_dir.glob("*.h")))
            changed = [f.name for f in inputs
                       if f.stat().st_mtime > build_start_wall]
        except OSError:
            pass
        if changed:
            ok = False
            try:
                import os as _os
                _os.utime(work / "out.exe", (1, 1))   # force-stale
            except OSError:
                pass
            all_output += (
                "\nsource changed DURING the build (concurrent session or "
                "mid-build save): " + ", ".join(sorted(changed)[:8])
                + "\nthe linked exe does not match the sources on disk -- "
                "rerun the command.")

    # Record the build config so the next call's make-style fast path can
    # detect a cflags/image change (which must force a full rebuild) and,
    # when unchanged, skip the container entirely.  Only meaningful for
    # the persistent cache dir; harmless in a tempdir.
    if ok and use_cache:
        try:
            (work / ".build_config").write_text(f"{cflags}\x00{image}")
            # Stamp out.exe to the build-start instant.  wmake leaves
            # out.exe untouched on a no-op build (content-stable staging),
            # so without this a `touch`ed-but-unchanged source would look
            # perpetually newer than the binary and defeat the fast path.
            import os as _os
            _os.utime(work / "out.exe", (build_start_wall, build_start_wall))
        except OSError:
            pass

    return ok, all_output, work


# ── Map file parser ────────────────────────────────────────────────────────────

_MAP_SYM_RE = re.compile(r"^0001:([0-9A-Fa-f]{8})[* +]?\s+(\S+)")


def _parse_map(map_path: Path) -> dict[str, int]:
    """Parse a WLINK .map file → {mangled_name: code_section_offset}."""
    syms: dict[str, int] = {}
    for line in map_path.read_text(errors="replace").splitlines():
        m = _MAP_SYM_RE.match(line)
        if m:
            syms[m.group(2)] = int(m.group(1), 16)
    return syms


# ── LE code section + fixup extractor ─────────────────────────────────────────

def _load_le_code_and_fixups(exe_path: Path) -> tuple[bytes, set[int]]:
    """Extract code section bytes + fixup byte-offset set from an LE exe.

    Memoised by (path, mtime, size): both PS.EXE and the recompiled out.exe are
    re-parsed many times across a verify run (123x in a profile); the result is
    read-only (the fixup set is only membership-tested), so caching is safe and
    cuts several seconds off ``-v``."""
    st = exe_path.stat()
    return _load_le_code_and_fixups_cached(str(exe_path), st.st_mtime_ns, st.st_size)


@lru_cache(maxsize=8)
def _load_le_code_and_fixups_cached(path_str: str, _mtime_ns: int,
                                    _size: int) -> tuple[bytes, set[int]]:
    exe_path = Path(path_str)
    from c2.parsers.exe import parse_exe
    from c2.commands.fixups import parse_le_fixups

    _, bw_headers, le = parse_exe(exe_path)

    code_fm, _ = parse_le_fixups(
        exe_path,
        le.le_offset,
        le.page_size,
        le.num_pages,
        le.objects[0].num_pages,
        le.objects[1].num_pages,
    )
    fix_bytes: set[int] = set()
    for off in code_fm:
        for k in range(4):
            fix_bytes.add(off + k)

    code_bin = _extract_le_code(exe_path, le)
    return code_bin, fix_bytes


def _extract_le_code(exe_path: Path, le) -> bytes:
    """Read the raw code-section pages from an LE executable."""
    raw  = exe_path.read_bytes()
    obj  = le.objects[0]
    off  = le.object_file_offset(obj)
    size = le.object_file_size(obj)
    return raw[off : off + size]


# ── Comparison helpers ─────────────────────────────────────────────────────────

def _rel_call_jmp_disp_mask(code: bytes) -> set[int]:
    """Return byte offsets within `code` belonging to the displacement field
    of a cross-function relative call/jump.

    Masks:
      - `E8 rel32` (call)        — always cross-function; 4 disp bytes.
      - `E9 rel32` (jmp)         — always cross-function; 4 disp bytes.
      - `0F 8x rel32` (Jcc long) — only if target lies outside the function,
        which happens when Watcom's linker tail-merges shared epilogues.

    These bytes hold link-time-resolved displacements that differ between
    PS.EXE and the small testbench because the call target lands at a
    different physical address — even though the compiler-emitted
    instruction is identical. Masking them eliminates purely link-
    positional noise from the byte-diff counter.
    """
    mask: set[int] = set()
    n = len(code)
    for insn in _CS.disasm(code, 0):
        # E8 rel32 (call) — always cross-function.
        # E9 rel32 (jmp)  — always cross-function (tail call).
        if insn.size == 5 and insn.bytes[0] in (0xE8, 0xE9):
            for k in range(1, 5):
                mask.add(insn.address + k)
            continue
        # EB rel8 (short jmp) and 7x rel8 (short Jcc): mask only if target
        # lies outside the function (cross-function tail-call/epilogue jump).
        if insn.size == 2 and (insn.bytes[0] == 0xEB or 0x70 <= insn.bytes[0] <= 0x7F):
            disp = int.from_bytes(insn.bytes[1:2], "little", signed=True)
            target = insn.address + insn.size + disp
            if target < 0 or target >= n:
                mask.add(insn.address + 1)
            continue
        # 0F 8x rel32 (long Jcc): mask only if target lies outside function
        # (Watcom's linker tail-merges shared epilogues across functions).
        if insn.size == 6 and insn.bytes[0] == 0x0F and 0x80 <= insn.bytes[1] <= 0x8F:
            disp = int.from_bytes(insn.bytes[2:6], "little", signed=True)
            target = insn.address + insn.size + disp
            if target < 0 or target >= n:
                for k in range(2, 6):
                    mask.add(insn.address + k)
    return mask


def _branch_target_audit(
    orig: bytes,
    recomp: bytes,
    orig_off: int,
    recomp_off: int,
    orig_fix: set[int],
    recomp_fix: set[int],
    ps_resolve,
    rc_resolve,
) -> list[dict]:
    """Symbolic audit of the rel-branch displacement fields the byte
    comparison deliberately masks.

    A masked rel32/rel8 can hide a call/jump to the WRONG symbol, or to
    a different canonical ComTail merge point that includes/excludes
    whole call statements (worked example: ``act_set_patrol_stop``'s
    spurious ``save_undo_info`` call compiled byte-"exact" under the
    mask — only the merged-tail jmp displacement differed, targeting
    ``act_set_patrol_markers+0x140`` instead of PS's ``+0x145``).

    Call ONLY on functions whose masked comparison is exact (identical
    instruction streams).  Disassembles the PS side once; for every
    displacement field the mask hides (E8/E9 rel32 always; Jcc/short
    forms when the target leaves the function), reads the field from
    BOTH sides and resolves each target to (alias-name-set, delta) in
    its own address space.  No shared alias or a different delta =
    a REAL divergence the byte oracle cannot see.

    ``ps_resolve(abs_code_off)`` / ``rc_resolve(abs_code_off)`` →
    (frozenset[str] normalized names, int delta) or None.
    """
    n = len(orig)
    sites: list[dict] = []
    for insn in _CS.disasm(orig, 0):
        fld_lo = fld_hi = None
        mnem = insn.mnemonic
        if insn.size == 5 and insn.bytes[0] in (0xE8, 0xE9):
            fld_lo, fld_hi = insn.address + 1, insn.address + 5
        elif (insn.size == 6 and insn.bytes[0] == 0x0F
                and 0x80 <= insn.bytes[1] <= 0x8F):
            disp = int.from_bytes(insn.bytes[2:6], "little", signed=True)
            if not (0 <= insn.address + 6 + disp < n):
                fld_lo, fld_hi = insn.address + 2, insn.address + 6
        elif insn.size == 2 and (insn.bytes[0] == 0xEB
                                 or 0x70 <= insn.bytes[0] <= 0x7F):
            disp = int.from_bytes(insn.bytes[1:2], "little", signed=True)
            if not (0 <= insn.address + 2 + disp < n):
                fld_lo, fld_hi = insn.address + 1, insn.address + 2
        if fld_lo is None or fld_hi > len(recomp):
            continue
        # Skip fields overlapping loader fixups on either side (a fake
        # "branch" decoded from an in-function data table).
        if any((orig_off + k) in orig_fix or (recomp_off + k) in recomp_fix
               for k in range(fld_lo, fld_hi)):
            continue
        width = fld_hi - fld_lo
        o_disp = int.from_bytes(orig[fld_lo:fld_hi], "little", signed=True)
        r_disp = int.from_bytes(recomp[fld_lo:fld_hi], "little", signed=True)
        end = insn.address + insn.size
        ps_t = orig_off + end + o_disp
        rc_t = recomp_off + end + r_disp
        ps_r = ps_resolve(ps_t)
        rc_r = rc_resolve(rc_t)
        if ps_r is None or rc_r is None:
            continue          # out-of-range target (pad/junk decode)
        ps_names, ps_delta = ps_r
        rc_names, rc_delta = rc_r
        if ps_names & rc_names and ps_delta == rc_delta:
            continue
        ps_n = min(ps_names) if ps_names else "?"
        rc_n = min(rc_names) if rc_names else "?"
        sites.append({
            "insn_off": insn.address,
            "mnem": mnem,
            "width": width,
            "ps_target": f"{ps_n}+{ps_delta:#x}" if ps_delta else ps_n,
            "rc_target": f"{rc_n}+{rc_delta:#x}" if rc_delta else rc_n,
        })
    return sites


def _compare_bytes(
    orig: bytes,
    recomp: bytes,
    orig_off: int,
    recomp_off: int,
    orig_fix: set[int],
    recomp_fix: set[int],
) -> list[int]:
    """Return list of offsets where bytes differ.

    Masks both LE-fixup bytes (loader-patched absolute addresses) and
    relative-call/jmp displacement bytes (link-positional noise).
    """
    n = min(len(orig), len(recomp))
    rel_orig   = _rel_call_jmp_disp_mask(orig[:n])
    rel_recomp = _rel_call_jmp_disp_mask(recomp[:n])
    diffs: list[int] = []
    for i in range(n):
        if i in rel_orig or i in rel_recomp:
            continue
        o = 0 if (orig_off + i)   in orig_fix   else orig[i]
        r = 0 if (recomp_off + i) in recomp_fix else recomp[i]
        if o != r:
            diffs.append(i)
    return diffs


_JCC_OPCODES_1B = set(range(0x70, 0x80))           # 7x rel8  Jcc short
_JCC_OPCODES_2B_PREFIX = 0x0F                     # 0F 8x rel32  Jcc near
_JMP_NEAR_OPCODE = 0xE9                           # E9 rel32  jmp
_JMP_SHORT_OPCODE = 0xEB                          # EB rel8   jmp short
_CALL_NEAR_OPCODE = 0xE8                          # E8 rel32  call
_POP_REG_OPCODES = set(range(0x58, 0x60))         # pop eax..edi
_RET_OPCODES = {0xC3, 0xC2}                       # ret  /  ret imm16


def _is_jcc(raw: bytes) -> bool:
    if not raw:
        return False
    if raw[0] in _JCC_OPCODES_1B:
        return True
    if len(raw) >= 2 and raw[0] == _JCC_OPCODES_2B_PREFIX:
        return 0x80 <= raw[1] <= 0x8F
    return False


def _is_jmp(raw: bytes) -> bool:
    return bool(raw) and raw[0] in (_JMP_NEAR_OPCODE, _JMP_SHORT_OPCODE)


def _is_call(raw: bytes) -> bool:
    return bool(raw) and raw[0] == _CALL_NEAR_OPCODE


def _is_branch(raw: bytes) -> bool:
    """Any rel8/rel32 control transfer: jmp, jcc, call.  The rel
    displacement bytes shift with layout; a same-mnemonic-same-length
    diff in such instructions is layout cascade, not body divergence."""
    return _is_jmp(raw) or _is_jcc(raw) or _is_call(raw)


def _jmp_target_in_function(insn_rel_off: int, raw: bytes, func_size: int) -> bool:
    """True if a near/short jmp's target lies INSIDE this function body."""
    if not raw or raw[0] not in (_JMP_NEAR_OPCODE, _JMP_SHORT_OPCODE):
        return False
    if raw[0] == _JMP_SHORT_OPCODE and len(raw) >= 2:
        # EB rel8 -- signed offset from end of insn
        disp = raw[1] if raw[1] < 0x80 else raw[1] - 0x100
        end = insn_rel_off + len(raw)
        tgt = end + disp
    elif raw[0] == _JMP_NEAR_OPCODE and len(raw) >= 5:
        disp = int.from_bytes(raw[1:5], "little", signed=True)
        end = insn_rel_off + len(raw)
        tgt = end + disp
    else:
        return False
    return 0 <= tgt < func_size


def _is_stack_unwind(insn: InsnT) -> bool:
    """True for a frame-cleanup instruction allowed BEFORE the pop run:
    `add esp, imm8/imm32` or `mov esp, ebp` or `leave`.  These finalise
    the stack frame and are functionally part of the epilogue."""
    if not insn[2]:
        return False
    raw = insn[2]
    if raw[0] == 0xC9:        # leave
        return True
    if (len(raw) >= 3 and raw[0] in (0x83, 0x81)
            and (raw[1] & 0xF8) == 0xC0
            and (raw[1] & 0x07) == 0x04):
        # add/sub esp, imm8 (0x83 /0,/5 esp) or imm32 (0x81); we only
        # care about ADD (subop 0).
        subop = (raw[1] >> 3) & 0x07
        return subop == 0     # ADD esp, imm
    # mov esp, ebp -> 89 ec
    if len(raw) >= 2 and raw[0] == 0x89 and raw[1] == 0xEC:
        return True
    return False


def _is_retval_setup(insn: InsnT) -> bool:
    """True for a return-value setup instruction allowed BEFORE the pop
    run: `mov eax, imm32` (0xB8) or `mov al, imm8` (0xB0) or `xor eax,
    eax` (0x31 0xC0).  These set up the return value just before the
    epilogue, a common foreign-jmp donor pattern."""
    if not insn[2]:
        return False
    raw = insn[2]
    # mov eax, imm32 -> B8 .. .. .. ..
    if len(raw) == 5 and raw[0] == 0xB8:
        return True
    # mov al, imm8 -> B0 ..
    if len(raw) == 2 and raw[0] == 0xB0:
        return True
    # xor eax, eax -> 31 C0
    if len(raw) == 2 and raw[0] == 0x31 and raw[1] == 0xC0:
        return True
    return False


def _is_inline_epilogue(insns: list[InsnT], i: int) -> int:
    """If insns[i:] begins an inline epilogue, return the number of
    instructions it spans; else 0.  Accepted form:

      [retval setup]  [frame cleanup]  pop reg+  [ret]

    retval setup is at most ONE of `mov eax, imm` / `mov al, imm` /
    `xor eax, eax` (the return value).  frame cleanup is at most ONE
    of `add esp, N` / `mov esp, ebp` / `leave`.  >=1 pop reg required.
    `ret` / `ret imm16` optional."""
    j = i
    if j < len(insns) and _is_retval_setup(insns[j]):
        j += 1
    if j < len(insns) and _is_stack_unwind(insns[j]):
        j += 1
    n_pop = 0
    while j < len(insns) and insns[j][2] and insns[j][2][0] in _POP_REG_OPCODES:
        n_pop += 1
        j += 1
    if n_pop == 0:
        return 0
    if j < len(insns) and insns[j][2] and insns[j][2][0] in _RET_OPCODES:
        return j + 1 - i
    return 0


def _is_epilogue_prefix(insns: list[InsnT], i: int, end_i: int) -> int:
    """Like _is_inline_epilogue, but accepts a TRUNCATED epilogue whose
    tail (pops / ret) lies past the function-symbol boundary -- the
    recomp emits the full sequence but the symbol only carries part of
    it.  Returns the number of instructions consumed within [i, end_i).

    Accepts:
      retval setup ONLY (truncated before cleanup/pops)
      retval setup + cleanup ONLY (truncated before pops)
      retval setup + cleanup + 0+ pops (truncated before ret)
      retval setup + cleanup + 0+ pops + ret (full)
    plus the same forms without the retval setup.  At least one of
    retval-setup, cleanup, or pop must be present."""
    j = i
    have_retval = False
    if j < end_i and _is_retval_setup(insns[j]):
        have_retval = True
        j += 1
    have_cleanup = False
    if j < end_i and _is_stack_unwind(insns[j]):
        have_cleanup = True
        j += 1
    n_pop = 0
    while j < end_i and insns[j][2] and insns[j][2][0] in _POP_REG_OPCODES:
        n_pop += 1
        j += 1
    if not (have_retval or have_cleanup or n_pop > 0):
        return 0
    if j < end_i and insns[j][2] and insns[j][2][0] in _RET_OPCODES:
        j += 1
    return j - i


def _instr_kind(insn: InsnT) -> tuple[str, int]:
    """Coarse instruction-equivalence key: (mnemonic head, length).
    Two instructions with the same kind are the same operation modulo
    immediates, displacements, and register operands -- enough to walk
    PS and RC streams in lockstep even when downstream offsets drift
    from a Rule 16 encoding cascade."""
    if not insn[2] or not insn[3]:
        return ("", insn[1])
    return (insn[3].split(None, 1)[0], insn[1])


def _epilogue_len(insns: list[InsnT], k: int, end_k: int) -> int:
    """Length of the inline epilogue starting at insns[k]: an optional
    single retval setup (`mov eax,imm` / `mov al,imm` / `xor eax,eax`),
    an optional single frame-cleanup (`add esp,N` / `mov esp,ebp` /
    `leave`), followed by >=1 `pop reg`, optionally followed by `ret`/
    `ret imm16`.  Returns 0 if no epilogue."""
    n = 0
    # optional single retval setup
    if k + n < end_k and _is_retval_setup(insns[k + n]):
        n += 1
    # optional single frame-cleanup
    if k + n < end_k and _is_stack_unwind(insns[k + n]):
        n += 1
    pops_started = n
    while (k + n < end_k
           and insns[k + n][2]
           and insns[k + n][2][0] in _POP_REG_OPCODES):
        n += 1
    if n == pops_started:
        # no actual pop run; not an epilogue
        return 0
    if (k + n < end_k
            and insns[k + n][2]
            and insns[k + n][2][0] in _RET_OPCODES):
        n += 1
    return n if n > 0 else 0


def _donor_flip_exit_only(
    orig: bytes,
    recomp: bytes,
    diffs: list[int],
    orig_off: int = 0,
    recomp_off: int = 0,
    orig_fix: Optional[set[int]] = None,
    recomp_fix: Optional[set[int]] = None,
) -> Optional[str]:
    """True (returns a one-line note) when every byte diff is explained
    by a tail-merge donor selection difference between PS and the recomp.

    Walks the two instruction streams in lockstep.  At each step the
    pair must be either:

    (a) Same instruction kind (mnemonic + length) -- the same operation
        modulo immediates / displacements / globals.  Any byte diff
        inside an unmasked field is a downstream layout-shift cascade.
    (b) Rule 16 encoding swap: jmp/Jcc short on one side, near on the
        other (same condition).  Advance both.
    (c) Tail-merge donor flip: one side has a foreign-target jmp
        (target OUTSIDE the function), the other has an inline epilogue
        run (>=1 `pop reg` + optional `ret`).  Advance the jmp side by
        1 instruction and the epilogue side by N.  Foreign jmp on BOTH
        sides to different donors is also a donor flip.
    (d) Leakage: PS-side symbol size includes trailing bytes that
        belong to the NEXT function on the recomp side (recomp ended
        earlier).  These bytes are not a body diff of this function.

    Returns a short note string when the function qualifies, else None.
    This is the "jump-table filler" analogue for tail-merge: the body
    LOGIC is byte-equivalent; only the donor coupling differs.
    """
    if not diffs or len(orig) != len(recomp):
        return None
    diff_set = set(diffs)
    ps_fix_local = ({fx - orig_off for fx in orig_fix
                     if orig_off <= fx < orig_off + len(orig)}
                    if orig_fix is not None else set())
    rc_fix_local = ({fx - recomp_off for fx in recomp_fix
                     if recomp_off <= fx < recomp_off + len(recomp)}
                    if recomp_fix is not None else set())

    ps_insns = _disasm_for_diff(orig)
    rc_insns = _disasm_for_diff(recomp)

    def _real_end_idx(insns: list[InsnT]) -> int:
        last = -1
        for k, (_o, _s, raw, _asm) in enumerate(insns):
            if not raw:
                continue
            if (raw[0] in _RET_OPCODES
                    or raw[0] in (_JMP_NEAR_OPCODE, _JMP_SHORT_OPCODE)):
                last = k + 1
        return last if last > 0 else len(insns)

    ps_end_i = _real_end_idx(ps_insns)
    rc_end_i = _real_end_idx(rc_insns)
    ps_end_off = (ps_insns[ps_end_i - 1][0]
                  + ps_insns[ps_end_i - 1][1]) if ps_end_i else 0
    rc_end_off = (rc_insns[rc_end_i - 1][0]
                  + rc_insns[rc_end_i - 1][1]) if rc_end_i else 0

    foreign_flip_seen = False
    rule16_cascade = False

    i = j = 0
    while i < ps_end_i and j < rc_end_i:
        p = ps_insns[i]
        r = rc_insns[j]

        pk = _instr_kind(p)
        rk = _instr_kind(r)
        if pk == rk and pk[0]:
            # Same instruction kind.  Bytes can differ in two ways:
            #   1. The differing bytes are FIXUP-MASKED (mov from a
            #      different global address, call rel32, etc.) -- they
            #      didn't make it into the `diffs` list, so they're
            #      irrelevant to the donor-flip judgement.
            #   2. The differing bytes are NOT masked and appear in
            #      `diffs` -- e.g. a ModRM register byte (xor edx,edx
            #      vs xor eax,eax) or an immediate.  Those are genuine
            #      body divergence UNLESS they're in a branch/call rel
            #      displacement (layout-shift cascade).
            if p[2] == r[2]:
                i += 1
                j += 1
                continue
            # Within this aligned same-kind insn pair, ANY differing
            # byte at a position that is NOT fixup-masked on BOTH sides
            # is a real (non-layout) diff.  Branches / calls / jmp
            # encode rel displacements that always count as layout
            # cascade -- those are tolerated below.
            ps_unmasked = False
            for k in range(p[1]):
                if (k < len(p[2]) and k < len(r[2])
                        and p[2][k] != r[2][k]
                        and (p[0] + k) not in ps_fix_local
                        and (r[0] + k) not in rc_fix_local):
                    ps_unmasked = True
                    break
            mnem = pk[0]
            if mnem == "jmp":
                if (not _jmp_target_in_function(p[0], p[2], ps_end_off)
                        and not _jmp_target_in_function(r[0], r[2],
                                                       rc_end_off)):
                    foreign_flip_seen = True
                i += 1
                j += 1
                continue
            if mnem == "call" or _is_jcc(p[2]):
                i += 1
                j += 1
                continue
            if not ps_unmasked:
                # All differing bytes within this same-kind insn pair
                # are fixup-masked -- a layout-shift cascade, not a body
                # divergence.
                i += 1
                j += 1
                continue
            # Real (non-masked) diff bytes inside a non-branch, same-
            # kind insn pair -> genuine body divergence (reg swap,
            # immediate diff).
            return None

        # (b) Rule 16: Jcc encoding swap (short<->near, same condition).
        if _is_jcc(p[2]) and _is_jcc(r[2]):
            p_cond = (p[2][0] & 0x0F if p[2][0] in _JCC_OPCODES_1B
                      else p[2][1] & 0x0F)
            r_cond = (r[2][0] & 0x0F if r[2][0] in _JCC_OPCODES_1B
                      else r[2][1] & 0x0F)
            if p_cond == r_cond:
                rule16_cascade = True
                i += 1
                j += 1
                continue

        # (b) Rule 16: jmp short EB vs jmp near E9.
        if _is_jmp(p[2]) and _is_jmp(r[2]):
            rule16_cascade = True
            i += 1
            j += 1
            continue

        # (c) Donor flip: foreign jmp vs inline epilogue.
        ps_foreign = (_is_jmp(p[2])
                      and not _jmp_target_in_function(p[0], p[2],
                                                     ps_end_off))
        rc_foreign = (_is_jmp(r[2])
                      and not _jmp_target_in_function(r[0], r[2],
                                                     rc_end_off))
        if ps_foreign and rc_foreign:
            foreign_flip_seen = True
            i += 1
            j += 1
            continue
        if ps_foreign:
            n = _is_epilogue_prefix(rc_insns, j, rc_end_i)
            if n:
                foreign_flip_seen = True
                i += 1
                j += n
                continue
        if rc_foreign:
            n = _is_epilogue_prefix(ps_insns, i, ps_end_i)
            if n:
                foreign_flip_seen = True
                i += n
                j += 1
                continue

        # Genuine body divergence.
        return None

    # Trailing-side fold: leftover insns must be a tolerable donor-flip
    # remainder: a pop run optionally ended by ret or by a foreign jmp
    # (donor flip with extra fixup-restore prefix).  At the very tail of
    # a function the truncated `<raw>` entry whose first byte is the
    # near-jmp opcode (0xE9) counts as a foreign jmp -- the symbol-size
    # boundary cut off the rel32 disp.
    def _is_foreign_jmp_or_truncated(ins: InsnT, end_off: int) -> bool:
        raw = ins[2]
        if not raw:
            return False
        if raw[0] != _JMP_NEAR_OPCODE and raw[0] != _JMP_SHORT_OPCODE:
            return False
        if (raw[0] == _JMP_NEAR_OPCODE and len(raw) < 5) or (
                raw[0] == _JMP_SHORT_OPCODE and len(raw) < 2):
            return True               # truncated at function-size boundary
        return not _jmp_target_in_function(ins[0], raw, end_off)

    def _trailing_donor_ok(insns: list[InsnT], k: int, end_k: int,
                           end_off: int) -> bool:
        m = k
        # optional single retval setup
        if m < end_k and _is_retval_setup(insns[m]):
            m += 1
        # optional single frame cleanup
        if m < end_k and _is_stack_unwind(insns[m]):
            m += 1
        pops_start = m
        while m < end_k and insns[m][2] and insns[m][2][0] in _POP_REG_OPCODES:
            m += 1
        if m == end_k:
            return m > k
        last = insns[m]
        if last[2] and last[2][0] in _RET_OPCODES and m + 1 == end_k:
            return True
        if _is_foreign_jmp_or_truncated(last, end_off) and m + 1 == end_k:
            return True
        return False

    if i < ps_end_i:
        if not _trailing_donor_ok(ps_insns, i, ps_end_i, ps_end_off):
            return None
        foreign_flip_seen = True
    if j < rc_end_i:
        if not _trailing_donor_ok(rc_insns, j, rc_end_i, rc_end_off):
            return None
        foreign_flip_seen = True

    # (d) Leakage bytes are after BOTH natural ends (next-fn prologue).
    leak_bytes = sum(1 for d in diffs
                     if d >= max(ps_end_off, rc_end_off))

    if not (foreign_flip_seen or rule16_cascade or leak_bytes):
        return None
    parts: list[str] = []
    if foreign_flip_seen:
        parts.append("tail-merge donor flip")
    if rule16_cascade:
        parts.append("Rule 16 encoding cascade")
    if leak_bytes:
        parts.append(f"{leak_bytes} next-fn leak byte(s)")
    return "; ".join(parts)


_R4_JCC_FLIP: dict[str, str] = {
    "jl": "jg",   "jg": "jl",
    "jle": "jge", "jge": "jle",
    "jb": "ja",   "ja": "jb",
    "jbe": "jae", "jae": "jbe",
}


def _rule4_only_diffs(
    orig: bytes,
    recomp: bytes,
    diffs: list[int],
) -> Optional[int]:
    """Return Rule 4 site count when EVERY (fixup-unmasked) diff byte
    is explained by a ``cmp`` operand swap + complementary ``jcc``:

        PS: cmp a, b ; jl  L_x          // source `a < b`
        RC: cmp b, a ; jg  L_x          // source `b > a`

    Both branch identically; only the cmp ModRM/REG encoding and the
    Jcc opcode differ.  Source-level ambiguity, not body divergence.

    Algorithm: group the diff byte offsets by enclosing instruction.
    Every diff-bearing instruction pair must be either (a) a ``cmp``
    with REG-swapped operands or (b) a complementary Jcc whose
    preceding insn is a Rule 4 cmp swap.  Returns the Rule 4 site
    count or None.
    """
    if not diffs or len(orig) != len(recomp):
        return None
    ps = _disasm_for_diff(orig)
    rc = _disasm_for_diff(recomp)
    if len(ps) != len(rc):
        return None
    # Map each diff byte to its enclosing PS instruction index.
    diff_set = set(diffs)
    insn_indices_with_diff: set[int] = set()
    for k, (po, sz, _raw, _asm) in enumerate(ps):
        for o in range(po, po + sz):
            if o in diff_set:
                insn_indices_with_diff.add(k)
                break
    if not insn_indices_with_diff:
        return None
    counted: set[int] = set()    # cmp+jcc rows already absorbed by a site
    n_sites = 0
    for k in sorted(insn_indices_with_diff):
        if k in counted:
            continue
        ps_asm = ps[k][3]
        rc_asm = rc[k][3]
        ps_mn = ps_asm.split()[0] if ps_asm else ""
        rc_mn = rc_asm.split()[0] if rc_asm else ""
        # Case A: this insn is the cmp; next must be complementary jcc.
        if ps_mn == "cmp" and rc_mn == "cmp" and k + 1 < len(ps):
            ps_ops = [o.strip() for o in ps_asm[4:].split(",")]
            rc_ops = [o.strip() for o in rc_asm[4:].split(",")]
            if (len(ps_ops) == 2 and len(rc_ops) == 2
                    and ps_ops[0] == rc_ops[1]
                    and ps_ops[1] == rc_ops[0]
                    and ps_ops[0] != ps_ops[1]):
                nps_mn = ps[k+1][3].split()[0] if ps[k+1][3] else ""
                nrc_mn = rc[k+1][3].split()[0] if rc[k+1][3] else ""
                if _R4_JCC_FLIP.get(nps_mn) == nrc_mn:
                    n_sites += 1
                    counted.add(k)
                    counted.add(k + 1)
                    continue
        # Case B: this insn is the complementary jcc; previous was the
        # swapped cmp (which may not itself have a diff if cmp is
        # `cmp reg, imm` -- only the jcc differs in that special form).
        if (_R4_JCC_FLIP.get(ps_mn) == rc_mn
                and k > 0
                and ps[k-1][3].startswith("cmp")
                and rc[k-1][3].startswith("cmp")):
            ps_prev_ops = [o.strip() for o in ps[k-1][3][4:].split(",")]
            rc_prev_ops = [o.strip() for o in rc[k-1][3][4:].split(",")]
            if (len(ps_prev_ops) == 2 and len(rc_prev_ops) == 2
                    and ps_prev_ops[0] == rc_prev_ops[1]
                    and ps_prev_ops[1] == rc_prev_ops[0]):
                n_sites += 1
                counted.add(k)
                counted.add(k - 1)
                continue
        # This insn has a diff that is NOT Rule 4 explained.
        return None
    return n_sites if n_sites > 0 else None


_R103_GP_REGS = {
    "eax", "ebx", "ecx", "edx", "esi", "edi", "ebp",
    "ax", "bx", "cx", "dx", "si", "di",
}


def _rule103_branchy_def_note(
    orig: bytes,
    recomp: bytes,
) -> Optional[str]:
    """Rule 103 RESOLVED-lever detector for a ~r4 (cmp-swap) residue.

    Fires when a swapped register-vs-register ``cmp``'s operand is
    defined upstream by the boolean-constant idiom

        sete/setne r8 ... [and rX,0xff] ... lea rDST,[rX+K]

    i.e. the source wrote ``v = K + (cond)`` (or the equivalent
    ternary).  Proven lever (entering_new_square, 017f7728): rewrite
    the def as a constant if/else -- Watcom 10.0a if-converts
    ``if (cond) v = A; else v = B;`` to the SAME sete/lea bytes, but
    the branchy IL's conflict-creation slots differ and the unstable
    ShellSort flips the equal-savings ConfBefore tie -- then spell the
    compare in PS's operand order.  Both facts of the Rule 103 weld
    decouple; the function can go byte-exact.

    Reliable on a ~r4-classified function (disasm aligned everywhere
    except the cmp ModRM + Jcc opcode); on other diffing functions it
    is best-effort and returns None once the disasms fall out of
    alignment.
    """
    return _rule103_branchy_def_note_insns(
        _disasm_for_diff(orig), _disasm_for_diff(recomp))


def _rule103_branchy_def_note_insns(
    ps: list[InsnT],
    rc: list[InsnT],
) -> Optional[str]:
    """Insn-list core of :func:`_rule103_branchy_def_note`."""
    if len(ps) != len(rc):
        return None
    for k, (_, _, _, rc_asm) in enumerate(rc):
        ps_asm = ps[k][3]
        if ps_asm == rc_asm or not rc_asm.startswith("cmp "):
            continue
        rc_ops = [o.strip() for o in rc_asm[4:].split(",")]
        ps_ops = [o.strip() for o in ps_asm[4:].split(",")]
        if not (len(rc_ops) == 2 and len(ps_ops) == 2
                and rc_ops[0] == ps_ops[1] and rc_ops[1] == ps_ops[0]
                and rc_ops[0] in _R103_GP_REGS
                and rc_ops[1] in _R103_GP_REGS):
            continue
        # Backward scan: each cmp operand's most recent def.  If either
        # operand is defined by `lea rDST,[rBASE + K]` with a
        # sete/setne within the 4 insns before it (the boolean-constant
        # def chain), the branchy-def lever applies.
        remaining = set(rc_ops)
        for j in range(k - 1, max(k - 21, -1), -1):
            if not remaining:
                break
            asm = rc[j][3]
            mn = asm.split()[0] if asm else ""
            dst = asm[len(mn):].split(",")[0].strip() if "," in asm else ""
            if dst not in remaining:
                continue
            if mn == "lea" and "+" in asm and "*" not in asm:
                for m in range(j - 1, max(j - 5, -1), -1):
                    if rc[m][3].startswith(("sete", "setne")):
                        return (
                            f"Rule 103 lever: cmp operand {dst} is a "
                            f"sete+lea constant-boolean (`K + (cond)` def) "
                            f"-- rewrite its def as a constant if/else "
                            f"(`if (cond) v = A; else v = B;`: same "
                            f"sete/lea bytes, branchy IL flips the "
                            f"ConfBefore tie) AND spell the compare in "
                            f"PS's operand order.  "
                            f"Worked: entering_new_square (017f7728)"
                        )
            remaining.discard(dst)
    return None


def _trailing_table_pad_only(
    orig: bytes,
    recomp: bytes,
    diffs: list[int],
    orig_off: int,
    orig_fix: set[int],
) -> bool:
    """True when ALL genuine diff bytes sit AFTER the function's last
    executed ``ret``, in a trailing region that is a fixup-dense JUMP
    TABLE (one loader fixup per 4-byte entry) plus its alignment NOP pad.

    This is residue cluster #32 (docs/jump-table-alignment.md): the
    wcc386 build that produced PS pads jump-table labels differently
    (e.g. no pad, or ``mov eax,eax`` vs ``lea eax,[eax]``) -- a proven
    compiler-version delta.  The CODE of such functions is byte-exact;
    only the dead alignment filler between the last ``ret`` and the
    table differs (table entries themselves are fixup-masked).  For
    decomp purposes these functions ARE exact; the filler bytes matter
    only for a final whole-image byte recreation.
    """
    if not diffs or len(orig) != len(recomp):
        return False
    first_diff = diffs[0]
    # Last unconditional control transfer (`ret`/`ret imm16`, or the
    # dispatcher's own `jmp [table+reg*4]`) that ends BEFORE the first
    # diff byte -- everything after it is dead filler + the table.
    ret_end = None
    for off, size, _raw, asm in _disasm_for_diff(orig):
        if asm.startswith(("ret", "jmp")) and off + size <= first_diff:
            ret_end = off + size
    if ret_end is None:
        return False
    if any(d < ret_end for d in diffs):
        return False
    trailing_len = len(orig) - ret_end
    if trailing_len < 8:          # need at least 2 table entries
        return False
    fixup_bytes = sum(
        1 for i in range(ret_end, len(orig)) if (orig_off + i) in orig_fix
    )
    # A jump table is one 4-byte fixup per entry => ~100% fixup density;
    # allow for the (<=3 byte) alignment pad and a partial last entry.
    return fixup_bytes >= (trailing_len - 7) and fixup_bytes >= 8


def _next_fn_scan_table_only(
    orig: bytes,
    recomp_code: bytes,
    diffs: list[int],
    orig_off: int,
    recomp_off: int,
    rc_next_off: Optional[int],
    orig_fix: set[int],
    recomp_fix: set[int],
) -> bool:
    """True when ALL diff bytes sit AFTER the function's last executed
    ``ret``/``jmp`` in a trailing region that is the NEXT symbol's Watcom
    select/scan table, byte-identical (fixup-masked) to the RC bytes
    immediately preceding the RC location of that next symbol.

    Watcom dumps a function's switch tables just before the function's
    entry label (docs/jump-table-alignment.md), so a last-in-module
    function's symbols.json extent (which runs to the next symbol) can
    swallow the NEXT MODULE's first-function tables.  The RC link order
    differs from PS, so the naive ``rc_off + delta`` slice compares the
    table region against unrelated code from whatever module follows in
    the RC link.  Re-anchoring the trailing region at the RC next-symbol
    site proves the table is faithfully reproduced; the remaining diff
    is pure extent attribution, and the function's own CODE is exact.
    Worked example: ``stop_system`` (last fn of lib32.c, 0x43b of code)
    followed by sim_mouse's (hotkeys.c) two scan tables in the 254b gap.

    GUARD: the re-anchor is only *evidence* when the RC link order actually
    differs.  When the next symbol is ADJACENT in RC too
    (``rc_next_off == recomp_off + len(orig)``) the "re-anchored" slice is
    byte-for-byte the slice the naive comparison already diffed, and
    re-running ``_compare_bytes`` on the short trailing sub-buffer can only
    flip the verdict via a framing artifact: an in-function rel8/rel32
    branch whose target falls outside the sub-buffer gets masked as
    "cross-function" by ``_rel_call_jmp_disp_mask``, silently hiding a
    GENUINE code diff.  Observed false positives: place_a_building_roof /
    place2_a_building_roof -- their "trailing region" is live code (the
    fixups are data refs, not a table) and the single diff byte is a real
    divergence (PS ``jmp`` back to a distant duplicated ``add eax,eax``
    tail vs RC ``jmp`` forward to the near copy).  Those must stay DIFF.
    """
    if not diffs or rc_next_off is None:
        return False
    if rc_next_off == recomp_off + len(orig):
        return False  # identity re-anchor: no independent evidence
    first_diff = diffs[0]
    ret_end = None
    for off, size, _raw, asm in _disasm_for_diff(orig):
        if asm.startswith(("ret", "jmp")) and off + size <= first_diff:
            ret_end = off + size
    if ret_end is None:
        return False
    if any(d < ret_end for d in diffs):
        return False
    trailing = orig[ret_end:]
    if len(trailing) < 8:
        return False
    # Must look like a table (fixup-bearing address entries), not code.
    fixup_bytes = sum(
        1 for i in range(ret_end, len(orig)) if (orig_off + i) in orig_fix
    )
    if fixup_bytes < 8:
        return False
    rc_start = rc_next_off - len(trailing)
    if rc_start < 0 or rc_next_off > len(recomp_code):
        return False
    return not _compare_bytes(
        trailing, recomp_code[rc_start:rc_next_off],
        orig_off + ret_end, rc_start, orig_fix, recomp_fix,
    )


# ── Verbose diff rendering ─────────────────────────────────────────────────────
#
# Output format: unified-diff-style.
#
#   * Equal rows are a single compact line:
#         +0008  L2202   6b c0 3a               imul eax, eax, 0x3a
#
#   * Diff rows are stacked, one prefix per side, with byte-level [xx]
#     brackets marking which bytes actually differ after fixup masking:
#         +0020  L2203   replace
#                -PS  8a [90] [??] [??] [??] [??]   mov dl, byte ptr [eax + 0x...]
#                +RC  8a [10]                       mov dl, byte ptr [eax]
#                hint Rule 19 — base+disp vs no-disp memory form
#
#   * insert / delete only emit one side (-PS or +RC).
#
# This was chosen over a side-by-side table because (a) horizontal width
# pressure forces Rich to wrap operand cells which breaks row pairing,
# (b) equal rows printed twice (once per side) waste 80%+ of vertical
# space on the most-common-and-least-informative case, and (c) insert/
# delete in a side-by-side view reuses the same offset on both halves
# which reads as "two instructions at the same address".  The unified
# format removes all three failure modes; see the discussion in commit
# message and AGENTS.md notes.
#
# The same row stream powers --json (one record per row, with explicit
# `kind`, per-side bytes/asm, masked-byte-diff positions, and rule hint).

InsnT = tuple[int, int, bytes, str]


def _disasm_for_diff(code: bytes) -> list[InsnT]:
    """Disassemble a function body; tail bytes that don't decode become a
    synthetic <raw Nb> entry so they still participate in alignment."""
    out: list[InsnT] = []
    for insn in _CS.disasm(code, 0):
        out.append((insn.address, insn.size, bytes(insn.bytes),
                    f"{insn.mnemonic} {insn.op_str}".strip()))
    decoded = sum(s for _, s, _, _ in out)
    if decoded < len(code):
        tail = code[decoded:]
        out.append((decoded, len(tail), tail, f"<raw {len(tail)}b>"))
    return out


def _hex_tokens(raw: bytes, rel_off: int, abs_base: int,
                fix: set[int]) -> list[str]:
    """Per-byte hex tokens with `??` for fixup-masked positions."""
    return [
        "??" if (abs_base + rel_off + i) in fix else f"{b:02x}"
        for i, b in enumerate(raw)
    ]


def _masked_bytes(raw: bytes, rel_off: int, abs_base: int, fix: set[int],
                  rel_mask: set[int]) -> bytes:
    """Comparison key: zero out fixup bytes and rel-call/jmp disp bytes."""
    return bytes(
        0 if (abs_base + rel_off + i) in fix or (rel_off + i) in rel_mask else b
        for i, b in enumerate(raw)
    )


def _diff_byte_positions(o: Optional[InsnT], r: Optional[InsnT],
                         orig_off: int, recomp_off: int,
                         orig_fix: set[int], recomp_fix: set[int],
                         rel_orig: set[int], rel_recomp: set[int]
                         ) -> tuple[list[int], list[int]]:
    """Return (ps_diff_positions, rc_diff_positions): byte indices within
    each side's `raw` that differ from the other side after fixup/rel
    masking.  For insert/delete, every byte of the present side is
    flagged.  For replace with mismatched lengths, positions beyond the
    shorter side are flagged on the longer side.
    """
    if o is None and r is not None:
        return [], list(range(len(r[2])))
    if r is None and o is not None:
        return list(range(len(o[2]))), []
    assert o is not None and r is not None
    o_m = _masked_bytes(o[2], o[0], orig_off,   orig_fix,   rel_orig)
    r_m = _masked_bytes(r[2], r[0], recomp_off, recomp_fix, rel_recomp)
    n = min(len(o_m), len(r_m))
    ps_diff = [i for i in range(n) if o_m[i] != r_m[i]]
    rc_diff = list(ps_diff)
    if len(o_m) > n:
        ps_diff += list(range(n, len(o_m)))
    if len(r_m) > n:
        rc_diff += list(range(n, len(r_m)))
    return ps_diff, rc_diff


def _bracket_tokens(tokens: list[str], diff_positions: list[int]) -> str:
    """Render hex tokens with [xx] brackets around `diff_positions`."""
    if not tokens:
        return ""
    diff_set = set(diff_positions)
    return " ".join(
        f"[{tok}]" if i in diff_set else tok
        for i, tok in enumerate(tokens)
    )


# Operand simplification for compact mode: drop `dword ptr ` (which is
# the implicit default for 32-bit register / 4-byte memory ops in 32-bit
# code, redundant with the mnemonic).  Keep `byte ptr` and `word ptr`
# because those carry width info that is otherwise not visible.
_DWORD_PTR_RE = re.compile(r"\bdword ptr ")


def _simplify_operands(asm: str) -> str:
    """Strip `dword ptr ` qualifiers; leave byte/word ptr intact."""
    return _DWORD_PTR_RE.sub("", asm)


_CALLEE_SAVE_REGS = ("ebx", "ecx", "edx", "esi", "edi", "ebp", "eax")


def _detect_callee_saves(insns: list[InsnT]) -> list[str]:
    """Walk the prologue and return the ordered list of registers
    pushed (callee-save set).  Skips the optional ``push <imm>; call
    __CHK`` stack-probe prefix that Watcom emits for functions with >=
    16-byte locals.  Stops at the first non-``push reg`` instruction.
    """
    start = 0
    # Skip optional `push <imm>; call __CHK` stack-check prefix.  The
    # immediate may render as `push 8` or `push 0x10` depending on
    # capstone's per-value choice; the discriminant is "push <number>"
    # immediately followed by `call`.
    def _is_push_imm(asm: str) -> bool:
        parts = asm.split(None, 1)
        if not parts or parts[0] != "push":
            return False
        op = parts[1] if len(parts) > 1 else ""
        if not op:
            return False
        return op[0].isdigit() or op.startswith("0x") or op.startswith("-")

    if (len(insns) >= 2
            and _is_push_imm(insns[0][3])
            and insns[1][3].startswith("call ")):
        start = 2

    saves: list[str] = []
    for j in range(start, len(insns)):
        parts = insns[j][3].split(None, 1)
        if not parts or parts[0] != "push":
            break
        op = parts[1] if len(parts) > 1 else ""
        if op in _CALLEE_SAVE_REGS:
            saves.append(op)
        else:
            break
    return saves


def _detect_frame_alloc(insns: list[InsnT]) -> int | None:
    """Return the prologue stack-frame allocation in bytes (the `sub esp,
    N` that follows the callee-save pushes), or None if the prologue can't
    be parsed.  0 means no frame allocation (no stack locals / outgoing
    stack args).

    Unlike per-row `[esp+N]` offsets (which renumber on any cascade), this
    is a single scalar reflecting the FINAL frame layout, so a PS-vs-RC
    delta is a reliable signal that the stack-local layout differs
    (extra/missing local, wrong-width local, or different outgoing
    stack-arg space).  See Rule 107.
    """
    def _is_push_imm(asm: str) -> bool:
        parts = asm.split(None, 1)
        if not parts or parts[0] != "push":
            return False
        op = parts[1] if len(parts) > 1 else ""
        if not op:
            return False
        return op[0].isdigit() or op.startswith("0x") or op.startswith("-")

    start = 0
    if (len(insns) >= 2
            and _is_push_imm(insns[0][3])
            and insns[1][3].startswith("call ")):
        start = 2
    # Skip callee-save pushes.
    j = start
    while j < len(insns):
        parts = insns[j][3].split(None, 1)
        if not parts or parts[0] != "push":
            break
        op = parts[1] if len(parts) > 1 else ""
        if op in _CALLEE_SAVE_REGS:
            j += 1
        else:
            break
    if j >= len(insns):
        return None
    parts = insns[j][3].split(None, 1)
    if not parts:
        return None
    mnem = parts[0]
    ops = parts[1] if len(parts) > 1 else ""
    fields = [o.strip() for o in ops.split(",")]
    if len(fields) != 2 or fields[0] != "esp":
        # No frame allocation immediately after the pushes.
        return 0
    try:
        imm = int(fields[1], 0)
    except ValueError:
        return None
    if mnem == "sub":
        return imm
    if mnem == "add":          # `add esp, -N` form
        return -imm
    return 0


def _render_frame_alloc(console, orig_insns: list[InsnT],
                        recomp_insns: list[InsnT],
                        rows: list[dict] | None = None) -> None:
    """Print a `Frame:` root-cause diagnostic when PS and recomp allocate
    different prologue frame sizes (Rule 107 companion).  Reliable because
    it compares a single scalar (`sub esp, N`), not per-row `[esp+N]`
    offsets.

    Corpus analysis: 45 % of diffing functions have their first divergence
    in the prologue, and those cascades are 63 % of all residual diff
    bytes.  When ``rows`` is supplied this line flags whether the frame
    mismatch is the ROOT of the cascade and gives a sign-based fix
    direction (RC-bigger = inline superfluous named locals, generalised
    Rule 116; PS-bigger = PS spilled more, Rule 111).  Full logic lives in
    ``c2.commands.frame_hints``.

    Note: this catches a *total-size* difference; the same-size slot SWAP
    (Rule 107's noisy per-row case) is caught separately by
    ``_render_slot_swap`` / ``c2.commands.slot_swap_hints``.
    """
    from c2.commands.frame_hints import detect as _frame_detect, render_line

    hint = _frame_detect(orig_insns, recomp_insns, rows)
    if hint is None:
        return
    console.print(render_line(hint), highlight=False)


def _render_slot_swap(console, orig_insns: list[InsnT],
                      recomp_insns: list[InsnT],
                      rows: list[dict] | None = None,
                      name: str | None = None) -> None:
    """Print a `Slot-swap:` diagnostic when PS and recomp share a frame size
    but permute same-size co-spilled temps across `[esp+N]` slots (Rule
    107's noisy per-row case that `_render_frame_alloc` does NOT catch).
    When ``name`` is given, annotates the swap with the SetTempLocation
    (`st`) trace -- naming the swapped temps + def lines for a directed
    lever.  See ``c2.commands.slot_swap_hints``.
    """
    try:
        from c2.commands.slot_swap_hints import (detect as _ss_detect,
                                                 render as _ss_render,
                                                 annotate as _ss_annotate)
    except ImportError:
        return
    hint = _ss_detect(orig_insns, recomp_insns, rows)
    if hint is None:
        return
    if name:
        try:
            _ss_annotate(hint, name, None)
        except Exception:
            pass
    # escape() so the literal `[esp]` slot names aren't eaten as Rich markup.
    console.print(f"  [yellow]Slot-swap[/]: {escape(_ss_render(hint))}",
                  highlight=False)


def _diff_shape_summary(rows) -> Optional[str]:
    """Classify the diff ROWS so the 'N unexplained' count isn't opaque:
    replace vs insert/delete, and the dominant replace shapes (same-op =
    reg/operand/encoding; op-select = a different mnemonic).  A high
    insert/delete fraction means the bulk is ALIGNMENT CASCADE from one
    early size-changing diff -- not N distinct problems -- so the verdict
    points at fixing the earliest size diff instead of grinding each row.
    """
    from collections import Counter
    rep_same: Counter = Counter()
    rep_sel: Counter = Counter()
    n_rep = ins = dele = 0
    for row in rows:
        k = row.get("kind")
        if k == "equal":
            continue
        o = row.get("o")
        r = row.get("r")
        if not o:
            ins += 1
            continue
        if not r:
            dele += 1
            continue
        pm = o[3].split(None, 1)[0] if o[3] else "?"
        rm = r[3].split(None, 1)[0] if r[3] else "?"
        n_rep += 1
        if pm == rm:
            rep_same[pm] += 1
        else:
            rep_sel[f"{pm}->{rm}"] += 1
    total = n_rep + ins + dele
    if total == 0:
        return None
    # A real ALIGNMENT cascade = insert/delete-heavy AND enough of them that
    # it's one early size diff fanning out, not a 1-row shift.
    cascade = (ins + dele) >= 4 and (ins + dele) / total > 0.3
    # Only worth a line when it's actionable: a real cascade, or a diff big
    # enough that the shape breakdown adds signal.  Small clean diffs already
    # read from the histogram.
    if not cascade and total < 12:
        return None
    msg = f"Diff-shape: {n_rep} replace, {ins} insert, {dele} delete"
    if rep_sel:
        msg += "; op-select [" + ", ".join(
            f"{k}:{v}" for k, v in rep_sel.most_common(3)) + "]"
    if rep_same:
        msg += "; same-op [" + ", ".join(
            f"{k}:{v}" for k, v in rep_same.most_common(3)) + "]"
    if cascade:
        msg += (f".  {ins + dele}/{total} rows are insert/delete = ALIGNMENT "
                "CASCADE from a size-changing diff (NOT distinct problems) -- "
                "fix the EARLIEST size diff (Rule 16 branch encoding / frame / "
                "a missing-or-extra instruction) and they collapse.")
    return msg


def _render_schedule(console, name: str | None, orig_insns: list[InsnT],
                     recomp_insns: list[InsnT],
                     rows: list[dict] | None = None) -> None:
    """Print a `Schedule:` diagnostic when PS and recomp compute the RHS value
    vs the LHS address of an indexed read-modify-write in opposite order (the
    eval-order hoist lever).  See ``c2.commands.sched_hints``."""
    try:
        from c2.commands.sched_hints import detect as _sc_detect, render as _sc_render
    except ImportError:
        return
    hint = _sc_detect(name, orig_insns, recomp_insns, rows)
    if hint is None:
        return
    console.print(f"  [yellow]Schedule[/]: {escape(_sc_render(hint))}",
                  highlight=False)


def _render_binir_shape(console, rows: list[dict] | None = None) -> None:
    """Print a `binir-shape:` diagnostic comparing per-source-line IR shapes
    between PS and our compile.

    A ``verdict=encoding_noise`` line means EVERY source line's binir-
    recovered IR matches between sides -- the byte diff is pure
    regalloc tie-break / Jcc encoding length and the existing Reg-swap /
    encoding hints are sufficient.  A ``verdict=shape_divergence`` line
    names the specific source lines where the recovered ops differ --
    those lines are the smallest-blast-radius source-perturbation
    targets.  See ``c2.commands.binir_shape_hints``.
    """
    if rows is None:
        return
    try:
        from c2.commands.binir_shape_hints import detect as _bs_detect
    except ImportError:
        return
    hint = _bs_detect(rows)
    if hint.verdict == "no_lines_with_ir":
        return       # nothing to say
    if hint.verdict == "encoding_noise":
        console.print(
            f"  [dim]binir-shape[/]: "
            f"all {hint.lines_identical}/{hint.lines_compared} compared "
            f"source line(s) have IDENTICAL IR -- byte diff is pure "
            f"regalloc/encoding noise (look at Reg-swap / Jcc hints, "
            f"not source restructuring).  Equal-savings register-identity "
            f"swaps flip on conflict-creation = REVERSE LAST-USE order: see "
            f"the Cascade lever (screen: `c2 savings <fn> --flip VAR=REG`)",
            highlight=False,
        )
        return
    # shape_divergence
    line_list = ", ".join(str(d.line) for d in hint.divergences[:5])
    if len(hint.divergences) > 5:
        line_list += f", … (+{len(hint.divergences) - 5})"
    console.print(
        f"  [magenta]binir-shape[/]: "
        f"{hint.lines_divergent}/{hint.lines_compared} line(s) diverge "
        f"semantically -- L{line_list}",
        highlight=False,
    )
    for d in hint.divergences[:5]:
        console.print(
            f"    [dim]·[/] [magenta]L{d.line}[/]: {escape(d.summary)}",
            highlight=False,
        )


def _build_diff_rows(
    orig: bytes, orig_off: int,
    recomp: bytes, recomp_off: int,
    orig_fix: set[int], recomp_fix: set[int],
    line_map: dict[int, int] | None,
) -> tuple[list[dict], list]:
    """Decode + align both sides; return (rows, hints).

    Each row dict has keys:
        kind     : "equal" | "replace" | "insert" | "delete"
        off      : int  (function-relative byte offset, PS-side for
                         everything except pure inserts)
        ln       : Optional[int]  (PS source line, only on first insn
                                   of each source statement)
        o, r     : Optional[InsnT]  (raw capstone tuples, for hints)
        ps_tokens, rc_tokens : list[str]  (per-byte hex with ?? masks)
        ps_diff, rc_diff     : list[int]  (positions to bracket)
    """
    import difflib

    orig_insns   = _disasm_for_diff(orig)
    recomp_insns = _disasm_for_diff(recomp)

    rel_orig   = _rel_call_jmp_disp_mask(orig)
    rel_recomp = _rel_call_jmp_disp_mask(recomp)

    orig_keys = [
        _masked_bytes(r, o, orig_off, orig_fix, rel_orig)
        for o, _, r, _ in orig_insns
    ]
    recomp_keys = [
        _masked_bytes(r, o, recomp_off, recomp_fix, rel_recomp)
        for o, _, r, _ in recomp_insns
    ]

    # Build sorted line-number entries within this function's PS bytes.
    line_entries: list[tuple[int, int]] = sorted(
        (off, ln) for off, ln in (line_map or {}).items()
        if orig_off <= off < orig_off + len(orig)
    )
    last_ln: list[int | None] = [None]

    def _ln_for(abs_off: int) -> int | None:
        """Return source line at abs_off when it changes from the previous
        emitted value, else None — so vertical scanning highlights
        statement boundaries (and their absence in macro/inline code)."""
        if not line_entries:
            return None
        cur: int | None = None
        for off, ln in line_entries:
            if off <= abs_off:
                cur = ln
            else:
                break
        if cur is None or cur == last_ln[0]:
            return None
        last_ln[0] = cur
        return cur

    rows: list[dict] = []

    def _emit(kind: str, o: InsnT | None, r: InsnT | None) -> None:
        ps_tokens = _hex_tokens(o[2], o[0], orig_off,   orig_fix)   if o else []
        rc_tokens = _hex_tokens(r[2], r[0], recomp_off, recomp_fix) if r else []
        ps_diff, rc_diff = _diff_byte_positions(
            o, r, orig_off, recomp_off, orig_fix, recomp_fix,
            rel_orig, rel_recomp,
        )
        anchor_off = o[0] if o is not None else r[0]  # type: ignore[index]
        rows.append({
            "kind":      kind,
            "off":       anchor_off,
            "ln":        _ln_for(orig_off + o[0]) if o else None,
            "o":         o,
            "r":         r,
            "ps_tokens": ps_tokens,
            "rc_tokens": rc_tokens,
            "ps_diff":   ps_diff,
            "rc_diff":   rc_diff,
        })

    sm = difflib.SequenceMatcher(None, orig_keys, recomp_keys, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                _emit("equal", orig_insns[i1 + k], recomp_insns[j1 + k])
        elif tag == "replace":
            olen, rlen = i2 - i1, j2 - j1
            for k in range(max(olen, rlen)):
                o = orig_insns[i1 + k]   if k < olen else None
                r = recomp_insns[j1 + k] if k < rlen else None
                if o is None:
                    _emit("insert", None, r)
                elif r is None:
                    _emit("delete", o, None)
                else:
                    _emit("replace", o, r)
        elif tag == "delete":
            for k in range(i2 - i1):
                _emit("delete", orig_insns[i1 + k], None)
        else:  # insert
            for k in range(j2 - j1):
                _emit("insert", None, recomp_insns[j1 + k])

    hint_rows = [(row["o"], row["r"], row["kind"] != "equal") for row in rows]
    hints = detect_hints(hint_rows, orig_off, recomp_off,
                         orig_fix, recomp_fix)
    return rows, hints


def _render_headers(
    console: Console,
    rows: list[dict],
    hints: list,
    orig: bytes,
    orig_off: int,
    orig_insns: list[InsnT],
    recomp_insns: list[InsnT],
    name: str | None,
    recomp_off: int = 0,
    recomp_line_map: dict[int, int] | None = None,
) -> None:
    """Print the per-function header block (callee-saves, pragma hint,
    rule histogram, tail-merge donor, sig mismatch, sibling hint).
    Shared by the compact and side-by-side renderers."""
    ps_saves = _detect_callee_saves(orig_insns)
    rc_saves = _detect_callee_saves(recomp_insns)

    if ps_saves or rc_saves:
        ps_str = " ".join(ps_saves) if ps_saves else "(none)"
        rc_str = " ".join(rc_saves) if rc_saves else "(none)"
        if ps_saves != rc_saves:
            console.print(
                f"  [red]PS callee-saves[/]: {escape(ps_str)}", highlight=False)
            console.print(
                f"  [green]RC callee-saves[/]: {escape(rc_str)}  "
                f"[yellow](divergent)[/]", highlight=False)
        else:
            console.print(
                f"  [dim]callee-saves[/]: {escape(ps_str)}", highlight=False)

    _render_frame_alloc(console, orig_insns, recomp_insns, rows)
    _render_slot_swap(console, orig_insns, recomp_insns, rows, name=name)
    _render_schedule(console, name, orig_insns, recomp_insns, rows)
    _render_binir_shape(console, rows)

    try:
        from c2.commands.pragma_hints import detect_pragma_hint, render_hint_lines

        pragma_hint = detect_pragma_hint(orig_insns, recomp_insns)
        if pragma_hint is not None:
            lines = render_hint_lines(pragma_hint)
            sev_color = {
                "high": "red",
                "medium": "yellow",
                "low": "dim",
            }.get(pragma_hint.severity, "yellow")
            console.print(
                f"  [{sev_color}]Prologue hint[/]: {escape(lines[0])}",
                highlight=False,
            )
            if len(lines) > 1:
                console.print(
                    f"  [{sev_color}]{escape(lines[1])}[/]",
                    highlight=False,
                )
    except ImportError:
        pass

    # Regalloc ground truth: the REAL 10.0a allocator's per-value register
    # choices (from the instrumented -trace image, parsed once per file by
    # c2.regalloc and disk-cached). Only for diffing functions, and self-gated
    # (no hint for functions without a regalloc phase).
    _reg_alloc = None
    _reg_spilled = None
    if name and any(r["kind"] != "equal" for r in rows):
        try:
            from c2.commands import regalloc_hints
            _rh = regalloc_hints.detect(name.rstrip("_"))
            if _rh is not None:
                _reg_alloc, _reg_spilled = _rh.allocs, _rh.spilled
                # Per-source-line view (the long `regalloc by source line`
                # table) is the most direct evidence of what the compiler did
                # at each statement, but it's ~25 lines of mostly-negative
                # detail.  Gate it behind --full-hints; the compact summary
                # (head + picks + conflict/birth order) always prints.
                for _ln in regalloc_hints.render_lines(_rh, detailed=_DIAG_FULL):
                    console.print(f"  [cyan]{escape(_ln)}[/]", highlight=False)
            elif os.environ.get("C2_DEBUG_REGALLOC"):
                console.print("  [dim]regalloc: detect() -> None[/]")
        except Exception as _e:
            if os.environ.get("C2_DEBUG_REGALLOC"):
                import traceback
                console.print(f"  [red]regalloc hint error: {escape(repr(_e))}[/]")
                traceback.print_exc()

    # (PS-alloc verdict moved BELOW the rover detection: its tie-swap
    # claims must be cross-checked against the rover's claimed pairs --
    # a register pair the RISCify rover diverges on is a FindRegister
    # scratch seat at the diff rows, NOT the allocator tie holding the
    # same registers.  font_format_split was misdiagnosed this way.)

    # Caching-mismatch hint (de-invent OR add-intermediate): fuses the AST
    # candidate (NAMES the exact local + line) with the PS-side per-address
    # reload census (the direction).  Subsumes the old Rule-129 reread hint
    # (totals fallback when no AST candidate resolves).  See
    # c2/commands/deinvent_hints.py.
    _deinvent_fired = False
    if name and any(r["kind"] != "equal" for r in rows):
        try:
            from c2.commands import deinvent_hints
            _fa = _build_src_func_cache().get(name)
            _di = deinvent_hints.detect(
                _fa[1] if _fa else None, orig_insns, recomp_insns)
            if _di is not None:
                console.print(
                    f"  [magenta]{escape(deinvent_hints.render(_di))}[/]",
                    highlight=False)
                _deinvent_fired = _di.kind in ("deinvent", "totals")
        except Exception as _e:
            if os.environ.get("C2_DEBUG_REGALLOC"):
                import traceback
                console.print(f"  [red]deinvent hint error: {escape(repr(_e))}[/]")
                traceback.print_exc()

    # Invented-temp hint (§10 de-invent): a dominant single-register-pair
    # identity swap + an extra RC-only reg-to-reg copy into that register =
    # a redundant local (e.g. `ptr = sptr;`) PS never made -- it walks the
    # value in place.  Complementary register-walk signal to the reload
    # census above; suppressed when the de-invent hint already fired (they
    # would name the same fix).  See c2/commands/invented_temp_hints.py.
    if name and not _deinvent_fired and any(r["kind"] != "equal" for r in rows):
        try:
            from c2.commands import invented_temp_hints
            _it = invented_temp_hints.detect(hints, rows, orig_insns,
                                             recomp_insns)
            if _it is not None:
                console.print(
                    f"  [magenta]{escape(invented_temp_hints.render(_it))}[/]",
                    highlight=False)
        except Exception as _e:
            if os.environ.get("C2_DEBUG_REGALLOC"):
                import traceback
                console.print(f"  [red]invented-temp hint error: {escape(repr(_e))}[/]")
                traceback.print_exc()

    # Reassign-to-constant hint (Rule 155): a throwaway boolean-expression
    # call arg `(c != K) + N` materialises a boolean temp that spills at the
    # pressure threshold; PS reassigns `c` to the constant first.  Distinct
    # from Rule 26 (both forms setcc here -- the spill delta is the only
    # symptom).  Gated on a real pressure spill (RC frame bigger than PS at
    # equal push count).  See c2/commands/reassign_hints.py +
    # docs/codegen-experiments/reassign-to-constant.py.
    if name and any(r["kind"] != "equal" for r in rows):
        try:
            from c2.commands import reassign_hints
            _fa2 = _build_src_func_cache().get(name)
            # NB: do NOT assign to _rh -- that is the regalloc-trace handle
            # (regalloc_hints.detect) still needed below by the rover
            # detector's `fr=` argument.  Shadowing it here (2026-06..07-09)
            # silently starved rover_hints.detect of the trace on every
            # diffing function, degrading the Rover lever to the naive
            # uniform-shift text.
            _rh2 = reassign_hints.detect(
                _fa2[1] if _fa2 else None, orig_insns, recomp_insns)
            if _rh2 is not None:
                console.print(
                    f"  [magenta]{escape(reassign_hints.render(_rh2))}[/]",
                    highlight=False)
        except Exception as _e:
            if os.environ.get("C2_DEBUG_REGALLOC"):
                import traceback
                console.print(f"  [red]reassign hint error: {escape(repr(_e))}[/]")
                traceback.print_exc()

    # Const-drift hint: the cmp/test comparison constants differ from PS -- a
    # wrong threshold / dispatch literal in the source (get_census class).
    # See c2/commands/const_drift.py (and `c2 const-drift` for corpus triage).
    if name and any(r["kind"] != "equal" for r in rows):
        try:
            from c2.commands import const_drift
            _cd = const_drift.detect_hint(orig_insns, recomp_insns)
            if _cd is not None:
                console.print(
                    f"  [magenta]{escape(const_drift.render_hint(_cd))}[/]",
                    highlight=False)
        except Exception as _e:
            if os.environ.get("C2_DEBUG_REGALLOC"):
                import traceback
                console.print(f"  [red]const-drift hint error: {escape(repr(_e))}[/]")
                traceback.print_exc()

    # Byte-seat verdict: ONE classification for every `Byte-reg swap` row --
    # CASE A (collateral to a dword tie), B (AL-squat masking / Rule 126),
    # C (rover-seated CSE / Rule 127), or D (inert byte tie / Rule 133,
    # irreducible).  Subsumes the old AL-squat hint (cases B/C compose it)
    # and replaces the generic "no source lever" framing with the OW-v1 path
    # + lever.  watcom10.0a repo docs/wcc386-re/regalloc-model.md "Byte-register seating".
    if name and any(r["kind"] != "equal" for r in rows):
        try:
            from c2.commands import byte_seat_hints
            _bs = byte_seat_hints.detect(name.rstrip("_"), hints,
                                         ps_insns=orig_insns, rows=rows)
            if _bs is not None:
                for _ln in byte_seat_hints.render_lines(_bs):
                    console.print(f"  [magenta]{escape(_ln)}[/]",
                                  highlight=False)
        except Exception as _e:
            if os.environ.get("C2_DEBUG_REGALLOC"):
                import traceback
                console.print(f"  [red]byte-seat hint error: {escape(repr(_e))}[/]")
                traceback.print_exc()

    # Divisor hint: walks the per-routine IR forest to classify each O_DIV /
    # O_MOD (literal pow2 -> Rule 5; shared-temp CSE -> Rule 5c; paired
    # const div/mod -> potential Rule 5c, asm-confirm).  Pure prediction
    # from the trace -- complements the asm-side rule-hint histogram.
    if name and any(r["kind"] != "equal" for r in rows):
        try:
            from c2.commands import divisor_hints
            _dh = divisor_hints.detect(name.rstrip("_"))
            if _dh is not None:
                for _ln in divisor_hints.render_lines(_dh):
                    console.print(f"  [cyan]{escape(_ln)}[/]", highlight=False)
        except Exception as _e:
            if os.environ.get("C2_DEBUG_REGALLOC"):
                import traceback
                console.print(f"  [red]divisor hint error: {escape(repr(_e))}[/]")
                traceback.print_exc()

    # Binary-IR reconstruction: reverse-map known x86 idioms back to cg_op
    # tree ops (R_MOVOP2TEMP idiv-pairs => Rule 5c FIRED; sar/shl/sbb/sar =>
    # Pow2Div etc.).  Only render when PS and RC DIFFER -- a divergence in
    # reconstructed signatures is a direct evidence of which codegen path
    # each side took.  Use this side-by-side with the per-line regalloc
    # view above (the IR-forest origin) and the asm diff below (the
    # codegen result) to triangulate the source-level lever.
    if name and any(r["kind"] != "equal" for r in rows):
        try:
            from c2 import binir
            ps_ops = binir.recover(orig_insns)
            rc_ops = binir.recover(recomp_insns)
            ps_summary = binir.summarize(ps_ops)
            rc_summary = binir.summarize(rc_ops)
            if ps_summary != rc_summary:
                only_ps = {k: v for k, v in ps_summary.items()
                           if rc_summary.get(k, 0) != v}
                only_rc = {k: v for k, v in rc_summary.items()
                           if ps_summary.get(k, 0) != v}
                # The raw signature dicts are redundant with the readable
                # PS-only/RC-only lines emitted just below; show them only
                # under --full-hints.
                if _DIAG_FULL:
                    console.print(
                        f"  [cyan]binary-IR signatures (PS vs RC):[/]  "
                        f"PS={escape(str(ps_summary))}  "
                        f"RC={escape(str(rc_summary))}", highlight=False)
                # For each pattern only on one side, surface its source
                # implication (the most actionable thing).  This per-op
                # drill-down duplicates the `binir-shape` summary above, so
                # cap it in the default view (full list under --full-hints).
                _psrc_cap = None if _DIAG_FULL else 12
                _psrc_n = 0
                _psrc_skipped = 0
                for op in ps_ops:
                    if rc_summary.get(op.kind, 0) < ps_summary.get(op.kind, 0):
                        # PS has this pattern that RC lacks at this offset.
                        _lever = op.kind in _LEVER_KINDS
                        if _lever or _psrc_cap is None or _psrc_n < _psrc_cap:
                            console.print(
                                f"  [yellow]PS-only[/]  +{op.offset:#06x} "
                                f"[bold]{op.kind}[/] "
                                f"[dim]({op.op or '-'})[/]:  {escape(op.note)}",
                                highlight=False)
                            if not _lever:
                                _psrc_n += 1
                        else:
                            _psrc_skipped += 1
                        ps_summary[op.kind] -= 1
                        # Symbol-resolved upgrade for the ambiguous
                        # EDX:EAX-pair-at-exit pattern: follow the jmp
                        # through the PS epilogue/call-tail stubs.
                        if op.kind == "regpair_const_exit" and \
                                op.detail.get("jmp_target") is not None:
                            try:
                                from c2.commands.tail_merge import (
                                    classify_regpair_exit, _load_symbols)
                                # _disasm_for_diff uses base 0, so the jmp
                                # target is function-relative; rebase to the
                                # vaddr via the LE section offset + code base.
                                _cb = _load_symbols(Path("data/out/symbols.json")).code_base
                                _tva = op.detail["jmp_target"] + orig_off + _cb
                                _verdict = classify_regpair_exit(_tva)
                            except Exception:
                                _verdict = "unknown"
                            if _verdict == "return":
                                _seg, _off2 = op.detail["seg"], op.detail["off"]
                                _src = (f"return (char __far *){_off2:#x};"
                                        if _seg == 0 else
                                        f"return (char __far *)MK_FP({_seg:#x}, {_off2:#x});")
                                console.print(
                                    f"      [green]resolved: RETURN[/] -- "
                                    f"Rule 85 far-ptr constant; source is "
                                    f"literally `{escape(_src)}`",
                                    highlight=False)
                            elif _verdict == "args":
                                console.print(
                                    f"      [green]resolved: ARGS[/] -- "
                                    f"(eax,edx) watcall args into a ComTail-"
                                    f"merged shared call tail; reproduce the "
                                    f"identical call shape at every merged "
                                    f"site (NOT a return value).",
                                    highlight=False)
                for op in rc_ops:
                    if ps_summary.get(op.kind, 0) < rc_summary.get(op.kind, 0):
                        _lever = op.kind in _LEVER_KINDS
                        if _lever or _psrc_cap is None or _psrc_n < _psrc_cap:
                            console.print(
                                f"  [yellow]RC-only[/]  +{op.offset:#06x} "
                                f"[bold]{op.kind}[/] "
                                f"[dim]({op.op or '-'})[/]:  {escape(op.note)}",
                                highlight=False)
                            if not _lever:
                                _psrc_n += 1
                        else:
                            _psrc_skipped += 1
                        rc_summary[op.kind] -= 1
                if _psrc_skipped:
                    console.print(
                        f"  [dim]… {_psrc_skipped} more PS-only/RC-only IR-op "
                        f"asymmetr(ies) elided (see binir-shape above; "
                        f"--full-hints for the list)[/]", highlight=False)
        except Exception as _e:
            if os.environ.get("C2_DEBUG_REGALLOC"):
                import traceback
                console.print(f"  [red]binary-IR error: {escape(repr(_e))}[/]")
                traceback.print_exc()

    hist = histogram(hints)
    diff_count = sum(1 for r in rows if r["kind"] != "equal")

    # Regalloc model explainer + RISCify ROVER detection are computed HERE
    # (before the Rule-hints histogram) so the histogram can label catalogue-
    # unmatched rows correctly: when the rover is CONFIRMED they are
    # rover-cascade, not genuinely "unexplained".
    rae_layer: Optional[int] = None
    rae = None
    _rae_render = None
    try:
        from c2.commands.regalloc_explain import explain as _rae, render as _rae_render
        rae = _rae(orig_insns, recomp_insns, rule_hist=hist,
                   has_body_diff=(diff_count > 0),
                   rc_alloc=_reg_alloc, rc_spilled=_reg_spilled)
        if rae is not None:
            rae_layer = rae.layer
    except ImportError:
        pass
    _rov = None
    if name and rae_layer == 3:
        try:
            from c2.commands import rover_hints
            _rov = rover_hints.detect(orig_insns, recomp_insns, rule_hist=hist,
                                      fr=(_rh.fr if _rh is not None else None),
                                      lw=(getattr(_rh, "lw", None) if _rh is not None else None),
                                      src_lines=_decomp_src_lines(name),
                                      src_struct=_rover_src_structure(name))
        except Exception:
            if os.environ.get("C2_DEBUG_REGALLOC"):
                import traceback
                traceback.print_exc()
    # ROVER-CONFIRMED: the `fr` trace proves the exact byte-neutral advance
    # (``advances`` non-empty) -> the diff IS the rover, a theorem.  Used to
    # (a) relabel the histogram tail, and (b) suppress the orthogonal source-
    # shape suggestion hints (Neg-corpus, line-shape) further down.
    _rover_confirmed = _rov is not None and bool(getattr(_rov, "advances", None))
    _parm_reload = None
    _closeable = None
    if name and _rh is not None and getattr(_rh, "fr", None):
        try:
            from c2.commands import rover_hints as _rovmod
            from c2.commands.slot_swap_hints import detect as _ss_detect_pr
            # A same-size spill-SLOT swap is a more specific, confident
            # diagnosis than the parm-reload rover heuristic; when the residue
            # IS a slot swap, the reload `fr` is incidental -- defer to the
            # Slot-swap hint instead of mis-routing to parm-reload.
            _is_slot_swap = _ss_detect_pr(orig_insns, recomp_insns, rows) is not None
            _parm_reload = None if _is_slot_swap else _rovmod.parm_reload(_rh.fr)
            # OFFLINE closeable/blocked verdict (no recompile): does a single
            # self-healing +k dword advance reproduce PS's rover picks?  Fires
            # independently of detect() (works for imul/add-consumed loads too).
            # `visible` feeds the CompressIns model so invisible compressed ops
            # (immediate const-stores / single-use compare-loads) are not
            # wrongly required to hold.
            _vis = _visible_dword_picks(recomp_insns, recomp_off, recomp_line_map)
            _closeable = _rovmod.closeability(rows, _rh.fr, _decomp_src_lines(name),
                                              visible=_vis)
        except Exception:
            if os.environ.get("C2_DEBUG_REGALLOC"):
                import traceback
                traceback.print_exc()

    if diff_count > 0:
        explained = sum(hist.values())
        unexpl = diff_count - explained
        parts = [f"{n}x {rule}" for rule, n in sorted(hist.items())]
        if unexpl > 0 and _rover_confirmed:
            # the catalogue didn't match these rows, but the ROVER did: they
            # are RISCify-rover cascade (the size-shift jcc/encoding fallout),
            # NOT genuinely unexplained.
            tail = f"; {unexpl} more = RISCify-rover cascade (see Rover line)"
        elif unexpl > 0:
            tail = f"; {unexpl} unexplained"
        else:
            tail = "; all explained"
        if parts:
            console.print(
                f"  [yellow]Rule hints[/]: {', '.join(parts)}{tail}",
                highlight=False,
            )
            try:
                from c2.commands.rules_registry import (
                    verdicts_for_hist, render_verdict_lines)
                for vline in render_verdict_lines(verdicts_for_hist(hist.keys())):
                    console.print(f"    [dim]·[/] {vline}", highlight=False)
            except Exception:
                pass
        elif unexpl > 0:
            _lbl = ("RISCify-rover cascade (see Rover line)"
                    if _rover_confirmed else "none matched")
            console.print(
                f"  [yellow]Rule hints[/]: {unexpl} diff(s), {_lbl}",
                highlight=False,
            )
        # Classify the diff rows so 'N unexplained' isn't opaque (distinct
        # shapes vs alignment-cascade from one early size diff).
        try:
            _ds = _diff_shape_summary(rows)
            if _ds is not None:
                console.print(f"  [cyan]{escape(_ds)}[/]", highlight=False)
        except Exception:
            pass
        # Rule 103 branchy-def lever: a swapped (R,R) cmp whose operand
        # is a sete+lea constant-boolean def (`K + (cond)`) -- the
        # if/else constant-def rewrite flips the ConfBefore tie.
        try:
            _r103 = _rule103_branchy_def_note_insns(orig_insns,
                                                    recomp_insns)
            if _r103 is not None:
                console.print(f"  [green]{escape(_r103)}[/]",
                              highlight=False)
        except Exception:
            pass

    # (rae / _rov / _rover_confirmed / _parm_reload are computed ABOVE, before
    # the Rule-hints histogram, so the histogram can label rover-cascade rows.)
    if rae is not None and _rae_render is not None:
        if _rov is not None:
            from c2.commands import rover_hints as _rovmod
            console.print(
                f"  [magenta]Regalloc[/]: layer 3 register-identity swap "
                f"(RISCify {_rov.cls} rover -- not a savings/decl tie)",
                highlight=False)
            console.print(
                f"  [bright_magenta]Rover[/]: {escape(_rovmod.render(_rov))}",
                highlight=False)
        else:
            color = "dim" if rae.layer == -1 else "magenta"
            console.print(
                f"  [{color}]Regalloc[/]: {escape(_rae_render(rae))}",
                highlight=False)

    # OFFLINE closeable/blocked verdict for the rover divergence (no recompile).
    # Fires independently of the Regalloc layer + detect()'s load-pattern gate,
    # so it labels imul/add-consumed rover swaps (build_region_item) too.
    if _closeable is not None:
        from c2.commands import rover_hints as _rovmod
        _ctxt = _rovmod.render_closeability(
            _closeable, _decomp_src_lines(name),
            chain_vintages=getattr(_rh, "chain_vintages", None))
        if _ctxt:
            _ccol = "green" if _closeable[0] == "closeable" else "yellow"
            console.print(f"  [{_ccol}]{escape(_ctxt)}[/]", highlight=False)
            # lw census per closeable inject site (trace images >= 2026-07-09):
            # the concrete +1 candidates in each named gap, or the
            # kind-flip-free verdict routing to the IL-birth/walk-order class.
            if _closeable[0] == "closeable" and getattr(_rh, "lw", None):
                try:
                    from c2.regalloc import lwalk as _lwalk
                    for _ln in _closeable[2][:3]:
                        _cen = _lwalk.census_after_line(
                            _rh.lw, _rh.fr, "dword", _ln)
                        if _cen is not None:
                            console.print(
                                f"    [dim]L{_ln} gap census:[/] "
                                f"{escape(_cen.verdict())}",
                                highlight=False)
                except Exception:
                    if os.environ.get("C2_DEBUG_REGALLOC"):
                        import traceback
                        traceback.print_exc()

    if _parm_reload is not None:
        console.print(
            f"  [bright_magenta]Parm-reload[/]: {escape(_parm_reload)}",
            highlight=False)

    # PS-alloc verdict: when the diff is a pure register-identity swap,
    # replay SortConflicts' ShellSort with the tied pair's creation slots
    # exchanged and classify: REACHABLE (names the exact creations + the
    # source lever) vs NOT-TRANSPORTED (compiler-delta class, stop
    # grinding).  Uses the `cn` (AddConflictNode-birth) trace stream.
    # Pairs the ROVER diverges on are passed in so the verdict defers to
    # the Rover lever instead of claiming the (unrelated) allocator tie.
    if name and any(r["kind"] != "equal" for r in rows):
        try:
            from c2.commands import ps_alloc
            _rover_pairs: set[frozenset] = set()
            if _rov is not None:
                for _rcr, _psr in zip(_rov.rc_regs, _rov.ps_regs):
                    if _rcr and _psr and _rcr != _psr:
                        _rover_pairs.add(
                            frozenset((str(_rcr).upper(), str(_psr).upper())))
            _pv = ps_alloc.detect(name.rstrip("_"), hints, rows,
                                  rover_pairs=_rover_pairs)
            if _pv is not None:
                for _ln in ps_alloc.render_lines(_pv):
                    # Suppress the no-verdict non-results (MODEL-MISMATCH /
                    # "no verdict") -- they add a line that says nothing.
                    if ("no verdict" in _ln or "MODEL-MISMATCH" in _ln) \
                            and not _DIAG_FULL:
                        continue
                    console.print(f"  [magenta]{escape(_ln)}[/]",
                                  highlight=False)
        except Exception as _e:
            if os.environ.get("C2_DEBUG_REGALLOC"):
                import traceback
                console.print(f"  [red]ps-alloc hint error: {escape(repr(_e))}[/]")
                traceback.print_exc()

    # Cascade verdict: the ACTIONABLE swap hint.  Runs the corpus-certified
    # offline allocator cascade (c2.regalloc.replay) as an inverse search
    # and names the ONE lever class to try (tie-reorder / savings change)
    # or says STOP (unreachable by allocation order).  Gated per routine on
    # exact identity replay -- suppressed (with a notice) when leaky.
    if name and any(r["kind"] != "equal" for r in rows):
        try:
            from c2.commands import cascade_hints
            _cv_rp: set[frozenset] = set()
            if _rov is not None:
                for _rcr, _psr in zip(_rov.rc_regs, _rov.ps_regs):
                    if _rcr and _psr and _rcr != _psr:
                        _cv_rp.add(frozenset((str(_rcr).upper(),
                                              str(_psr).upper())))
            _cv = cascade_hints.detect(name.rstrip("_"), hints, rows,
                                       rover_pairs=_cv_rp)
            if _cv is not None:
                _cv_lines = cascade_hints.render_lines(_cv)
                _cv_inc = sum(1 for l in _cv_lines if "INCONCLUSIVE" in l)
                for _ln in _cv_lines:
                    # INCONCLUSIVE = a non-result ("absence means NOTHING");
                    # collapse the run to one line in the default view.
                    if "INCONCLUSIVE" in _ln and not _DIAG_FULL:
                        continue
                    console.print(f"  [magenta]{escape(_ln)}[/]",
                                  highlight=False)
                if _cv_inc and not _DIAG_FULL:
                    console.print(
                        f"  [dim]Cascade: {_cv_inc} more pair(s) inconclusive "
                        f"(replay budget; not actionable -- --full-hints)[/]",
                        highlight=False)
        except Exception as _e:
            if os.environ.get("C2_DEBUG_REGALLOC"):
                import traceback
                console.print(f"  [red]cascade hint error: {escape(repr(_e))}[/]")
                traceback.print_exc()

    # Seat-chain verdict (2026-07-11): the CERTIFIED full-chain flip
    # analysis per PS<->RC seat swap -- masks recomputed (neighbours.py
    # 100%), scores recomputed with per-ins credit provenance (crm10a_v2
    # 100%), pick replayed (100%).  One verdict per swap names the LEVER
    # CLASS (masked=live-range / outscored=credit / tie-order=Rule 115/28a
    # / vetoed / not-a-candidate) BEFORE any grinding.  `c2 seats <fn>`
    # is the drill-in with the evidence rows.
    if name and any(r["kind"] != "equal" for r in rows):
        try:
            from c2.commands import seatchain_hints
            _sc = seatchain_hints.detect(name.rstrip("_"), rows)
            if _sc is not None:
                console.print(
                    f"  [cyan]Seat-chain[/]: "
                    f"{escape(seatchain_hints.render(_sc))}",
                    highlight=False)
        except Exception as _e:
            if os.environ.get("C2_DEBUG_REGALLOC"):
                import traceback
                console.print(f"  [red]seat-chain hint error: "
                              f"{escape(repr(_e))}[/]")
                traceback.print_exc()

    # Rule 115 declaration-order lever: when the regalloc layer is 3 (caller-
    # saved register-identity swap) AND the function has ≥2 named int locals,
    # name the candidate pair to reorder.  See watcom10.0a repo docs/wcc386-re/regalloc-model.md
    # §3.  This is the lever for the half of layer-3 ties where Rule 28a's
    # use-order lever is dead (use pinned by semantics).
    if name and rae_layer == 3 and _rov is None:
        try:
            from c2.commands.decl_order_hints import detect as _doh, render as _doh_render
            dict_rows = _diff_to_json_rows(rows, hints)
            doh = _doh(name, regalloc_layer=rae_layer, diff_rows=dict_rows)
            if doh is not None:
                console.print(
                    f"  [magenta]Rule 115[/]: {escape(_doh_render(doh))}",
                    highlight=False,
                )
        except ImportError:
            pass

    # Rule 124 reader: explain the diverging picks from the gb/tg trace --
    # which knob (savings order / MOV credit / Given tie-break) produced
    # RC's register, so the agent edits the right thing instead of
    # permuting declarations.
    if name and rae_layer in (3, 5, 6):
        try:
            from c2.commands.gb_hints import detect as _gbd, render as _gbr
            from c2.commands.decl_order_hints import _swap_register_pair as _swp
            from c2.commands.regalloc_hints import _lookup as _gb_lk
            _pair2 = _swp(_diff_to_json_rows(rows, hints))
            if _pair2:
                _gr, _c2, _b3 = _gb_lk(name.rstrip("_"), None)
                _exp = _gbd(_gr, {p.upper() for p in _pair2})
                for _ln3 in _gbr(_exp):
                    console.print(f"  [magenta]GB[/]: {escape(_ln3)}",
                                  highlight=False)
        except Exception:
            if os.environ.get("C2_DEBUG_REGALLOC"):
                import traceback
                traceback.print_exc()

    # Rule 123 split-temp merge lever: same layer-3 gate.  When two same-
    # class temps' savings SUM exceeds a swapped-register owner's savings,
    # the original likely used an in-place compound op (one merged temp
    # that allocates FIRST).  Proven on the copy_ferret_run twins.
    if name and rae_layer == 3 and _rov is None:
        try:
            from c2.commands.merge_hints import detect as _mh_detect, render as _mh_render
            from c2.commands.decl_order_hints import _swap_register_pair
            from c2.commands.regalloc_hints import _lookup as _mh_lk
            _pair = _swap_register_pair(_diff_to_json_rows(rows, hints))
            if _pair:
                _mr, _mc, _mb = _mh_lk(name.rstrip("_"), None)
                _mh = _mh_detect(_mr, {p.upper() for p in _pair})
                if _mh is not None:
                    console.print(
                        f"  [magenta]Merge[/]: {escape(_mh_render(_mh))}",
                        highlight=False)
        except Exception:
            if os.environ.get("C2_DEBUG_REGALLOC"):
                import traceback
                traceback.print_exc()

    # Register-pressure spill / rematerialization (Rule 111): PS re-reads a
    # CSE-able global where the recompile holds it in a register.  Negative
    # triage — the diff is a spill tie-break, not source-shape.
    try:
        from c2.commands.spill_hints import detect_spill_class, render as _spill_render
        sp = detect_spill_class(orig_insns, recomp_insns,
                                has_body_diff=(diff_count > 0))
        if sp is not None:
            console.print(
                f"  [magenta]Spill-class[/]: {escape(_spill_render(sp))}",
                highlight=False,
            )
    except ImportError:
        pass

    # Rule 119 byte-pump workhorse rotation: function builds a multi-byte
    # composite into an accumulator with compound assigns + byte-zext loads.
    # The lever is to route byte loads through a SCRATCH local, pushing the
    # accumulator off EAX onto a callee-save.  See
    # c2/commands/byte_pump_hints.py and docs/watcom-codegen-patterns.md
    # Rule 119 for the OW v1 ``regalloc.c::CountRegMoves`` mechanism.
    if name and diff_count > 0:
        try:
            from c2.commands.byte_pump_hints import detect as _bp_detect, render as _bp_render
            bph = _bp_detect(name)
            if bph is not None:
                console.print(
                    f"  [magenta]Rule 119[/]: {escape(_bp_render(bph))}",
                    highlight=False,
                )
        except ImportError:
            pass

    # Known-zero register tail store (Rule 156): PS stores a register that the
    # flow proved == 0 (test r,r; je fall-through) -> the source statement is
    # `= 0`, NOT `= <that var>`.  The dropped use can unblock a Rule 115/28a
    # byte-seat tie.  See c2/commands/known_zero_store_hints.py.
    if name and diff_count > 0:
        try:
            from c2.commands import known_zero_store_hints as _kz
            _kzh = _kz.detect(orig_insns)
            _kzr = _kz.render(_kzh)
            if _kzr:
                console.print(
                    f"  [magenta]Rule 156[/]: {escape(_kzr)}",
                    highlight=False,
                )
        except ImportError:
            pass

    # Reload-vs-hold named-intermediate marker (Rule 116): our source declares a
    # named local caching a memory-rooted value that PS *inlines* (reloads).
    # Actionable — delete the temp, inline the expression.
    if name:
        try:
            from c2.commands.reload_hints import detect_reload_hints, render as _reload_render
            rls = detect_reload_hints(name, orig_insns,
                                      has_body_diff=(diff_count > 0))
            if rls:
                console.print(
                    f"  [magenta]Rule 116[/]: {escape(_reload_render(rls))}",
                    highlight=False,
                )
        except ImportError:
            pass

    tm_hint = _scan_tail_merge_donor(orig, orig_off, is_vaddr=False)
    if tm_hint is not None:
        _print_tail_merge(console, tm_hint, escape, rc_insns=recomp_insns)

    # Frame-level levers (c2.commands.frame_hints): hosted foreign-frame
    # blocks on the PS side (Rule 125 -- function-local work pointless)
    # and the RC-side retval-funnel homing pair (W107 join-read exile).
    try:
        from c2.commands import frame_hints as _fh
        _ff = _fh.detect_foreign_frame(name or "?", orig_insns)
        if _ff is not None:
            for _i, _ln in enumerate(_fh.render_foreign_frame(_ff)):
                _st = "[red]" if _i == 0 else "[dim]"
                console.print(f"  {_st}{escape(_ln)}[/]", highlight=False)
            # Block-ownership map: who actually executes those bytes.
            try:
                from c2.commands.tail_merge import foreign_branches, _load_symbols
                _cb = _load_symbols(Path("data/out/symbols.json")).code_base
                _fs = orig_off + _cb
                _inb, _outb = foreign_branches(_fs, _fs + len(orig))
                if _inb:
                    _src = ", ".join(
                        f"{n2}+{sr:#x}->+{do:#x}"
                        for n2, sr, do in _inb[:6])
                    console.print(
                        f"      [dim]inbound foreign branches "
                        f"({len(_inb)}): {escape(_src)}"
                        f"{' …' if len(_inb) > 6 else ''}[/]",
                        highlight=False)
                if _outb:
                    _dst = ", ".join(
                        f"+{so:#x}->{n2}+{di:#x}" for so, n2, di in _outb[:6])
                    console.print(
                        f"      [dim]outbound foreign branches "
                        f"({len(_outb)}): {escape(_dst)}"
                        f"{' …' if len(_outb) > 6 else ''}[/]",
                        highlight=False)
            except Exception:
                pass
        _rf = _fh.detect_retval_funnel(name or "?", recomp_insns)
        if _rf is not None:
            for _i, _ln in enumerate(_fh.render_retval_funnel(_rf)):
                _st = "[magenta]" if _i == 0 else "[dim]"
                console.print(f"  {_st}{escape(_ln)}[/]", highlight=False)
        # c2.c burn-down detectors (Rules 136/137/138): memory retval
        # funnel, suffix-merge direction, param-reg scratch.
        # gloops.c initreg_game_loop close-out (Rules 148/149): epilogue
        # funnel + global cached in extra callee-save (2026-06-13).
        for _det, _ren in (
            (_fh.detect_memory_retval_funnel, _fh.render_memory_retval_funnel),
            (_fh.detect_merge_direction, _fh.render_merge_direction),
            (_fh.detect_param_reg_scratch, _fh.render_param_scratch),
            (_fh.detect_epilogue_funnel, _fh.render_epilogue_funnel),
            (_fh.detect_global_in_extra_callee_save,
             _fh.render_global_in_extra_callee_save),
        ):
            _h = _det(name or "?", orig_insns, recomp_insns)
            if _h is not None:
                for _i, _ln in enumerate(_ren(_h)):
                    _st = "[magenta]" if _i == 0 else "[dim]"
                    console.print(f"  {_st}{escape(_ln)}[/]", highlight=False)
    except ImportError:
        pass

    try:
        from c2.commands.dispatch_hints import detect_dispatch_mismatch
        dm = detect_dispatch_mismatch(name, orig_insns)
        if dm is not None:
            console.print(f"  [yellow]Dispatch[/]: {escape(dm)}", highlight=False)
    except ImportError:
        pass

    if name is not None:
        try:
            from c2.commands.inferred_sig import compare_sig

            sig_diff = compare_sig(name)
            if sig_diff.has_diff:
                if sig_diff.arg_count_mismatch:
                    inferred_n = (
                        len(sig_diff.inferred.arg_regs)
                        + len(sig_diff.inferred.stack_args)
                    )
                    inferred_args = (
                        ", ".join(sig_diff.inferred.arg_regs) or "void"
                    )
                    if sig_diff.inferred.stack_args:
                        inferred_args += ", ".join(
                            f" [esp+{o:#x}]" for o in sig_diff.inferred.stack_args
                        )
                    console.print(
                        f"  [red]Sig mismatch[/]: declared takes "
                        f"[yellow]{sig_diff.declared.n_args}[/] arg(s), "
                        f"inferred [yellow]{inferred_n}[/] "
                        f"({inferred_args})",
                        highlight=False,
                    )
                if sig_diff.return_mismatch:
                    console.print(
                        f"  [red]Sig mismatch[/]: declared "
                        f"[yellow]{'void' if sig_diff.declared.returns_void else 'non-void'}[/] return, "
                        f"inferred [yellow]{'has return' if sig_diff.inferred.has_return else 'void'}[/] "
                        f"(EAX written before RET in PS asm)",
                        highlight=False,
                    )
        except (KeyError, FileNotFoundError, ValueError, ImportError):
            pass

    if name is not None:
        try:
            from c2.commands.sibling import render_sibling_hint

            sib = render_sibling_hint(name, top_n=3, min_score=0.30)
            if sib is not None:
                console.print(
                    f"  [cyan]Sibling[/]: {escape(sib)}",
                    highlight=False,
                )
        except (KeyError, FileNotFoundError, ValueError, ImportError):
            pass

    if name is not None:
        try:
            from c2.commands.crossbuild import render_crossbuild_hint

            cb = render_crossbuild_hint(name)
            if cb is not None:
                console.print(f"  [cyan]Cross-build[/]: {cb}", highlight=False)
        except (KeyError, FileNotFoundError, ValueError, ImportError):
            pass

    if name is not None:
        try:
            from c2.commands.moved_code_hints import render_moved_code_hint

            mc = render_moved_code_hint(name)
            if mc is not None:
                console.print(
                    f"  [yellow]Moved-code[/]: {escape(mc)}", highlight=False)
        except (KeyError, FileNotFoundError, ValueError, ImportError):
            pass

    if name is not None:
        try:
            from c2.commands.loop_hints import render_loops_hint

            lh = render_loops_hint(name)
            if lh is not None:
                console.print(f"  [cyan]Loops[/]: {escape(lh)}", highlight=False)
        except (KeyError, FileNotFoundError, ValueError, ImportError):
            pass

    if name is not None:
        try:
            from c2.commands.style_check import render_style_hints

            for line in render_style_hints(name):
                console.print(line, highlight=False)
        except (KeyError, FileNotFoundError, ValueError, ImportError):
            pass
        try:
            from c2.commands.global_cache_hints import render_global_cache_hints

            for line in render_global_cache_hints(name):
                console.print(line, highlight=False)
        except (KeyError, FileNotFoundError, ValueError, ImportError):
            pass
        if not _rover_confirmed:
            try:
                from c2.commands.negative_corpus import render_negative_hint

                # Cache-only + re-entry-guarded: never triggers a verify rebuild.
                for line in render_negative_hint(name):
                    console.print(line, highlight=False)
            except (KeyError, FileNotFoundError, ValueError, ImportError):
                pass
    # Returned so the side-by-side renderer can suppress its own source-shape
    # hint (line-shape) on a confirmed-rover diff.
    return _rover_confirmed


# Line-number rendering mode for the side-by-side view.  False (default):
# function-relative "L+N" (both sides rebased to their first cue -- directly
# comparable).  True (--abs-lines): absolute "L<n>" per side (PS = original
# debug-info line, RC = decomp .c file line -- greppable in the sources).
_ABS_LINES = False


def _augment_merged_tail(
    body: bytes,
    body_off: int,
    body_fix: set[int],
    *,
    code_bytes: bytes,
    code_base: int,
    resolve,
):
    """Splice a tail-merged function's borrowed epilogue back onto its body.

    When ``body`` ends in a Rule 42 tail-merge ``jmp``, the shared epilogue
    physically lives in the donor.  This returns ``(aug_body, aug_fix,
    expansion)`` where ``aug_body`` is ``body`` followed by the donor's
    tail bytes (so the side-by-side renderer can show the bytes that
    logically belong to the function) and ``aug_fix`` carries the donor's
    fixup positions remapped into the appended region.  ``expansion`` is
    the ``TailExpansion`` (or None when the body did not tail-merge, in
    which case ``body``/``body_fix`` are returned unchanged).
    """
    from c2.commands.tail_merge import expand_merged_tail
    exp = expand_merged_tail(
        body, body_off, code_bytes=code_bytes, code_base=code_base,
        resolve=resolve,
    )
    if exp is None or not exp.tail_bytes:
        return body, body_fix, None
    aug = body + exp.tail_bytes
    append_base = body_off + len(body)   # section offset of the first tail byte
    # Keep only the REAL body's fixups: entries at/after the body end belong
    # to the *next* function and would wrongly mask the appended tail bytes
    # (they share the same synthetic section offsets).  The donor tail's own
    # fixups live at the donor's offsets, so map them into the tail region.
    aug_fix = {f for f in body_fix if f < append_base}
    pos = 0
    for seg in exp.segments:
        for k in range(seg.length):
            if (seg.src_off + k) in body_fix:
                aug_fix.add(append_base + pos + k)
        pos += seg.length
    return aug, aug_fix, exp


def _render_side_by_side(
    orig: bytes,
    orig_off: int,
    recomp: bytes,
    recomp_off: int,
    orig_fix: set[int],
    recomp_fix: set[int],
    line_map: dict[int, int] | None = None,
    recomp_line_map: dict[int, int] | None = None,
    name: str | None = None,
    recomp_code: bytes | None = None,
    recomp_ranges=None,
) -> None:
    """Side-by-side renderer: PS on the left, RC on the right, one row
    per aligned instruction.  Equal rows show on both sides (dim);
    diff rows show the present side(s) coloured.  Mirrors the layout
    that `c2 cgex run <slug> --trial <name>` uses for codegen
    experiments.

    Merged-tail splice: when Watcom tail-merges a shared epilogue, the
    function's last byte is a `jmp` into a donor and the bytes that
    logically belong to the function (the pop/ret epilogue) live in the
    donor — invisible to a naive disasm.  This renderer splices those
    borrowed bytes back onto BOTH sides (following chained partial-stub
    hops) and shows them under a ``── merged epilogue tail ──`` banner,
    so a still-diffing pair can be driven until the epilogues line up and
    the merge "just happens".  When ``recomp_code``/``recomp_ranges`` are
    supplied the RC side is spliced from the freshly-built image too;
    otherwise only the PS side is.

    Layout::

          +0000  L2202  56               push esi    │  +0000  L2202  56               push esi
        * +0001  L2202  57               push edi    │  +0001  L2202  53               push ebx
          +0002          55               push ebp    │  +0002          55               push ebp
          ...                                          │  +0010                                     <empty: insert>
          ── merged epilogue tail (…) ──  PS ← donor+0xNN │ RC ← donor+0xNN
        · +0061         5b               pop ebx     │  +005e         5b               pop ebx
        · +0062         c3               ret         │  +005f         c3               ret
    """
    rows, hints = _build_diff_rows(
        orig, orig_off, recomp, recomp_off,
        orig_fix, recomp_fix, line_map,
    )
    orig_insns   = _disasm_for_diff(orig)
    recomp_insns = _disasm_for_diff(recomp)

    # soft_wrap: don't truncate or wrap long side-by-side rows at the
    # terminal width; let the terminal handle horizontal scrolling.
    # color_system=None: this output is consumed by LLMs / pipe-to-file,
    # never by a human in a colored TTY -- markup commands like
    # `[yellow]Tail-merge[/]` still parse (and are stripped from the
    # rendered text) but no ANSI escapes are emitted.
    console = Console(highlight=False, soft_wrap=True, color_system=None)
    _rover_confirmed = _render_headers(console, rows, hints, orig, orig_off,
                                       orig_insns, recomp_insns, name,
                                       recomp_off, recomp_line_map)
    _render_run_ledger(console, orig, orig_off, recomp, recomp_off,
                       orig_fix, recomp_fix, line_map, recomp_line_map,
                       name=name)

    # ── Merged-tail splice ───────────────────────────────────────
    # Watcom tail-merges shared epilogues: the function's last byte is a
    # `jmp` into a donor, and the bytes that logically belong to THIS
    # function (the pop/ret epilogue) live in the donor, invisible to a
    # naive disasm.  Splice them back onto each side so the side-by-side
    # shows the full logical function -- then a still-diffing pair can be
    # driven until the epilogues line up and the merge "just happens".
    #
    # `rows`/`hints`/`orig_insns`/`recomp_insns` above stay on the REAL
    # bytes (the headers + line-shape + stmt-map analyses depend on the
    # un-spliced shape and on `_scan_tail_merge_donor` still seeing the
    # trailing jmp).  The splice feeds a SEPARATE visual diff below.
    ps_real_len = len(orig)
    rc_real_len = len(recomp)
    aug_orig, aug_orig_fix, ps_exp = orig, orig_fix, None
    aug_recomp, aug_recomp_fix, rc_exp = recomp, recomp_fix, None
    try:
        from c2.commands.tail_merge import _load_symbols, _function_at
        _sym = _load_symbols(Path("data/out/symbols.json"))
        _ps_code, _ = _load_le_code_and_fixups(Path("data/PS.EXE"))
        aug_orig, aug_orig_fix, ps_exp = _augment_merged_tail(
            orig, orig_off, orig_fix,
            code_bytes=_ps_code, code_base=_sym.code_base,
            resolve=lambda va: _function_at(_sym, va),
        )
    except Exception:
        if os.environ.get("C2_DEBUG_REGALLOC"):
            import traceback
            traceback.print_exc()
    if recomp_code is not None and recomp_ranges is not None:
        try:
            _rc_base = 0x10000
            # RC's REAL function bytes (the passed `recomp` is sliced to the
            # PS size and may overrun into the next function, hiding RC's own
            # trailing jmp).  Recover the true extent from the linker map.
            _rc_start_va = recomp_off + _rc_base
            _rc_size = next(
                (e - s for s, e, _n in recomp_ranges if s == _rc_start_va),
                None,
            )
            _rc_real = (recomp_code[recomp_off: recomp_off + _rc_size]
                        if _rc_size else recomp)
            rc_real_len = len(_rc_real)

            def _rc_resolve(va, _rr=recomp_ranges):
                for s, e, n in _rr:
                    if s <= va < e:
                        return n, s, e
                return None

            aug_recomp, aug_recomp_fix, rc_exp = _augment_merged_tail(
                _rc_real, recomp_off, recomp_fix,
                code_bytes=recomp_code, code_base=_rc_base,
                resolve=_rc_resolve,
            )
        except Exception:
            if os.environ.get("C2_DEBUG_REGALLOC"):
                import traceback
                traceback.print_exc()

    _spliced = ps_exp is not None or rc_exp is not None
    if _spliced:
        vis_rows, vis_hints = _build_diff_rows(
            aug_orig, orig_off, aug_recomp, recomp_off,
            aug_orig_fix, aug_recomp_fix, line_map,
        )
        aug_orig_insns   = _disasm_for_diff(aug_orig)
        aug_recomp_insns = _disasm_for_diff(aug_recomp)
    else:
        vis_rows, vis_hints = rows, hints
        aug_orig_insns, aug_recomp_insns = orig_insns, recomp_insns

    # Build per-side line lookups, rebased to each side's first cue
    # within this function so the columns are directly comparable
    # ("L+0" = the function's first statement on each side).  The PS
    # cue stream comes from symbols.json; the RC cue stream comes
    # from Watcom -d1 debug info on the freshly-built LE binary.
    def _per_insn_lines(
        insns: list[InsnT], base_off: int,
        lmap: dict[int, int] | None,
    ) -> dict[int, str]:
        """rel_off -> 'L+N' string, emitted only when the line changes."""
        if not lmap:
            return {}
        # Function-local cues, sorted by code offset.
        end = base_off + max((i[0] + i[1] for i in insns), default=0)
        entries = sorted(
            (off - base_off, ln)
            for off, ln in lmap.items()
            if base_off <= off < end
        )
        if not entries:
            return {}
        base_line = entries[0][1]
        out: dict[int, str] = {}
        last: int | None = None
        idx = 0
        for rel, sz, *_ in insns:
            cur: int | None = None
            while idx < len(entries) and entries[idx][0] <= rel:
                cur = entries[idx][1]
                idx += 1
            # Use the most recent cue at-or-before this insn.
            if cur is None:
                # No cue yet reached; fall back to scanning behind us.
                cur = next(
                    (ln for off, ln in reversed(entries) if off <= rel),
                    None,
                )
            # Cues earlier than base_line belong to a *previous*
            # function whose tail spilled into this one's address
            # range -- happens on the RC side when our recompile
            # produced a longer body than PS expected and the diff
            # walker pulled in insert rows past the function end.
            # Treat them as having no cue.
            if cur is not None and cur >= base_line and cur != last:
                out[rel] = (f"L{cur}" if _ABS_LINES
                            else f"L+{cur - base_line}")
                last = cur
        return out

    ps_lines = _per_insn_lines(orig_insns,   orig_off,   line_map)
    rc_lines = _per_insn_lines(recomp_insns, recomp_off, recomp_line_map)

    # Line cues for the spliced VISUAL diff: same as above for the body,
    # but the appended donor tail carries no source lines of its own (its
    # bytes belong to the donor), so we trim each line map to the real
    # function length before mapping -- the merged-tail rows show blank in
    # the L column.  When nothing was spliced these are identical to the
    # real lookups above (and we reuse them).
    if _spliced:
        _ps_lmap_trim = ({off: ln for off, ln in (line_map or {}).items()
                          if orig_off <= off < orig_off + ps_real_len}
                         if line_map else line_map)
        _rc_lmap_trim = ({off: ln for off, ln in (recomp_line_map or {}).items()
                          if recomp_off <= off < recomp_off + rc_real_len}
                         if recomp_line_map else recomp_line_map)
        vis_ps_lines = _per_insn_lines(aug_orig_insns,   orig_off,   _ps_lmap_trim)
        vis_rc_lines = _per_insn_lines(aug_recomp_insns, recomp_off, _rc_lmap_trim)
    else:
        vis_ps_lines, vis_rc_lines = ps_lines, rc_lines

    # ── line-shape analysis ──────────────────────────────────────
    # Statement-boundary cues are LAYOUT-INDEPENDENT evidence of the
    # original's statement structure: a cue position survives comments /
    # blank lines (which only inflate the deltas).  Compare cue POSITIONS
    # across the aligned rows:
    #   * RC-only cue  -> the ORIGINAL continues its previous source line
    #     here: a multi-statement line or a combined condition (`||` /
    #     `&&` / `else if (++x > K) x = 0;`).  This is the signature that
    #     solved print3_test_info, get_industry_ov_image's ||-form and
    #     update_time (Rule 122's line form).
    #   * PS-only cue  -> the original STARTS a statement where our source
    #     continues one: split the RC expression/line.
    # Render only for diffing functions (equal rows on both sides still
    # carry cues, so the shape comparison works on exact code too -- but
    # the hint is for steering rewrites).
    if any(r["kind"] != "equal" for r in rows):
        rc_only, ps_only = [], []
        for row in rows:
            o, rr_ = row.get("o"), row.get("r")
            if o is None or rr_ is None:
                continue            # insert/delete rows: alignment too weak
            pc = ps_lines.get(o[0])
            rc = rc_lines.get(rr_[0])
            if rc and not pc:
                rc_only.append((o[0], rc))
            elif pc and not rc:
                ps_only.append((o[0], pc))
        if (rc_only or ps_only) and not _rover_confirmed:
            bits = []
            if rc_only:
                bits.append("RC-only cue (original packs onto the PREVIOUS "
                            "line -- multi-stmt line / ||,&&-combined): "
                            + ", ".join(f"+{off:04x}({cue})"
                                        for off, cue in rc_only[:6])
                            + (" …" if len(rc_only) > 6 else ""))
            if ps_only:
                bits.append("PS-only cue (original STARTS a statement here "
                            "-- split the RC line/expression): "
                            + ", ".join(f"+{off:04x}({cue})"
                                        for off, cue in ps_only[:6])
                            + (" …" if len(ps_only) > 6 else ""))
            console.print(
                f"  [cyan]line-shape: {len(rc_only)+len(ps_only)} statement-"
                f"boundary mismatch(es).  " + "  ".join(bits) + "[/]",
                highlight=False)

        # Statement map + per-statement forward/reverse IR (the fine-
        # grained refinement: segments the aligned rows at PS cue
        # positions, maps each original statement to the RC lines it
        # covers, and for diverging statements diffs the forward trace
        # tree against the binir-recovered PS shapes AT THAT STATEMENT).
        try:
            from c2.commands import stmt_map as _sm
            _forest = None
            if name:
                try:
                    from c2.commands.regalloc_hints import _lookup as _lk
                    _r, _c, _b2 = _lk(name.rstrip("_"), None)
                    _forest = (_r or {}).get("ir")
                except Exception:
                    _forest = None
            _rc_abs = None
            if recomp_line_map:
                _rc_abs = {off - recomp_off: ln
                           for off, ln in recomp_line_map.items()
                           if recomp_off <= off < recomp_off + len(recomp)}
            _h = _sm.build(name or "?", rows, ps_lines, rc_lines,
                           rc_abs=_rc_abs, forest=_forest)
            if _h is not None:
                for _ln2 in _sm.render_lines(_h):
                    console.print(f"  [cyan]{escape(_ln2)}[/]",
                                  highlight=False)
        except Exception:
            if os.environ.get("C2_DEBUG_REGALLOC"):
                import traceback
                traceback.print_exc()

    def _bytes(tokens: list[str], diff_positions: list[int]) -> str:
        if not tokens:
            return ""
        ds = set(diff_positions)
        partial = 0 < len(ds) < len(tokens)
        return " ".join(
            f"[{t}]" if (partial and i in ds) else t
            for i, t in enumerate(tokens)
        )

    # First pass: build raw cell text for each side so we can size the
    # bytes column.  Cell layout: "+OOOO  LNNNN  bytes  asm".
    cells: list[tuple[dict, object, str | None, str | None,
                      str, str, str, str]] = []
    # A cell is "borrowed" when either side's instruction lives in the
    # spliced merged tail (offset past that side's real function length).
    cell_borrowed: list[bool] = []
    max_ps_b = 0
    max_rc_b = 0
    for row, hint in zip(vis_rows, vis_hints):
        ps_b = _bytes(row["ps_tokens"], row["ps_diff"]) if row["o"] else ""
        rc_b = _bytes(row["rc_tokens"], row["rc_diff"]) if row["r"] else ""
        ps_asm = _simplify_operands(row["o"][3]) if row["o"] else ""
        rc_asm = _simplify_operands(row["r"][3]) if row["r"] else ""
        ps_off = f"+{row['o'][0]:04x}" if row["o"] else ""
        rc_off = f"+{row['r'][0]:04x}" if row["r"] else ""
        ps_ln  = vis_ps_lines.get(row["o"][0], "") if row["o"] else ""
        rc_ln  = vis_rc_lines.get(row["r"][0], "") if row["r"] else ""
        borrowed = bool(
            (row["o"] and row["o"][0] >= ps_real_len)
            or (row["r"] and row["r"][0] >= rc_real_len)
        )
        max_ps_b = max(max_ps_b, len(ps_b))
        max_rc_b = max(max_rc_b, len(rc_b))
        cells.append((row, hint, ps_off or None, rc_off or None,
                      ps_b, rc_b, ps_asm, rc_asm, ps_ln, rc_ln))
        cell_borrowed.append(borrowed)
    # Cap byte-column width so monster operand lines don't blow the
    # screen out; long bytes simply push asm rightward on that row.
    ps_w = min(max_ps_b, 28)
    rc_w = min(max_rc_b, 28)
    ln_w = 6  # "L+NNN "
    off_w = 6  # "+OOOO "
    # Widest asm string on the PS side, so we can pad the left half to
    # a fixed width and the central gutter lines up vertically.
    max_ps_asm = max(
        (len(c[6]) for c in cells), default=0,
    )
    half_w = off_w + 1 + ln_w + 1 + ps_w + 2 + max_ps_asm

    # Windowing: by default collapse long runs of byte-identical rows so the
    # diff rows + a few lines of context dominate the output.  --full-hints
    # (or C2_FULL_HINTS=1) prints every row.  An interesting cell is any
    # alignment diff (kind != equal) or any row carrying a rule hint.
    n_cells = len(cells)
    if _DIAG_FULL:
        show_idx = set(range(n_cells))
    else:
        # Always show the spliced merged-tail rows -- they are the whole
        # point of the splice (the bytes that belong to the function even
        # when both sides merged identically), so never let windowing
        # collapse them as "unchanged".
        interesting = [
            i for i, c in enumerate(cells)
            if c[0]["kind"] != "equal" or c[1] is not None or cell_borrowed[i]
        ]
        show_idx = set()
        for i in interesting:
            for j in range(i - _DIAG_CONTEXT, i + _DIAG_CONTEXT + 1):
                if 0 <= j < n_cells:
                    show_idx.add(j)
        # No diffs at all (e.g. size-only mismatch): show everything rather
        # than an empty pane.
        if not interesting:
            show_idx = set(range(n_cells))

    def _tail_side_desc(exp, body: bytes) -> str:
        if exp is not None:
            return (f"{exp.label} ({len(exp.tail_bytes)}b"
                    f"{', ret' if exp.ends_in_ret else ''})")
        # No splice on this side: did it end in a ret (inline epilogue, the
        # merge has not fired yet) or something else?  ``body`` here is the
        # real function body (aug == real when nothing was spliced).
        tail_insns = _disasm_for_diff(body)
        if tail_insns and tail_insns[-1][3].split()[0] == "ret":
            return "inline epilogue (not merged \u2014 drive it to match)"
        return "(no merged tail)"

    tail_banner = None
    if _spliced:
        tail_banner = (
            "── merged epilogue tail (Watcom folded the shared epilogue; "
            "spliced back for alignment) ──\n"
            f"         PS \u2190 {_tail_side_desc(ps_exp, aug_orig)}"
            f"   \u2502   RC \u2190 {_tail_side_desc(rc_exp, aug_recomp)}"
        )

    prev_shown = -1
    banner_done = False
    for idx, (row, hint, ps_off, rc_off, ps_b, rc_b,
              ps_asm, rc_asm, ps_ln, rc_ln) in enumerate(cells):
        if idx not in show_idx:
            continue
        gap = idx - prev_shown - 1
        if gap > 0:
            console.print(
                f"     [dim]… {gap} unchanged row(s) elided "
                f"(--full-hints to show) …[/]", highlight=False)
        prev_shown = idx
        # Announce the merged tail just before its first row.
        if cell_borrowed[idx] and not banner_done and tail_banner:
            for _bl in tail_banner.split("\n"):
                console.print(f"     [yellow]{escape(_bl)}[/]", highlight=False)
            banner_done = True
        kind = row["kind"]
        # Colour each side: equal rows dim, diff sides bright.
        if kind == "equal":
            ps_colour = rc_colour = "dim"
            mark = "\u00b7" if cell_borrowed[idx] else " "
        elif kind == "replace":
            ps_colour, rc_colour = "red", "green"
            mark = "*"
        elif kind == "delete":
            ps_colour, rc_colour = "red", "dim"
            mark = "*"
        else:  # insert
            ps_colour, rc_colour = "dim", "green"
            mark = "*"

        def _half(off: str | None, ln: str, b: str, asm: str,
                  colour: str, b_w: int) -> str:
            if off is None:
                return " " * half_w
            ln_pad = f"{ln:<{ln_w}}"
            b_pad = b + " " * max(0, b_w - len(b))
            # Visible width: off + space + ln + space + bytes + 2sp + asm.
            visible = off_w + 1 + ln_w + 1 + len(b_pad) + 2 + len(asm)
            pad = " " * max(0, half_w - visible)
            text = f"{off:<{off_w}} {ln_pad} {escape(b_pad)}  {escape(asm)}"
            return f"[{colour}]{text}[/]{pad}"

        # Source-line column belongs to each side independently now
        # that we extract Watcom -d1 debug info from the recompile.
        # ps_ln / rc_ln are pre-rebased to function-start ("L+0").

        # Source-line column belongs to PS only (the recomp side often
        # has no line info from the wcc build); show ln on PS half,
        # blank on RC half.
        left  = _half(ps_off, ps_ln, ps_b, ps_asm, ps_colour, ps_w)
        right = _half(rc_off, rc_ln, rc_b, rc_asm, rc_colour, rc_w)
        hint_str = (
            f"  [yellow]{escape(hint.rule)}: {escape(hint.summary)}[/]"
            if hint else ""
        )
        console.print(f"  {mark} {left}  \u2502  {right}{hint_str}",
                      highlight=False)

    if not _DIAG_FULL:
        console.print(
            "     [dim]note: -v shows a focused view (windowed disasm; "
            "regalloc per-line table, raw IR-signature dicts, full disasm, "
            "PS-only/RC-only op list capped, Cascade-inconclusive collapsed, "
            "PS-alloc no-verdict suppressed).  Re-run with --full-hints for "
            "everything; see AGENTS.md Hard Rule #5.[/]",
            highlight=False)


def _render_compact(
    orig: bytes,
    orig_off: int,
    recomp: bytes,
    recomp_off: int,
    orig_fix: set[int],
    recomp_fix: set[int],
    line_map: dict[int, int] | None = None,
    name: str | None = None,
) -> None:
    """One-line-per-row diff renderer.  Designed to be readable cold by
    any reader who already understands x86 + diff terminology -- no
    legend, no custom symbols.

    Each row is a single line.  Equal (matching) rows show one side
    only; diff rows show both side-by-side::

        +0000          push esi
        +0001          push edi
        +0002          push ebp
        +0003          sub esp, 4
        +0006          mov ebp, eax
        ...
        +001a  replace PS: 89 c2  mov edx, eax    RC: 88 c2  mov dl, al
        +0030  delete  PS: 5d  pop ebp
        +0033  insert  RC: c7 05 ?? ?? ?? ?? 00  <raw 7b>

    Header lines (printed once per function):

    * ``PS callee-saves: ebx ecx edx esi edi ebp``
      ``RC callee-saves: ebx ecx edx esi``  *(divergent)*
    * ``Rule hints: 1x Rule 16; 0 unexplained``

    Differences from the legacy --full format:
      * 1 line per diff instead of 3 (drops `-PS` / `+RC` line headers)
      * `dword ptr ` qualifiers stripped from operands (implicit in 32-
        bit code; `byte ptr` / `word ptr` retained because they carry
        width info)
      * regalloc summary line and rule histogram printed at the top
      * equal rows still shown -- they're 1 line each anyway and they
        anchor the diff in the function structure
    """
    rows, hints = _build_diff_rows(
        orig, orig_off, recomp, recomp_off,
        orig_fix, recomp_fix, line_map,
    )

    # Disassemble both sides separately for the regalloc summary
    # (we want the original prologue ordering, not the diff-merged view).
    orig_insns   = _disasm_for_diff(orig)
    recomp_insns = _disasm_for_diff(recomp)
    ps_saves = _detect_callee_saves(orig_insns)
    rc_saves = _detect_callee_saves(recomp_insns)

    console = Console(highlight=False, color_system=None)

    # (Inline header block kept for now; _render_headers() is the
    # factored version used by --side-by-side.  Keeping the inline
    # copy avoids destabilising the well-trodden compact path; the
    # two stay in sync by code review.)
    # Header: regalloc summary.
    if ps_saves or rc_saves:
        ps_str = " ".join(ps_saves) if ps_saves else "(none)"
        rc_str = " ".join(rc_saves) if rc_saves else "(none)"
        if ps_saves != rc_saves:
            console.print(
                f"  [red]PS callee-saves[/]: {escape(ps_str)}", highlight=False)
            console.print(
                f"  [green]RC callee-saves[/]: {escape(rc_str)}  "
                f"[yellow](divergent)[/]", highlight=False)
        else:
            console.print(
                f"  [dim]callee-saves[/]: {escape(ps_str)}", highlight=False)

    _render_frame_alloc(console, orig_insns, recomp_insns, rows)
    _render_slot_swap(console, orig_insns, recomp_insns, rows, name=name)
    _render_schedule(console, name, orig_insns, recomp_insns, rows)
    _render_binir_shape(console, rows)

    # Header: prologue-divergence hint.  This looks at the *raw* PS/RC
    # prologue push sets (including exotic pushes like EAX/DS that the
    # callee-save summary intentionally filters out) and points at either
    # a real pragma lever or a source-shape lever.
    try:
        from c2.commands.pragma_hints import detect_pragma_hint, render_hint_lines

        pragma_hint = detect_pragma_hint(orig_insns, recomp_insns)
        if pragma_hint is not None:
            lines = render_hint_lines(pragma_hint)
            sev_color = {
                "high": "red",
                "medium": "yellow",
                "low": "dim",
            }.get(pragma_hint.severity, "yellow")
            console.print(
                f"  [{sev_color}]Prologue hint[/]: {escape(lines[0])}",
                highlight=False,
            )
            if len(lines) > 1:
                console.print(
                    f"  [{sev_color}]{escape(lines[1])}[/]",
                    highlight=False,
                )
    except ImportError:
        pass

    # Header: rule histogram.
    hist = histogram(hints)
    diff_count = sum(1 for r in rows if r["kind"] != "equal")
    if diff_count > 0:
        explained = sum(hist.values())
        unexpl = diff_count - explained
        parts = [f"{n}x {rule}" for rule, n in sorted(hist.items())]
        tail = (f"; {unexpl} unexplained" if unexpl > 0
                else "; all explained")
        if parts:
            console.print(
                f"  [yellow]Rule hints[/]: {', '.join(parts)}{tail}",
                highlight=False,
            )
            try:
                from c2.commands.rules_registry import (
                    verdicts_for_hist as _vfh, render_verdict_lines as _rvl)
                for vline in _rvl(_vfh(hist.keys())):
                    console.print(f"    [dim]·[/] {vline}", highlight=False)
            except Exception:
                pass
        elif unexpl > 0:
            console.print(
                f"  [yellow]Rule hints[/]: {unexpl} diff(s), none matched",
                highlight=False,
            )

    # Header: Rule 42 tail-merge donor (if any).  Always scanned, even
    # when the diff count is 0 (the function may already be byte-exact
    # *because* it merged into a donor — surfacing that helps the
    # decomp writer understand the dependency).  When the donor itself
    # diffs (per the last full verify run cached in verify.json), the
    # rendered hint is annotated DONOR-BLOCKED so the operator skips
    # this function until the donor is byte-exact.
    tm_hint = _scan_tail_merge_donor(orig, orig_off, is_vaddr=False)
    if tm_hint is not None:
        _print_tail_merge(console, tm_hint, escape, rc_insns=recomp_insns)

    # Frame-level levers (c2.commands.frame_hints): hosted foreign-frame
    # blocks on the PS side (Rule 125 -- function-local work pointless)
    # and the RC-side retval-funnel homing pair (W107 join-read exile).
    try:
        from c2.commands import frame_hints as _fh
        _ff = _fh.detect_foreign_frame(name or "?", orig_insns)
        if _ff is not None:
            for _i, _ln in enumerate(_fh.render_foreign_frame(_ff)):
                _st = "[red]" if _i == 0 else "[dim]"
                console.print(f"  {_st}{escape(_ln)}[/]", highlight=False)
            # Block-ownership map: who actually executes those bytes.
            try:
                from c2.commands.tail_merge import foreign_branches, _load_symbols
                _cb = _load_symbols(Path("data/out/symbols.json")).code_base
                _fs = orig_off + _cb
                _inb, _outb = foreign_branches(_fs, _fs + len(orig))
                if _inb:
                    _src = ", ".join(
                        f"{n2}+{sr:#x}->+{do:#x}"
                        for n2, sr, do in _inb[:6])
                    console.print(
                        f"      [dim]inbound foreign branches "
                        f"({len(_inb)}): {escape(_src)}"
                        f"{' …' if len(_inb) > 6 else ''}[/]",
                        highlight=False)
                if _outb:
                    _dst = ", ".join(
                        f"+{so:#x}->{n2}+{di:#x}" for so, n2, di in _outb[:6])
                    console.print(
                        f"      [dim]outbound foreign branches "
                        f"({len(_outb)}): {escape(_dst)}"
                        f"{' …' if len(_outb) > 6 else ''}[/]",
                        highlight=False)
            except Exception:
                pass
        _rf = _fh.detect_retval_funnel(name or "?", recomp_insns)
        if _rf is not None:
            for _i, _ln in enumerate(_fh.render_retval_funnel(_rf)):
                _st = "[magenta]" if _i == 0 else "[dim]"
                console.print(f"  {_st}{escape(_ln)}[/]", highlight=False)
        # c2.c burn-down detectors (Rules 136/137/138): memory retval
        # funnel, suffix-merge direction, param-reg scratch.
        # gloops.c initreg_game_loop close-out (Rules 148/149): epilogue
        # funnel + global cached in extra callee-save (2026-06-13).
        for _det, _ren in (
            (_fh.detect_memory_retval_funnel, _fh.render_memory_retval_funnel),
            (_fh.detect_merge_direction, _fh.render_merge_direction),
            (_fh.detect_param_reg_scratch, _fh.render_param_scratch),
            (_fh.detect_epilogue_funnel, _fh.render_epilogue_funnel),
            (_fh.detect_global_in_extra_callee_save,
             _fh.render_global_in_extra_callee_save),
        ):
            _h = _det(name or "?", orig_insns, recomp_insns)
            if _h is not None:
                for _i, _ln in enumerate(_ren(_h)):
                    _st = "[magenta]" if _i == 0 else "[dim]"
                    console.print(f"  {_st}{escape(_ln)}[/]", highlight=False)
    except ImportError:
        pass

    try:
        from c2.commands.dispatch_hints import detect_dispatch_mismatch
        dm = detect_dispatch_mismatch(name, orig_insns)
        if dm is not None:
            console.print(f"  [yellow]Dispatch[/]: {escape(dm)}", highlight=False)
    except ImportError:
        pass

    # Header: reload-vs-hold named-intermediate marker (Rule 116).
    if name:
        try:
            from c2.commands.reload_hints import detect_reload_hints, render as _reload_render
            _diff_count = sum(1 for r in rows if r["kind"] != "equal")
            rls = detect_reload_hints(name, orig_insns,
                                      has_body_diff=(_diff_count > 0))
            if rls:
                console.print(
                    f"  [magenta]Rule 116[/]: {escape(_reload_render(rls))}",
                    highlight=False,
                )
        except ImportError:
            pass

    # Header: declared-vs-inferred signature mismatch (if any).
    # A wrong stub signature — e.g., the caller declares
    # `void f(int x)` but the callee actually takes no args —
    # forces Watcom to keep the caller's arg in EAX across the
    # call, cascading into 20-50 byte regalloc diffs.  Surfacing
    # the mismatch early is a high-leverage hint.
    if name is not None:
        try:
            from c2.commands.inferred_sig import compare_sig

            sig_diff = compare_sig(name)
            if sig_diff.has_diff:
                if sig_diff.arg_count_mismatch:
                    inferred_n = (
                        len(sig_diff.inferred.arg_regs)
                        + len(sig_diff.inferred.stack_args)
                    )
                    inferred_args = (
                        ", ".join(sig_diff.inferred.arg_regs) or "void"
                    )
                    if sig_diff.inferred.stack_args:
                        inferred_args += ", ".join(
                            f" [esp+{o:#x}]" for o in sig_diff.inferred.stack_args
                        )
                    console.print(
                        f"  [red]Sig mismatch[/]: declared takes "
                        f"[yellow]{sig_diff.declared.n_args}[/] arg(s), "
                        f"inferred [yellow]{inferred_n}[/] "
                        f"({inferred_args})",
                        highlight=False,
                    )
                if sig_diff.return_mismatch:
                    console.print(
                        f"  [red]Sig mismatch[/]: declared "
                        f"[yellow]{'void' if sig_diff.declared.returns_void else 'non-void'}[/] return, "
                        f"inferred [yellow]{'has return' if sig_diff.inferred.has_return else 'void'}[/] "
                        f"(EAX written before RET in PS asm)",
                        highlight=False,
                    )
        except (KeyError, FileNotFoundError, ValueError, ImportError):
            pass

    # Header: byte-exact sibling hint.  Find the closest already-
    # byte-exact PS function via shingle similarity --- gives the
    # agent a verified C-source template to study when this
    # function's structure resembles a sibling already decompiled
    # exactly.  Filtered to byte-exact only so hints are always
    # actionable.  See `c2 sibling --help` and AGENTS.md §
    # "Sibling Hints".
    if name is not None:
        try:
            from c2.commands.sibling import render_sibling_hint

            sib = render_sibling_hint(name, top_n=3, min_score=0.30)
            if sib is not None:
                console.print(
                    f"  [cyan]Sibling[/]: {escape(sib)}",
                    highlight=False,
                )
        except (KeyError, FileNotFoundError, ValueError, ImportError):
            pass

    if name is not None:
        try:
            from c2.commands.crossbuild import render_crossbuild_hint

            cb = render_crossbuild_hint(name)
            if cb is not None:
                console.print(f"  [cyan]Cross-build[/]: {cb}", highlight=False)
        except (KeyError, FileNotFoundError, ValueError, ImportError):
            pass

    if name is not None:
        try:
            from c2.commands.moved_code_hints import render_moved_code_hint

            mc = render_moved_code_hint(name)
            if mc is not None:
                console.print(
                    f"  [yellow]Moved-code[/]: {escape(mc)}", highlight=False)
        except (KeyError, FileNotFoundError, ValueError, ImportError):
            pass

    if name is not None:
        try:
            from c2.commands.loop_hints import render_loops_hint

            lh = render_loops_hint(name)
            if lh is not None:
                console.print(f"  [cyan]Loops[/]: {escape(lh)}", highlight=False)
        except (KeyError, FileNotFoundError, ValueError, ImportError):
            pass

    # Per-row rendering.  Bytes are bracketed on the differing
    # positions of a partial-byte diff (tells you exactly which byte
    # of a multi-byte instruction changed).  When every byte differs
    # we drop brackets -- the asm delta on the right carries the signal.
    def _bytes(tokens: list[str], diff_positions: list[int]) -> str:
        if not tokens:
            return ""
        ds = set(diff_positions)
        partial = 0 < len(ds) < len(tokens)
        return " ".join(
            f"[{t}]" if (partial and i in ds) else t
            for i, t in enumerate(tokens)
        )

    for row, hint in zip(rows, hints):
        off_str = f"+{row['off']:04x}"
        ln_str = f"L{row['ln']}" if row["ln"] is not None else ""
        ln_col = f" {ln_str}" if ln_str else ""

        if row["kind"] == "equal":
            ps_b = _bytes(row["ps_tokens"], [])
            o_asm = _simplify_operands(row["o"][3]) if row["o"] else ""
            console.print(
                f"  [dim]{off_str}{ln_col}          "
                f"{escape(ps_b)}  {escape(o_asm)}[/]",
                highlight=False,
            )
            continue

        kind_word = row["kind"]  # "replace" | "delete" | "insert"
        ps_b = _bytes(row["ps_tokens"], row["ps_diff"]) if row["o"] else ""
        rc_b = _bytes(row["rc_tokens"], row["rc_diff"]) if row["r"] else ""
        ps_asm = _simplify_operands(row["o"][3]) if row["o"] else ""
        rc_asm = _simplify_operands(row["r"][3]) if row["r"] else ""

        if row["kind"] == "replace":
            body = (
                f"[red]PS: {escape(ps_b)}  {escape(ps_asm)}[/]"
                f"    "
                f"[green]RC: {escape(rc_b)}  {escape(rc_asm)}[/]"
            )
        elif row["kind"] == "delete":
            body = f"[red]PS: {escape(ps_b)}  {escape(ps_asm)}[/]"
        else:  # insert
            body = f"[green]RC: {escape(rc_b)}  {escape(rc_asm)}[/]"

        hint_str = (
            f"    [yellow]{escape(hint.rule)}: {escape(hint.summary)}[/]"
            if hint else ""
        )
        console.print(
            f"  {off_str}{ln_col}  {kind_word:7} {body}{hint_str}",
            highlight=False,
        )


def _render_diff(
    orig: bytes,
    orig_off: int,
    recomp: bytes,
    recomp_off: int,
    orig_fix: set[int],
    recomp_fix: set[int],
    line_map: dict[int, int] | None = None,
) -> None:
    """Print unified-diff-style annotated disassembly of orig vs recomp.

    See module-level comment above _build_diff_rows for the format.
    """
    rows, hints = _build_diff_rows(
        orig, orig_off, recomp, recomp_off,
        orig_fix, recomp_fix, line_map,
    )

    # Pre-render each row's bracketed bytes.  We measure visible width
    # *before* escaping for Rich (escape() inserts backslashes that the
    # console strips) so the asm column lines up correctly.
    rendered: list[tuple[dict, str | None, str | None, int, int]] = []
    max_bytes_w = 0
    for row in rows:
        ps_b = _bracket_tokens(row["ps_tokens"], row["ps_diff"]) if row["o"] else None
        rc_b = _bracket_tokens(row["rc_tokens"], row["rc_diff"]) if row["r"] else None
        ps_w = len(ps_b) if ps_b else 0
        rc_w = len(rc_b) if rc_b else 0
        max_bytes_w = max(max_bytes_w, ps_w, rc_w)
        rendered.append((row, ps_b, rc_b, ps_w, rc_w))
    # Cap the alignment column at a reasonable width — long instructions
    # (rare; mostly memory operands with large displacements) just push
    # asm rightward without breaking the layout.
    bytes_w = min(max_bytes_w, 36)

    def _pad(s: str, visible_w: int) -> str:
        """Right-pad with spaces to align asm columns, then escape for Rich.
        Padding is added before escaping so backslash-bracket sequences
        don't widen the visible string."""
        pad = " " * max(0, bytes_w - visible_w)
        return escape(s) + pad

    console = Console(highlight=False, color_system=None)

    # Header: prologue-divergence hint (legacy --full renderer).
    try:
        from c2.commands.pragma_hints import detect_pragma_hint, render_hint_lines

        pragma_hint = detect_pragma_hint(_disasm_for_diff(orig), _disasm_for_diff(recomp))
        if pragma_hint is not None:
            lines = render_hint_lines(pragma_hint)
            sev_color = {
                "high": "red",
                "medium": "yellow",
                "low": "dim",
            }.get(pragma_hint.severity, "yellow")
            console.print(
                f"  [{sev_color}]Prologue hint[/]: {escape(lines[0])}",
                highlight=False,
            )
            if len(lines) > 1:
                console.print(
                    f"  [{sev_color}]{escape(lines[1])}[/]",
                    highlight=False,
                )
    except ImportError:
        pass

    # Header: Rule 42 tail-merge donor (if any).  Donor status (diff /
    # byte-exact) is fetched from the verify.json cache so a stale donor
    # diff blocks this function visibly.
    tm_hint = _scan_tail_merge_donor(orig, orig_off, is_vaddr=False)
    if tm_hint is not None:
        _print_tail_merge(console, tm_hint, escape)

    for (row, ps_b, rc_b, ps_w, rc_w), hint in zip(rendered, hints):
        off_str = f"+{row['off']:04x}"
        ln_str  = f"L{row['ln']}" if row["ln"] is not None else ""
        ln_pad  = f"{ln_str:<6}"

        if row["kind"] == "equal":
            # One compact line.
            o_asm = row["o"][3] if row["o"] else ""
            console.print(
                f"  {off_str}  [cyan]{ln_pad}[/]  "
                f"[dim]{_pad(ps_b or '', ps_w)}[/]  {escape(o_asm)}",
                highlight=False,
            )
            continue

        # Diff row header.
        kind_label = {
            "replace": "[bold red]replace[/]",
            "insert":  "[bold green]insert (recomp only)[/]",
            "delete":  "[bold red]delete (PS.EXE only)[/]",
        }[row["kind"]]
        console.print(
            f"  {off_str}  [cyan]{ln_pad}[/]  {kind_label}",
            highlight=False,
        )
        # Diff-side prefix is sized so its bytes column starts at the
        # same screen column as equal rows: equal-row prefix is
        # "  +XXXX  LNNNN   " (2+5+2+6+2 = 17 chars before bytes); the
        # diff-side prefix "            -PS  " is 12+3+2 = 17 chars.
        if row["o"] is not None:
            o_asm = row["o"][3]
            console.print(
                f"            [red]-PS[/]  "
                f"[red]{_pad(ps_b or '', ps_w)}[/]  [red]{escape(o_asm)}[/]",
                highlight=False,
            )
        if row["r"] is not None:
            r_asm = row["r"][3]
            console.print(
                f"            [green]+RC[/]  "
                f"[green]{_pad(rc_b or '', rc_w)}[/]  [green]{escape(r_asm)}[/]",
                highlight=False,
            )
        if hint is not None:
            console.print(
                f"            [yellow]hint[/]  [yellow]{escape(hint.rule)} — {escape(hint.summary)}[/]",
                highlight=False,
            )

    # Per-function rule histogram
    hist = histogram(hints)
    if hist:
        diff_count  = sum(1 for r in rows if r["kind"] != "equal")
        explained   = sum(hist.values())
        unexplained = diff_count - explained
        parts = [f"{n}× {rule}" for rule, n in sorted(hist.items())]
        console.print(
            f"  [yellow]Rule hints[/]: {', '.join(parts)}"
            + (f"; {unexplained} diff row(s) unexplained"
               if unexplained > 0 else "; all diff rows explained")
        )


def _run_ledger_for(
    orig: bytes, orig_off: int, recomp: bytes, recomp_off: int,
    orig_fix: set[int], recomp_fix: set[int],
    line_map: dict[int, int] | None,
    recomp_line_map: dict[int, int] | None,
):
    """Build the dual -d1 run ledger (c2.runledger) for one function.

    Segments EACH side by its OWN line marks and aligns the register-blind
    canonical instruction streams -- attribution-exact at any function
    size (unlike the byte-diff-aligned per-line views, which drift past
    the first length-changing diff).  Returns a RunLedger or None when
    either side's marks are unavailable.
    """
    if not recomp_line_map or not line_map:
        return None
    from c2.runledger import ledger_from_raw
    ps_marks = {off - orig_off: ln for off, ln in line_map.items()
                if orig_off <= off < orig_off + len(orig)}
    rc_marks = {off - recomp_off: ln for off, ln in recomp_line_map.items()
                if recomp_off <= off < recomp_off + len(recomp)}
    if not ps_marks or not rc_marks:
        return None
    try:
        return ledger_from_raw(
            _disasm_for_diff(orig), ps_marks,
            {f - orig_off for f in orig_fix
             if orig_off <= f < orig_off + len(orig)}, orig,
            _disasm_for_diff(recomp), rc_marks,
            {f - recomp_off for f in recomp_fix
             if recomp_off <= f < recomp_off + len(recomp)}, recomp,
        )
    except Exception:
        return None


def _render_run_ledger(
    console, orig: bytes, orig_off: int, recomp: bytes, recomp_off: int,
    orig_fix: set[int], recomp_fix: set[int],
    line_map: dict[int, int] | None,
    recomp_line_map: dict[int, int] | None,
    name: str | None = None,
) -> None:
    """Print the `Run-ledger:` hint -- the dual-marks statement-level
    verdict.  ``regalloc_pure`` (all insns match register-blind) kills
    source-restructuring theories in one line; ``shape_islands`` lists
    the top islands with EXACT dual line attribution (PS L<n> = original
    -d1 witness / RC:<n> = our source's line) + family tags.  Full view:
    ``c2 ledger <fn>``."""
    led = _run_ledger_for(orig, orig_off, recomp, recomp_off,
                          orig_fix, recomp_fix, line_map, recomp_line_map)
    if led is None or not led.ps_total:
        return
    if not led.islands:
        console.print(
            f"  [green]Run-ledger[/]: all {led.matched}/{led.ps_total} insns "
            f"match register-blind (marks PS {led.ps_marks} / RC "
            f"{led.rc_marks}) -- the ENTIRE diff is register seats / slots / "
            f"encoding.  Do not restructure the source: c2 regtrace"
            + (f" {name}" if name else ""),
            highlight=False)
        return
    console.print(
        f"  [magenta]Run-ledger[/]: {led.matched}/{led.ps_total} insns match "
        f"register-blind; {len(led.islands)} island(s) over "
        f"{led.ps_runs_divergent}/{led.ps_runs_total} PS line-runs"
        + (f" (+{led.rc_only_runs} RC-only)" if led.rc_only_runs else "")
        + (f"  ·  full: c2 ledger {name}" if name else ""),
        highlight=False)
    for isl in led.islands[:10]:
        pls = ",".join(str(x) for x in isl.ps_lines) or "-"
        rls = ",".join(str(x) for x in isl.rc_lines) or "-"
        tags = "/".join(isl.tags)
        head_ps = isl.ps[0].text if isl.ps else ""
        head_rc = isl.rc[0].text if isl.rc else ""
        console.print(
            f"    [dim]·[/] [magenta]{escape(tags)}[/] PS L{pls} | RC:{rls}  "
            f"{escape(head_ps)}"
            + (f"  <>  {escape(head_rc)}" if head_rc else "")
            + (f"  (+{max(len(isl.ps), len(isl.rc)) - 1} more)"
               if max(len(isl.ps), len(isl.rc)) > 1 else ""),
            highlight=False)
    if len(led.islands) > 10:
        console.print(
            f"    [dim]… {len(led.islands) - 10} more island(s) -- "
            f"c2 ledger {name or '<fn>'}[/]", highlight=False)


def _seat_recon_for_json(
    orig: bytes, orig_off: int, recomp: bytes, recomp_off: int,
    orig_fix: set[int], recomp_fix: set[int],
    line_map: dict[int, int] | None,
) -> dict:
    """Asm-only PS↔RC register-seat reconstruction (no container).

    Aligns PS/RC, recovers the register permutation between the two
    allocations, and classifies the function clean/swap/ambiguous.  For a
    byte-exact (identically-allocated) function this is ``clean``."""
    from c2.regalloc.seat_recon import seat_diff
    rows, _ = _build_diff_rows(
        orig, orig_off, recomp, recomp_off, orig_fix, recomp_fix, line_map,
    )
    return seat_diff(rows)


def _width_recon_for_json(
    orig: bytes, orig_off: int, recomp: bytes, recomp_off: int,
    orig_fix: set[int], recomp_fix: set[int],
    line_map: dict[int, int] | None,
) -> dict:
    """Asm-only PS<->RC type/width diff (signedness + byte<->dword), the
    type-width companion to the register-seat diff.  Byte-exact => empty."""
    from c2.regalloc.seat_recon import type_width_diff
    rows, _ = _build_diff_rows(
        orig, orig_off, recomp, recomp_off, orig_fix, recomp_fix, line_map,
    )
    return type_width_diff(rows)


def _spill_recon_for_json(
    orig: bytes, orig_off: int, recomp: bytes, recomp_off: int,
    orig_fix: set[int], recomp_fix: set[int],
    line_map: dict[int, int] | None,
) -> dict:
    """Asm-only PS<->RC stack-frame / spill-slot diff (the frame-shift
    companion to the seat + width diffs).  Byte-exact => no delta."""
    from c2.regalloc.seat_recon import spill_diff
    rows, _ = _build_diff_rows(
        orig, orig_off, recomp, recomp_off, orig_fix, recomp_fix, line_map,
    )
    return spill_diff(rows)


def _recon_bundle_for_json(
    orig: bytes, orig_off: int, recomp: bytes, recomp_off: int,
    orig_fix: set[int], recomp_fix: set[int],
    line_map: dict[int, int] | None, byte_diff: int = 0,
    recomp_line_map: dict[int, int] | None = None,
    recomp_audit: bytes | None = None,
) -> dict:
    """All three asm-only PS<->RC recon diffs + the composite shape distance,
    from ONE row build: {seat_recon, width_recon, spill_recon, shape_distance,
    run_ledger}.  `shape_distance.shape` (seat+width+spill) is the
    byte-independent distance-to-PS; an edit that drops it is PS-faithful
    even if bytes rise.

    The ``ir`` layer comes from the DUAL-MARKS run ledger when the RC line
    map is available (attribution-exact: each side segmented by its OWN
    -d1 marks; see c2.runledger) and falls back to the byte-diff-aligned
    binir per-line comparison otherwise (approximate on drifting diffs)."""
    from c2.regalloc.seat_recon import (
        seat_diff, type_width_diff, spill_diff, shape_distance_from)
    from c2.commands.binir_shape_hints import detect as _binir_detect
    rows, _ = _build_diff_rows(
        orig, orig_off, recomp, recomp_off, orig_fix, recomp_fix, line_map,
    )
    seat = seat_diff(rows)
    width = type_width_diff(rows)
    spill = spill_diff(rows)
    led = _run_ledger_for(orig, orig_off,
                          recomp_audit if recomp_audit is not None else recomp,
                          recomp_off,
                          orig_fix, recomp_fix, line_map, recomp_line_map)
    if led is not None:
        ir_div = led.ps_runs_divergent + led.rc_only_runs
        ir_max = led.ps_runs_total
        ledger_json = led.to_json(with_insns=False)
        n_islands = len(led.islands)
    else:
        bh = _binir_detect(rows)
        ir_div, ir_max = bh.lines_divergent, bh.lines_compared
        ledger_json = None
        n_islands = None
    return {
        "seat_recon": seat, "width_recon": width, "spill_recon": spill,
        "run_ledger": ledger_json,
        "shape_distance": shape_distance_from(
            seat, width, spill, byte_diff, ir_div, ir_max,
            islands=n_islands),
    }


def _diff_to_json_rows(rows: list[dict], hints: list) -> list[dict]:
    """Serialise a row stream to plain-JSON-friendly dicts."""
    out: list[dict] = []
    for row, hint in zip(rows, hints):
        rec: dict = {
            "off":  row["off"],
            "ln":   row["ln"],
            "kind": row["kind"],
        }
        if row["o"] is not None:
            rec["ps"] = {
                "bytes":     " ".join(row["ps_tokens"]),
                "asm":       row["o"][3],
                "diff_pos":  row["ps_diff"],
            }
        if row["r"] is not None:
            rec["rc"] = {
                "bytes":     " ".join(row["rc_tokens"]),
                "asm":       row["r"][3],
                "diff_pos":  row["rc_diff"],
            }
        if hint is not None:
            rec["hint"] = {
                "rule":    hint.rule,
                "summary": hint.summary,
                "fix":     hint.fix,
            }
        out.append(rec)
    return out


def _tail_merge_to_json(hint) -> Optional[dict]:
    """Serialise a ``TailMergeHint`` to a JSON-friendly dict, or None.

    ``donor_status`` (``"diff"`` / ``"exact"`` / ``None``) records
    whether the donor is itself diffing in the cached verify.json --
    consumers (priority-target picker, residue census) use this to
    drop blocked functions from the actionable list automatically.
    """
    if hint is None:
        return None
    return {
        "donor_name":           hint.donor_name,
        "donor_start":          f"0x{hint.donor_start:X}",
        "merge_target":         f"0x{hint.merge_target:X}",
        "merge_offset_in_donor": hint.merge_offset_in_donor,
        "jmp_offset_in_self":   hint.jmp_offset_in_self,
        "tail_bytes":           hint.tail_bytes.hex(),
        "tail_disasm":          list(hint.tail_disasm),
        "donor_status":         _donor_blocking_status(hint.donor_name),
    }


def _pragma_hint_for_json(orig: bytes, recomp: bytes) -> Optional[dict]:
    """Return the prologue-divergence hint for JSON output, if any."""
    try:
        from c2.commands.pragma_hints import detect_pragma_hint, hint_to_json

        hint = detect_pragma_hint(_disasm_for_diff(orig), _disasm_for_diff(recomp))
    except ImportError:
        return None
    if hint is None:
        return None
    return hint_to_json(hint)


def _moved_code_for_json(name: str) -> Optional[dict]:
    """Rule 125 moved-code signature for ``name``, or None.
    See ``c2/commands/moved_code_hints.py``."""
    try:
        from c2.commands.moved_code_hints import detect, to_json

        return to_json(detect(name))
    except (ImportError, FileNotFoundError, KeyError, ValueError):
        return None


def _loops_for_json(name: str) -> Optional[list[dict]]:
    """Loop classifier output for ``name``, or None when no loops are
    detected.  See ``c2/commands/loop_hints.py``."""
    try:
        from dataclasses import asdict

        from c2.commands.disasm import disasm_function
        from c2.commands.loop_hints import detect_loops

        _, _, lines = disasm_function(name)
        detected = detect_loops(lines)
        if not detected:
            return None
        return [asdict(lp) for lp in detected]
    except (ImportError, FileNotFoundError, KeyError, ValueError):
        return None


def _crossbuild_for_json(name: str) -> Optional[dict]:
    """Per-build status record for ``name`` from the persisted
    cross-build map, or None when the map hasn't been generated."""
    try:
        from c2.commands.crossbuild import crossbuild_status

        rec = crossbuild_status(name)
    except (ImportError, ValueError, KeyError):
        return None
    if rec is None:
        return None
    return {
        bid: info.get("status")
        for bid, info in rec.get("builds", {}).items()
    }


def _dispatch_hint_for_json(name: str, orig_bytes: bytes) -> Optional[str]:
    """switch<=>jump-table mismatch hint for ``name``, or None."""
    try:
        from c2.commands.dispatch_hints import detect_dispatch_mismatch
        return detect_dispatch_mismatch(name, _disasm_for_diff(orig_bytes))
    except ImportError:
        return None


def _sibling_hint_for_json(name: str) -> Optional[list[dict]]:
    """Run the fuzzy-asm sibling matcher and return a JSON-friendly
    list of top byte-exact siblings (or None when nothing clears the
    threshold).  See ``c2/commands/sibling.py``.

    Sets sibling's ``_in_verify_hint`` re-entry guard so the status
    refresher doesn't recursively invoke decomp-verify from inside
    decomp-verify.
    """
    try:
        from c2.commands import sibling as _sib

        prev = _sib._in_verify_hint
        _sib._in_verify_hint = True
        try:
            hits = _sib.find_siblings(
                name, top_n=3, min_score=0.30, filter_status={"exact"},
            )
        finally:
            _sib._in_verify_hint = prev
    except (KeyError, FileNotFoundError, ValueError, ImportError):
        return None
    if not hits:
        return None
    return [
        {
            "name":     h.name,
            "score":    h.score,
            "common":   h.common,
            "src_file": h.src_file,
            "insns":    h.n_insns,
        }
        for h in hits
    ]


def _style_hints_for_json(name: str) -> Optional[list[dict]]:
    """Source-level style check (not-observed forms + codegen-noise
    forms).  See ``c2/commands/style_check.py``.  Advisory only."""
    try:
        from c2.commands.style_check import style_hints_to_json

        hits = style_hints_to_json(name)
    except (KeyError, FileNotFoundError, ValueError, ImportError):
        return None
    return hits or None


def _global_cache_hints_for_json(name: str) -> Optional[list[dict]]:
    """Precise "global array element cached in a local pointer" detector.
    See ``c2/commands/global_cache_hints.py``.  Advisory only."""
    try:
        from c2.commands.global_cache_hints import global_cache_hints_to_json

        hits = global_cache_hints_to_json(name)
    except (KeyError, FileNotFoundError, ValueError, ImportError):
        return None
    return hits or None


def _frame_hint_for_json(orig: bytes, recomp: bytes,
                         rows: list[dict]) -> Optional[dict]:
    """Frame-size root-cause hint for ``--json``.
    See ``c2/commands/frame_hints.py``."""
    try:
        from c2.commands.frame_hints import detect, to_json
        hint = detect(_disasm_for_diff(orig), _disasm_for_diff(recomp), rows)
    except Exception:
        return None
    return to_json(hint)


def _const_audit_for_json(orig: bytes, recomp: bytes,
                          orig_off: int, recomp_off: int,
                          orig_fix: set[int], recomp_fix: set[int]
                          ) -> Optional[dict]:
    """Wrong-constant / off-by-one-boundary audit for ``--json``.

    Compares the regalloc-invariant multiset of immediate constants
    between PS and the recompile, with comparison boundaries canonicalised
    (so ``>`` vs ``>=`` spellings don't false-positive).  Returns None when
    clean.  See ``c2/commands/const_audit.py``."""
    try:
        from c2.commands.const_audit import constant_audit
        res = constant_audit(orig, recomp, orig_off, recomp_off,
                             orig_fix, recomp_fix)
    except Exception:
        return None
    if res.get("clean"):
        return None
    # off-by-one boundary flag: a cmp-boundary present on one side that is
    # exactly +/-1 of one on the other -- the `>`/`>=` / `n vs n+-1` class.
    offby1 = False
    ct = res.get("cmp_threshold")
    if ct:
        ps_b, rc_b = set(ct["ps_only"]), set(ct["rc_only"])
        offby1 = any((k + 1 in rc_b or k - 1 in rc_b) for k in ps_b)
    out = {k: v for k, v in res.items() if k in ("cmp_threshold", "eq", "plain")}
    out["n_div"] = res.get("n_div", 0)
    out["boundary_offby1"] = offby1
    out["has_boundary"] = "cmp_threshold" in res
    return out


_RC_O2N_CACHE: dict = {}


def _argswap_for_json(orig: bytes, recomp: bytes,
                      orig_off: int, recomp_off: int,
                      orig_fix: set[int], recomp_fix: set[int],
                      recomp_map: dict) -> Optional[list]:
    """Out-of-order parameter (swapped constant arg) candidates for
    ``--json``.  A constant landing in a different __watcall arg register in
    PS vs RC (same callee, matched by order) is a swapped-argument candidate
    -- caught even when the other swapped arg is a variable, and invisible to
    the value-multiset ``const_audit``.  See ``c2/commands/const_audit.py``."""
    try:
        from c2.commands.const_audit import argswap_audit, _ps_off_to_name
        # rc off->name: invert the link map once (cache keyed by identity).
        key = id(recomp_map)
        rc_o2n = _RC_O2N_CACHE.get(key)
        if rc_o2n is None:
            rc_o2n = {off: nm.rstrip("_") for nm, off in recomp_map.items()}
            _RC_O2N_CACHE.clear()
            _RC_O2N_CACHE[key] = rc_o2n
        res = argswap_audit(orig, recomp, orig_off, recomp_off,
                            orig_fix, recomp_fix, _ps_off_to_name(), rc_o2n)
    except Exception:
        return None
    return res or None


def _sched_hint_for_json(name: str, orig: bytes, recomp: bytes,
                         rows: list[dict]) -> Optional[dict]:
    """Eval-order scheduling-swap hint for ``--json``.
    See ``c2/commands/sched_hints.py``."""
    try:
        from c2.commands.sched_hints import detect, to_json
        hint = detect(name, _disasm_for_diff(orig), _disasm_for_diff(recomp), rows)
    except Exception:
        return None
    return to_json(hint)


def _binir_shape_hint_for_json(rows: list[dict]) -> Optional[dict]:
    """Per-source-line binir-IR-shape comparison between PS and our compile.

    Distinguishes ``encoding_noise`` (every line's binir shape matches ->
    byte diff is pure regalloc tie-break / Jcc encoding, NOT a semantic
    perturbation) from ``shape_divergence`` (lines where the recovered
    IR shapes differ -> ACTIONABLE source-perturbation targets).

    See ``c2/commands/binir_shape_hints.py``.
    """
    try:
        from c2.commands.binir_shape_hints import detect, to_json
        hint = detect(rows)
    except Exception:
        return None
    return to_json(hint)


def _reload_hint_for_json(name: str, orig_insns) -> Optional[list[dict]]:
    """Reload-vs-hold named-intermediate marker (Rule 116).  Advisory.
    See ``c2/commands/reload_hints.py``."""
    try:
        from c2.commands.reload_hints import detect_reload_hints, to_json

        hints = detect_reload_hints(name, orig_insns, has_body_diff=True)
    except (KeyError, FileNotFoundError, ValueError, ImportError):
        return None
    return to_json(hints)


def _byte_pump_hint_for_json(name: str) -> Optional[dict]:
    """Rule 119 byte-pump workhorse rotation candidate.  See
    ``c2/commands/byte_pump_hints.py`` and ``docs/watcom-codegen-patterns.md``
    Rule 119 for the OW v1 CountRegMoves mechanism.  Advisory only."""
    try:
        from c2.commands.byte_pump_hints import detect as _bp_detect, to_json as _bp_json
    except ImportError:
        return None
    bph = _bp_detect(name)
    return _bp_json(bph) if bph is not None else None


def _slot_swap_for_json(name: str, orig_bytes: bytes, recomp_bytes: bytes,
                        json_rows) -> Optional[dict]:
    """Same-size spill-slot SWAP verdict (Rule 107), annotated with the
    SetTempLocation (`st`) trace so the swapped temps are NAMED.  Lets
    worklist route slot-swap functions out of DIAGNOSE.  See
    ``c2/commands/slot_swap_hints.py``."""
    try:
        from c2.commands import slot_swap_hints as _ss
        h = _ss.detect(_disasm_for_diff(orig_bytes),
                       _disasm_for_diff(recomp_bytes), json_rows)
        if h is None:
            return None
        _ss.annotate(h, name.rstrip("_"), None)
        return _ss.to_json(h)
    except Exception:
        return None


def _loop_rotation_for_json(orig_bytes: bytes, recomp_bytes: bytes) -> Optional[dict]:
    """Rule 134 loop-rotation lever: PS emits a rotated `for(;cond;cnt++)`
    loop (a `loop_rotation_entry` jmp) where RC's `while` form is head-tested.
    An asymmetric PS-only count means rewriting the `while` as the for-clause
    form reproduces PS's block layout.  Recovered from binir markers; a
    SEPARATE lever from any regalloc residue, so it must surface even when a
    slot-swap / reg-swap also fires on the same function."""
    try:
        from c2 import binir
        ps = binir.recover(_disasm_for_diff(orig_bytes))
        rc = binir.recover(_disasm_for_diff(recomp_bytes))
        ps_n = sum(1 for o in ps if getattr(o, "kind", None) == "loop_rotation_entry")
        rc_n = sum(1 for o in rc if getattr(o, "kind", None) == "loop_rotation_entry")
    except Exception:
        return None
    if ps_n > rc_n:
        return {"rule": "134", "ps_only": ps_n - rc_n,
                "lever": "rewrite the while-loop as `for ( ; cond; cnt++)` "
                         "(empty init clause + separate inc)"}
    return None


def _byte_seat_for_json(name: str, json_hints, orig_bytes: bytes) -> Optional[dict]:
    """Byte-seat verdict (CASE A/B/C/D) for any function with a ``Byte-reg
    swap`` row -- the per-function byte-register-seat classification + lever.
    Lets corpus tools (residue-cluster, negative-corpus, ``c2 sibling
    --survey``) route the byte-reg-swap family by verdict instead of treating
    every byte swap as opaque noise.  See ``c2/commands/byte_seat_hints.py``
    and watcom10.0a repo docs/wcc386-re/regalloc-model.md §"Byte-register seating"."""
    try:
        from c2.commands import byte_seat_hints
        v = byte_seat_hints.detect(
            name.rstrip("_"), json_hints,
            ps_insns=_disasm_for_diff(orig_bytes))
    except Exception:
        return None
    if v is None:
        return None
    out = {"case": v.case, "confidence": v.confidence,
           "summary": v.lines[0] if v.lines else None}
    if getattr(v, "savings_pair", None) is not None:
        out["savings_pair"] = v.savings_pair
    return out


def _decl_order_hint_for_json(
    name: str,
    orig_bytes: bytes, recomp_bytes: bytes,
    json_rows: list[dict], json_hints: list,
    rule_hist: dict,
) -> Optional[dict]:
    """Rule 115 declaration-order regalloc-lever candidate.  See
    ``c2/commands/decl_order_hints.py`` and the layer-3 description in
    ``watcom10.0a repo docs/wcc386-re/regalloc-model.md`` §3.  Advisory only.

    Fires only when the regalloc-explain layer is 3 (caller-saved
    register-identity swap, no prologue change) AND the function source
    declares ≥2 named int-class locals at top scope (the candidate pair).
    """
    try:
        from c2.commands.regalloc_explain import explain as _rae
        from c2.commands.decl_order_hints import detect as _doh, to_json as _doh_json
    except ImportError:
        return None
    orig_insns   = _disasm_for_diff(orig_bytes)
    recomp_insns = _disasm_for_diff(recomp_bytes)
    rae = _rae(orig_insns, recomp_insns, rule_hist=rule_hist,
               has_body_diff=True)
    if rae is None or rae.layer != 3:
        return None
    # Convert in-process rows + RuleHint list to the dict shape the detector
    # consumes (matches the on-disk verify.json row schema).
    dict_rows = _diff_to_json_rows(json_rows, json_hints)
    hint = _doh(name, regalloc_layer=rae.layer, diff_rows=dict_rows)
    return _doh_json(hint) if hint is not None else None


# ── Main command ───────────────────────────────────────────────────────────────

def _format_shape_cols(sd: dict) -> str:
    """Format shape distance as fixed-width columns for vertical alignment.

    Layout: ``ir  N/T   isl  K   width  N/T   spill N/T   seat  N/T``.
    Each layer pads its value to a consistent width so columns line up
    across rows.  Missing totals render as just ``ir N`` (no slash).
    ``isl`` is the run-ledger island count (the ir layer's fine-grained
    unit; 0 = regalloc_pure, ``-`` = ledger unavailable).
    """
    def _cell(name: str, name_w: int) -> str:
        n = sd.get(name, 0)
        t = sd.get(name + "_total", 0)
        if t:
            val = f"{n:>2}/{t:<3}"      # e.g. " 2/14 "  /  "31/78 "
        else:
            val = f"{n:>2}    "         # e.g. " 0    " -- 6 chars to match " 2/14 " width
        return f"{name:<{name_w}} {val}"
    isl = sd.get("islands")
    isl_cell = f"isl {isl if isl is not None else '-':>3}"
    return (f"{_cell('ir',    2)}  "
            f"{isl_cell}  "
            f"{_cell('width', 5)}  "
            f"{_cell('spill', 5)}  "
            f"{_cell('seat',  4)}")


def decomp_verify(
    c_files: Annotated[
        Optional[list[Path]],
        typer.Argument(
            help="C file(s) to show results for (default: all with FUNCTION annotations)",
        ),
    ] = None,
    symbols_json: Annotated[
        Path,
        typer.Option("--symbols", "-s", help="Path to symbols.json"),
    ] = Path("data/out/symbols.json"),
    exe_path: Annotated[
        Path,
        typer.Option("--exe", help="Path to original PS.EXE"),
    ] = Path("data/PS.EXE"),
    decomp_dir: Annotated[
        Path,
        typer.Option("--decomp", "-d", help="Decomp source directory"),
    ] = Path("decomp"),
    image: Annotated[
        str,
        typer.Option(
            "--image", "-i",
            help=f"Podman image for Watcom 10.0a (default: {_DEFAULT_IMAGE})",
        ),
    ] = _DEFAULT_IMAGE,
    cflags: Annotated[
        str,
        typer.Option("--cflags", help="Compiler flags"),
    ] = PS_CFLAGS,
    # See PS_CFLAGS above for the full, fingerprint-backed rationale for every
    # token.  Override only for deliberate codegen experiments.
    function: Annotated[
        Optional[list[str]],
        typer.Option(
            "--function", "-f",
            help="Only show these function(s) (can repeat: -f foo -f bar)",
        ),
    ] = None,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v",
                     help="Show annotated diff disassembly for each diff "
                          "(side-by-side PS │ RC by default; see --compact / --full)"),
    ] = False,
    full: Annotated[
        bool,
        typer.Option("--full",
                     help="Use the legacy 3-line-per-diff verbose format "
                          "(takes ~3x more vertical space).  Default is "
                          "the side-by-side PS │ RC renderer."),
    ] = False,
    compact: Annotated[
        bool,
        typer.Option(
            "--compact",
            help="Use the compact unified one-line-per-row renderer "
                 "instead of the default side-by-side PS │ RC view.",
        ),
    ] = False,
    full_hints: Annotated[
        bool,
        typer.Option(
            "--full-hints",
            help="Print the full -v diagnostics: the per-source-line regalloc "
                 "table, the raw binary-IR signature dicts, and the COMPLETE "
                 "instruction-by-instruction disasm (no windowing).  Default "
                 "-v shows a focused, windowed view; this restores everything "
                 "(also via C2_FULL_HINTS=1).",
        ),
    ] = False,
    mac_decompile: Annotated[
        Optional[bool],
        typer.Option(
            "--mac-decompile/--no-mac-decompile",
            help="After each diffing function, also print the AST-cleaned Mac "
                 "PPC Ghidra decompile (source-shape oracle).  Auto-builds "
                 "the Mac Ghidra DB on first use (~25s).  Default: OFF (a "
                 "one-line `mac:` pointer to `c2 mac-decompile <fn>` is "
                 "always shown for diffing functions); pass --mac-decompile "
                 "to inline the full block.",
        ),
    ] = None,
    win_decompile: Annotated[
        Optional[bool],
        typer.Option(
            "--win-decompile/--no-win-decompile",
            help="After each diffing function, also print the Windows MSVC /Od "
                 "Ghidra decompile (CAESAR2.EXE: x86 source-shape oracle, the "
                 "most legible reading -- named+typed params, named globals, "
                 "every statement explicit).  Auto-builds the Win Ghidra DB on "
                 "first use (~60s).  Default: OFF (a one-line `win:` pointer "
                 "to `c2 win-decompile <fn>` is always shown for diffing "
                 "functions); pass --win-decompile to inline the full block.",
        ),
    ] = None,
    json_out: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Emit per-function diff records as a single JSON document on "
                 "stdout (suppresses textual rendering; implies --verbose).",
        ),
    ] = False,
    json_summary: Annotated[
        bool,
        typer.Option(
            "--json-summary",
            help="Emit only summary/file JSON metrics (fast; skips per-function "
                 "rows, hints, and style probes).",
        ),
    ] = False,
    shape_divergence: Annotated[
        bool,
        typer.Option(
            "--shape-divergence",
            help="Whole-surface SHAPE map instead of per-function byte diffs: "
                 "rank every decompiled function by PS-vs-RC -d1 line-mark "
                 "divergence (recovered source over-split / over-merged vs "
                 "PS's statement structure).  Cheap (cached RC build + "
                 "symbols, no Mac).  `--shape-divergence-scope diff|exact|all`.",
        ),
    ] = False,
    shape_divergence_scope: Annotated[
        str,
        typer.Option(
            "--shape-divergence-scope",
            help="Scope for --shape-divergence: all | diff | exact.",
        ),
    ] = "all",
    abs_lines: Annotated[
        bool,
        typer.Option(
            "--abs-lines/--rel-lines",
            help="Side-by-side view line numbers: absolute per side "
                 "(PS = original debug-info line, RC = decomp .c line; "
                 "greppable in the sources) instead of the default "
                 "function-relative L+N (directly comparable across sides).",
        ),
    ] = False,
    keep: Annotated[
        bool,
        typer.Option("--keep", help="Keep temporary build directory for inspection"),
    ] = False,
    strict: Annotated[
        bool,
        typer.Option(
            "--strict/--no-strict",
            help="Build the runnable PS.EXE and exit non-zero on any "
                 "function or final-link code/data/layout/fixup mismatch. "
                 "--no-strict retains the fast function-only verifier "
                 "without the final rebuild (default: strict).",
        ),
    ] = True,
    strict_warnings: Annotated[
        bool,
        typer.Option(
            "--strict-warnings/--no-strict-warnings", "-W",
            help="Exit non-zero if the Watcom build emits any warning or "
                 "error (after the well-known math387 / stack-segment / "
                 "starting-address noise filter). Default: on.",
        ),
    ] = True,
    no_cache: Annotated[
        bool,
        typer.Option(
            "--no-cache",
            help="Build in a fresh tempdir (no .c2-cache/build reuse). "
                 "Use when you suspect cache staleness.",
        ),
    ] = False,
    target: Annotated[
        str,
        typer.Option(
            "--target", "-T",
            help="Byte oracle to compare against: 'watcom' (default; DOS "
                 "PS.EXE via Watcom 10.0a) or 'win' (Windows CAESAR2.EXE via "
                 "MSVC 4.0 /Od).  --target win dispatches into the win-verify "
                 "engine + .c2-cache/win-verify.json and renders the same "
                 "summary/per-function diff view; it has NO shape/regalloc "
                 "layers (/Od does no register allocation) -- see "
                 "docs/windows-dual-target-feasibility.md.",
        ),
    ] = "watcom",
    timings: Annotated[
        bool,
        typer.Option(
            "--timings",
            help="Print per-phase wall-clock timings to stderr.",
        ),
    ] = False,
) -> None:
    """Verify decompiled C functions match original binary.

    Compiles ALL .c files in decomp/src/ together into a single LE
    executable with a unified stubs file, then compares each FUNCTION-
    annotated function's bytes against PS.EXE.

    \\b
    Output filtering:
      c2 decomp-verify                         — show all functions
      c2 decomp-verify decomp/src/common.c     — show only common.c functions
      c2 decomp-verify -f create_unit           — show only create_unit
      c2 decomp-verify decomp/src/common.c -f create_unit  — both filters

    \\b
    Annotations recognised in source files:
      // FUNCTION: C2 0xADDR   — decompiled, will be compared
      // STUB: C2 0xADDR       — not yet decompiled, skipped
    """
    # Side-by-side line-number mode (see _ABS_LINES).
    global _ABS_LINES
    _ABS_LINES = abs_lines
    if json_summary:
        json_out = True

    # Whole-surface SHAPE map: rank every decompiled function by PS-vs-RC
    # -d1 line-mark divergence (recovered statement decomposition vs PS's),
    # INSTEAD of the per-function byte-diff positions -- which are
    # meaningless at corpus scale.  Cheap: the cached RC build + symbols,
    # no Mac.  shape-recon owns the engine; this is just the host.
    if shape_divergence:
        from c2.commands.shape_recon import shape_divergence_report
        shape_divergence_report(symbols_json, scope=shape_divergence_scope,
                                json_out=json_out)
        return

    # ── Windows (CAESAR2.EXE / MSVC /Od) target ────────────────────────────
    # Thin dispatch into the win-verify engine + .c2-cache/win-verify.json;
    # renders the same summary/per-function-diff view as the Watcom path but
    # has NO shape/regalloc layers (/Od does no register allocation -- see
    # docs/windows-dual-target-feasibility.md).  Maps the decomp-verify
    # options onto win-verify's: --function/-f -> single-fn view,
    # a positional .c path -> TU --file, --json/--verbose/--no-cache pass
    # through.  Doesn't touch the Watcom build/stub/hint machinery below.
    if target == "win":
        from c2.commands.win_verify import run as _run_win
        fn_list = list(function) if function else None
        file_arg = None
        if c_files:
            # a .c path argument scopes to that TU (win's --file).
            for p in c_files:
                if str(p).endswith(".c"):
                    file_arg = Path(p).stem
                    break
        # decomp-verify allows multiple -f; win-verify takes one at a time.
        if fn_list:
            if json_out and len(fn_list) > 1:
                import json as _json
                from c2 import win_verify_cache as _wvc
                rows = [_wvc.func_row_or_verify(n) for n in fn_list]
                typer.echo(_json.dumps({"functions": rows}, indent=1))
                return
            for fn in fn_list:
                _run_win(function=fn, file=file_arg, verbose=verbose,
                         diffing=False, json_out=json_out,
                         no_cache=no_cache)
        else:
            _run_win(function=None, file=file_arg, verbose=verbose,
                     diffing=False, json_out=json_out, no_cache=no_cache)
        return
    if target != "watcom":
        typer.echo(f"Error: unknown --target {target!r} "
                   f"(use 'watcom' or 'win')", err=True)
        raise typer.Exit(2)

    # Self-heal: drop any orphaned warm containers from a previously-killed run
    # (their stuck dosemu2 instances otherwise starve the CPU -> hung compiles).
    reap_orphan_warm_containers()
    if not symbols_json.exists():
        typer.echo(f"Error: {symbols_json} not found", err=True)
        raise typer.Exit(1)
    if not exe_path.exists():
        typer.echo(f"Error: {exe_path} not found", err=True)
        raise typer.Exit(1)

    src_dir = decomp_dir / "src"
    include_dir = decomp_dir / "include"

    # In JSON mode, route all human-facing chatter to stderr so stdout
    # stays a single parseable JSON document.  All progress/status
    # `typer.echo` calls below funnel through `_status` to honour this.
    def _status(msg: str = "") -> None:
        typer.echo(msg, err=json_out)

    # Top-level phase timer (toggle with --timings).
    import time
    _t_phase = time.perf_counter()
    def _tick(label: str) -> None:
        nonlocal _t_phase
        if timings:
            typer.echo(
                f"⏱  {label:<30} {time.perf_counter()-_t_phase:5.2f}s",
                err=True,
            )
        _t_phase = time.perf_counter()

    json_funcs: list[dict] = []

    # ── Load PS.EXE ──────────────────────────────────────────────────────
    _status("Loading PS.EXE …")
    orig_code, orig_fix = _load_le_code_and_fixups(exe_path)
    _tick("load PS.EXE + fixups")

    # ── Symbol table ─────────────────────────────────────────────────────
    sym_data   = json.loads(symbols_json.read_text())
    code_syms  = sorted(
        [s for s in sym_data["symbols"] if s["is_code"]],
        key=lambda s: s["offset"],
    )
    seen_offsets: set[int] = set()
    deduped: list[dict] = []
    for s in code_syms:
        if s["offset"] not in seen_offsets:
            seen_offsets.add(s["offset"])
            deduped.append(s)
    vsize = sym_data["memory_map"]["objects"][0]["virtual_size"]
    for i, s in enumerate(deduped):
        s["_end"] = deduped[i + 1]["offset"] if i + 1 < len(deduped) else vsize

    addr_to_loc: dict[int, tuple[int, int]] = {
        s["address"]: (s["offset"], s["_end"] - s["offset"])
        for s in deduped
    }
    # offset -> address (to name the NEXT symbol after a function's extent;
    # used by the cross-module trailing scan-table classifier).
    off_to_addr: dict[int, int] = {s["offset"]: s["address"] for s in deduped}
    # Keep ALL aliases (multiple symbols may share an address — e.g.
    # `gloop_end` / `mloop_end` both at 0x3D9DF).
    name_to_addr: dict[str, int] = {}
    for s in code_syms:
        name_to_addr.setdefault(s["raw_name"], s["address"])
        name_to_addr.setdefault(s["name"], s["address"])
    addr_to_name: dict[int, str] = {
        s["address"]: s["raw_name"]
        for s in deduped
    }
    # All aliases at each address (for recompile-map lookup that
    # may use any of the aliased symbols).
    addr_to_aliases: dict[int, list[str]] = {}
    for s in code_syms:
        addr_to_aliases.setdefault(s["address"], []).append(s["raw_name"])
    line_map: dict[int, int] = {
        ln["offset"]: ln["line"]
        for ln in sym_data["line_numbers"]
    }

    _tick("parse symbols.json")

    # ── Collect per-file annotations ─────────────────────────────────────
    all_c_files = sorted(src_dir.glob("*.c"))
    if not all_c_files:
        typer.echo("No .c files found in decomp/src/.")
        return

    # Map: source_file → (func_addrs, stub_addrs)
    file_annotations: dict[Path, tuple[set[int], set[int]]] = {}
    for cf in all_c_files:
        fa, sa = _parse_annotations(cf)
        if fa or sa:
            file_annotations[cf] = (fa, sa)
    _tick(f"parse {len(all_c_files)} .c annotations")

    # ── Collect per-asm annotations ────────────────────────────────
    # The 8 hand-written C2 .asm modules each have a fixed set of
    # PUBLIC functions — we treat every public as a comparison target.
    # No STUB concept here: asm functions are either present (and
    # therefore checked) or absent (the file isn't there at all).
    _C2_ASM_NAMES = {
        "library.asm", "sprites.asm", "dia_ptrs.asm",
        "dialarga.asm", "dialargb.asm", "dia_medi.asm", "dia_smal.asm",
        "palet.asm",
    }
    all_asm_files = sorted(
        f for f in src_dir.glob("*.asm") if f.name in _C2_ASM_NAMES
    )
    for af in all_asm_files:
        publics, _ed, _ep = _parse_asm_decls(af)
        asm_func_addrs: set[int] = set()
        for raw in publics:
            addr = name_to_addr.get(raw)
            if addr is None and raw.startswith("_"):
                addr = name_to_addr.get(raw[1:])
            if addr is not None:
                asm_func_addrs.add(addr)
        if asm_func_addrs:
            file_annotations[af] = (asm_func_addrs, set())
    _tick(f"parse {len(all_asm_files)} .asm declarations")

    total_funcs = sum(len(fa) for fa, _ in file_annotations.values())
    total_stubs = sum(len(sa) for _, sa in file_annotations.values())
    if total_funcs == 0:
        typer.echo(f"No FUNCTION annotations found ({total_stubs} stubs).")
        return

    # ── Build filter sets ────────────────────────────────────────────────
    # Determine which files to show results for
    if c_files:
        # Resolve user-provided paths to absolute for comparison
        show_files: set[Path] = set()
        for p in c_files:
            show_files.add(p.resolve())
    else:
        show_files = None  # show all

    # Determine which functions to show
    show_func_addrs: set[int] | None = None
    if function:
        show_func_addrs = set()
        for fname in function:
            mangled = fname if fname.endswith("_") else fname + "_"
            addr = name_to_addr.get(mangled) or name_to_addr.get(fname)
            if addr:
                show_func_addrs.add(addr)
            else:
                _status(f"  Warning: function '{fname}' not found in symbols")

    # Resolve --mac-decompile / --win-decompile defaults: OFF.  The inline
    # Ghidra blocks are noisy and spin up the JVM, so they are opt-in even
    # under -v/--verbose.  Diffing functions still get the one-line `mac:` /
    # `win:` pointers (_mac_hint / _win_hint) to `c2 mac-decompile <fn>` /
    # `c2 win-decompile <fn>` for on-demand pulls.  Explicit
    # --mac-decompile / --no-mac-decompile (and --win-decompile / --no-)
    # overrides.
    if mac_decompile is None:
        mac_decompile = False
    if win_decompile is None:
        win_decompile = False

    # --full-hints (or C2_FULL_HINTS=1) un-suppresses the heavy -v blocks
    # (regalloc per-line table, raw IR dicts, full un-windowed disasm).
    # Threaded via a module global so the many header/render helpers don't
    # each need an extra parameter.
    global _DIAG_FULL
    _DIAG_FULL = bool(full_hints) or bool(os.environ.get("C2_FULL_HINTS"))

    # ── Build ────────────────────────────────────────────────────────────
    _status(
        f"Building {len(all_c_files)} source files "
        f"({total_funcs} functions, {total_stubs} stubs) …"
    )

    ok, build_output, work, out_exe, out_map = _build_all(
        src_dir, include_dir, image, cflags,
        use_cache=not no_cache, timings=timings,
    )
    _tick("_build_all (total)")

    if not ok:
        _status("Build failed:\n")
        for ln in build_output.splitlines():
            _status(f"  {ln}")
        if keep:
            _status(f"\n  (build dir kept: {work})")
        else:
            _cleanup_work(work)
        raise typer.Exit(1)

    # Show build output lines that contain actual warnings/errors.
    # Track them too so --strict-warnings can fail at the end.
    #
    # wcc386 emits:           foo.c(123): Warning! W106: ...
    # wlink emits:            Warning(1027): file clib3r.lib(tzset): ...
    # wcc386 errors:          foo.c(123): Error! E1071: ...
    # wlink errors:           Error! E2008: ...
    #
    # Match both styles ("warning!" and "warning(", "error!" and
    # "error("), then suppress the well-known noise sources.
    #
    # Cached builds: wmake skips re-compiling unchanged .c, so wcc386
    # doesn't re-emit messages to stdout.  Fall back to the per-source
    # ``.err`` files left behind by previous compiles — they contain
    # the same one-line-per-issue format.
    def _is_noise(line: str) -> bool:
        low = line.lower()
        if any(s in low for s in (
            'math387', 'stack segment', 'starting address',
        )):
            return True
        # Benign clib3r.lib redefinitions: datainit.c intentionally defines
        # `_nullarea` (the program's string-literal pool) which collides with
        # the CRT startup module's own `__nullarea`; the linker keeps ours
        # ("redefinition ... ignored") which is what we want.  Scope the
        # suppression to clib3r.lib so genuine redefinitions still surface.
        # (The former tzset collisions — timezone/daylight/tzname — were
        # removed at the source; we no longer define those CRT globals.)
        if 'redefinition' in low and 'clib3r.lib' in low:
            return True
        return False

    def _classify(line: str) -> tuple[bool, bool]:
        low = line.lower()
        is_err  = ('error!' in low) or ('error(' in low)
        is_warn = (('warning!' in low or 'warning(' in low)
                   and not _is_noise(low))
        return is_err, is_warn

    n_build_warnings = 0
    n_build_errors   = 0
    # We can't dedupe identical lines (two calls on the same source line
    # legitimately produce two identical warnings).  Instead: skip the
    # .err fallback entirely if stdout already had any compiler/linker
    # diagnostics — i.e. wmake actually did something.
    stdout_had_diag = False
    for ln in build_output.splitlines():
        is_err, is_warn = _classify(ln)
        if is_err or is_warn:
            stdout_had_diag = True
            _status(f"  {ln}")
            if is_err:
                n_build_errors += 1
            elif is_warn:
                n_build_warnings += 1

    # Fallback: scan per-.err files (cached run path where wmake
    # skipped every compile and stdout has only the banner).
    if not stdout_had_diag:
        for err_file in sorted(work.glob("*.err")):
            for ln in err_file.read_text(errors="replace").splitlines():
                is_err, is_warn = _classify(ln)
                if is_err or is_warn:
                    _status(f"  {ln}")
                    if is_err:
                        n_build_errors += 1
                    elif is_warn:
                        n_build_warnings += 1

    if keep:
        _status(f"  (build dir: {work})")

    # ── Parse recompiled binary ──────────────────────────────────────────
    # out_exe/out_map are the under-lock SNAPSHOT paths from _build_all
    # (immune to a concurrent session relinking the shared cache dir).
    if not out_exe.exists() or not out_map.exists():
        _status("Linker produced no output.")
        if not keep:
            _cleanup_work(work)
        raise typer.Exit(1)

    recomp_code, recomp_fix = _load_le_code_and_fixups(out_exe)
    recomp_map = _parse_map(out_map)
    # Sorted unique offsets of every named code symbol in the recompile,
    # used to compute the *RC* function end (= next named symbol after the
    # function's own offset).  Without this, slicing RC bytes by the PS
    # function size overruns into the NEXT RC function when RC < PS, and
    # downstream analyses (const-audit / arg-swap) report constants from
    # neighbour code as divergent.  Worked example: `build_city_item`
    # (PS 0xCB3b / RC 0xC39b) surfaced phantom `cmp edi, 0x1e/0x1f ; jne`
    # equality literals that physically live in `prebuild_region_item`.
    _rc_sorted_offs: list[int] = sorted(set(recomp_map.values()))

    def _rc_func_size(rc_off: int, ps_func_size: int) -> int:
        """Return the byte length to slice from the RC code section for a
        function starting at ``rc_off``: ``next_named_symbol - rc_off``,
        clamped to the PS size as an upper bound (the analyses never need
        more than the PS size's worth of context).  Falls back to the PS
        size when there is no next symbol."""
        import bisect
        j = bisect.bisect_right(_rc_sorted_offs, rc_off)
        nxt = (_rc_sorted_offs[j] if j < len(_rc_sorted_offs)
               else len(recomp_code))
        return min(ps_func_size, nxt - rc_off)
    # ── Branch-target audit resolvers (see _branch_target_audit) ─────
    # PS side: every code symbol (game + CRT + AIL) sorted by offset.
    import bisect as _bt_bisect
    _bt_ps_starts = [s["offset"] for s in deduped]

    def _bt_ps_resolve(t: int):
        i = _bt_bisect.bisect_right(_bt_ps_starts, t) - 1
        if i < 0 or t >= vsize:
            return None
        s = deduped[i]
        names = frozenset(
            n.rstrip("_")
            for n in addr_to_aliases.get(s["address"], [s["raw_name"]]))
        return names, t - s["offset"]

    # RC side: every code-segment symbol in the testbench linker map
    # (aliases at one offset grouped).
    _bt_rc_by_off: dict[int, set[str]] = {}
    for _nm, _off in recomp_map.items():
        _bt_rc_by_off.setdefault(_off, set()).add(_nm.rstrip("_"))
    _bt_rc_starts = sorted(_bt_rc_by_off)

    def _bt_rc_resolve(t: int):
        i = _bt_bisect.bisect_right(_bt_rc_starts, t) - 1
        if i < 0 or t >= len(recomp_code):
            return None
        base = _bt_rc_starts[i]
        return frozenset(_bt_rc_by_off[base]), t - base

    # RC function vaddr ranges (start, end, name), inferred from the linker
    # map.  Lets the side-by-side renderer splice the RC side's tail-merged
    # epilogue back in (the donor lives in another function's byte range,
    # so it is invisible to a naive slice of the function's own bytes).
    try:
        _rc_items = sorted(recomp_map.items(), key=lambda kv: kv[1])
        recomp_ranges = [
            (off + 0x10000,
             (_rc_items[i + 1][1] if i + 1 < len(_rc_items) else off + 256)
             + 0x10000,
             nm.rstrip("_"))   # match PS display names (linker map keeps the _)
            for i, (nm, off) in enumerate(_rc_items)
        ]
    except Exception:
        recomp_ranges = None
    # Per-instruction source-line lookup for the recompile, used by the
    # side-by-side renderer.  Requires -d1 in cflags; silently empty
    # otherwise.  -d1 is byte-neutral on PS-matching codegen (verified;
    # see AGENTS.md § Optimization Sub-Flags) so we don't force-enable
    # it -- callers who want RC line numbers should pass --cflags with
    # -d1 (or add it to the default).
    try:
        from c2.commands.oracle import _load_oracle_line_lookup
        recomp_line_map = _load_oracle_line_lookup(out_exe)
    except Exception:
        recomp_line_map = {}
    _tick("load recompiled exe + map")

    # Run the strict final link before rendering the TU/function rows so its
    # relocation-target defects can be attributed to the containing source
    # function.  Defer the rebuild's verbose report until after those rows:
    # the normal TU listing remains the first actionable view.
    final_link_report = None
    final_link_failures: list[str] = []
    final_link_output = ""
    final_link_relocations: dict[int, list[dict]] = {}
    if strict:
        _status("Building final runnable PS.EXE for strict verification …")
        from c2.commands.rebuild import rebuild as _rebuild

        captured = io.StringIO()
        try:
            with contextlib.redirect_stdout(captured):
                final_link_report = _rebuild(
                    output=Path("build/PS.EXE"),
                    image=image,
                    bind=True,
                    verify_delink=True,
                    symbols_json=symbols_json,
                    exe_path=exe_path,
                    src_dir=src_dir,
                    include_dir=include_dir,
                    compare=True,
                    compare_verbose=verbose,
                    cflags=cflags,
                )
        except BaseException:
            for line in captured.getvalue().splitlines():
                _status(line)
            raise
        finally:
            final_link_output = captured.getvalue()
        final_link_failures = _final_link_failure_reasons(final_link_report)
        final_link_relocations = _final_link_relocations_by_address(
            final_link_report, deduped)
        _tick("strict final-link rebuild")

    # Cross-corpus line-code index: rebuilt automatically on every FULL pass
    # (no file / -f filter) that carries the RC -d1 line table, so the cache
    # always tracks the current byte-exact corpus.  A partial/filtered pass
    # would yield an incomplete index, so it leaves the existing cache intact.
    # The line-corpus index + exact-line sidecar are refreshed on EVERY pass
    # that carries the RC -d1 line table.  A full pass rewrites them; a
    # partial (-f / per-file) pass MERGES the visited functions into the
    # existing files (preserving every other function) so a single-function
    # verify never leaves the sidecar stale (which used to mislead
    # `c2 line-compare`).  ``_partial_pass`` selects merge vs. overwrite;
    # ``_processed_funcs`` is the set of functions visited this pass.
    _partial_pass = show_files is not None or show_func_addrs is not None
    _processed_funcs: set[str] = set()
    corpus_builder = None
    if recomp_line_map:
        from c2.commands.line_corpus import CorpusBuilder, extract_line_runs
        corpus_builder = CorpusBuilder()
        exact_line_sidecar: dict[str, dict] = {}

    # ── Compare functions ────────────────────────────────────────────────
    n_exact = 0
    n_pad = 0      # subset of n_exact: code-exact, trailing-pad diff (~)
    n_xmod = 0     # subset of n_exact: code-exact, extent over-reaches into
                   #   the NEXT module's leading table (verified at RC site);
                   #   the bytes do NOT differ -- pure symbol-extent artifact
    n_donor_flip = 0  # subset of n_exact: body-exact, donor-coupling diff (~)
    n_rule4 = 0   # subset of n_exact: semantics-exact, Rule 4 cmp-swap (~)
    n_diff  = 0
    n_miss  = 0
    n_stub  = 0
    total   = 0

    # Per-file roll-up; emitted under "files" in the JSON summary so
    # `progress --verify` can read everything in one subprocess call.
    files_summary: dict[str, dict[str, int]] = {}

    def _file_bucket(rel_path: str) -> dict[str, int]:
        return files_summary.setdefault(rel_path, {
            "exact": 0, "diff": 0, "byte_diff": 0,
            "relocation_target_mismatches": 0,
            "not_found": 0, "stub_skipped": 0, "compared": 0,
            "exact_func_bytes": 0,
            "diff_func_bytes": 0,
            "compared_func_bytes": 0,
        })

    for cf in sorted(file_annotations.keys()):
        func_addrs, stub_addrs = file_annotations[cf]
        rel = cf.relative_to(Path.cwd()) if cf.is_relative_to(Path.cwd()) else cf
        bucket = _file_bucket(str(rel))
        bucket["stub_skipped"] += len(stub_addrs)

        # Apply file filter
        if show_files is not None and cf.resolve() not in show_files:
            # Still count stubs/funcs but don't display
            n_stub += len(stub_addrs)
            for addr in func_addrs:
                if show_func_addrs is not None and addr not in show_func_addrs:
                    continue
                # Not in shown files and not specifically requested by -f
                pass
            continue

        # Determine which functions to show from this file
        file_func_addrs = func_addrs
        if show_func_addrs is not None:
            file_func_addrs = func_addrs & show_func_addrs

        n_stub += len(stub_addrs)

        if not file_func_addrs:
            continue

        if not json_out:
            typer.echo(f"\n{'─' * 60}")
            typer.echo(f"  {rel}")
            typer.echo(
                f"  Comparing {len(file_func_addrs)} function(s)"
                + (f", {len(stub_addrs)} stubs skipped" if stub_addrs else "")
                + " …"
            )

        for addr in sorted(file_func_addrs):
            loc = addr_to_loc.get(addr)
            if not loc:
                _status(f"  ?  0x{addr:X}  (not in symbols.json)")
                n_miss += 1
                total += 1
                bucket["not_found"] += 1
                bucket["compared"] += 1
                continue

            orig_off, func_size = loc
            raw_name = addr_to_name.get(addr)
            if not raw_name:
                _status(f"  ?  0x{addr:X}  (no raw_name)")
                n_miss += 1
                total += 1
                bucket["not_found"] += 1
                bucket["compared"] += 1
                continue

            # Try all aliases for this address (e.g. gloop_end / mloop_end).
            recomp_off = None
            for alias in addr_to_aliases.get(addr, [raw_name]):
                recomp_off = recomp_map.get(alias)
                if recomp_off is not None:
                    raw_name = alias
                    break
            if recomp_off is None:
                _status(
                    f"  ?  {raw_name.rstrip('_')}  "
                    f"(not found in recompiled map)"
                )
                n_miss += 1
                total += 1
                bucket["not_found"] += 1
                bucket["compared"] += 1
                continue

            total += 1
            bucket["compared"] += 1

            orig_bytes   = orig_code[orig_off : orig_off + func_size]
            recomp_bytes = recomp_code[recomp_off : recomp_off + func_size]
            # Audit-only RC slice bounded by the actual RC function end
            # (see `_rc_func_size`'s docstring): the constant / arg-swap
            # audits build *multisets* of immediate constants, so any
            # bytes past the RC function's own end leak as phantom
            # constants from the next function.  Worked example:
            # `build_city_item` (PS 0xCB3b / RC 0xC39b) used to flag
            # `cmp edi, 0x1e/0x1f ; jne` equality literals that
            # physically belong to `prebuild_region_item`.  The diff
            # comparison and the other detectors keep the PS-sized
            # slice so byte-equivalence semantics are unchanged.
            recomp_audit_size = _rc_func_size(recomp_off, func_size)
            recomp_bytes_audit = recomp_code[recomp_off : recomp_off + recomp_audit_size]
            bucket["compared_func_bytes"] += func_size

            diffs = _compare_bytes(
                orig_bytes,   recomp_bytes,
                orig_off,     recomp_off,
                orig_fix,     recomp_fix,
            )

            size_differs = len(recomp_bytes) != func_size
            name = raw_name.rstrip("_")
            relocation_sites = final_link_relocations.get(addr, [])
            bucket["relocation_target_mismatches"] += len(relocation_sites)
            if corpus_builder is not None:
                _processed_funcs.add(name)

            # Cluster #32: trailing jump-table alignment pad (compiler-
            # version delta).  Code is byte-exact; only dead filler before
            # the fixup-masked table differs.  Count as exact (the filler
            # matters only for a final whole-image byte recreation).
            if (diffs and not size_differs and not relocation_sites
                    and _trailing_table_pad_only(
                        orig_bytes, recomp_bytes, diffs,
                        orig_off, orig_fix)):
                n_exact += 1
                n_pad += 1
                bucket["exact"] += 1
                bucket["exact_func_bytes"] += func_size
                _status(
                    f"  ~  {name}  ({func_size}b)  code exact; "
                    f"{len(diffs)} filler byte(s) before trailing jump "
                    f"table differ (cluster #32 version delta)"
                )
                if json_out and not json_summary:
                    json_funcs.append({
                        "name":              name,
                        "address":           f"0x{addr:X}",
                        "file":              str(rel),
                        "size":              func_size,
                        "recomp_size":       func_size,
                        "size_differs":      False,
                        "diff_byte_count":   0,
                        "exact":             True,
                        "trailing_pad_diff": len(diffs),
                        "style_hints":       _style_hints_for_json(name),
                        "global_cache_hint": _global_cache_hints_for_json(name),
                    })
                continue

            # Cross-module trailing scan-table: a last-in-module function's
            # extent swallows the NEXT module's first-function select/scan
            # tables (Watcom dumps them just before that function's entry
            # label).  The RC link order differs, so re-anchor the trailing
            # region at the RC next-symbol site; a fixup-masked match
            # proves the code is exact and the table faithfully reproduced.
            if diffs and not size_differs and not relocation_sites:
                _nxt_addr = off_to_addr.get(orig_off + func_size)
                _rc_next_off = None
                _nxt_name = None
                if _nxt_addr is not None:
                    _nxt_name = (addr_to_name.get(_nxt_addr) or "").rstrip("_")
                    for _al in addr_to_aliases.get(_nxt_addr, []):
                        _rc_next_off = recomp_map.get(_al)
                        if _rc_next_off is not None:
                            break
                if _next_fn_scan_table_only(
                        orig_bytes, recomp_code, diffs, orig_off, recomp_off,
                        _rc_next_off, orig_fix, recomp_fix):
                    n_exact += 1
                    n_xmod += 1
                    bucket["exact"] += 1
                    bucket["exact_func_bytes"] += func_size
                    _status(
                        f"  ~  {name}  ({func_size}b)  code exact; the "
                        f"{len(diffs)} trailing byte(s) are {_nxt_name}'s "
                        f"switch/scan table (next module) -- byte-verified "
                        f"at its RC site, not part of this function "
                        f"(symbol-extent over-reach, not a diff)"
                    )
                    if json_out and not json_summary:
                        json_funcs.append({
                            "name":              name,
                            "address":           f"0x{addr:X}",
                            "file":              str(rel),
                            "size":              func_size,
                            "recomp_size":       func_size,
                            "size_differs":      False,
                            "diff_byte_count":   0,
                            "exact":             True,
                            "xmod_table_diff":   len(diffs),
                            "style_hints":       _style_hints_for_json(name),
                            "global_cache_hint": _global_cache_hints_for_json(name),
                        })
                    continue

            # Tail-merge donor flip: every byte diff is explained by
            # PS tail-merging to a foreign donor while the recomp inlined
            # the epilogue (or chose a different donor).  The function's
            # body LOGIC is byte-equivalent; only the donor coupling --
            # which is a layout side-effect of other functions' sizes --
            # differs.  Count as exact-with-note (the "jump-table filler"
            # analogue for tail-merge).
            donor_note = (
                _donor_flip_exit_only(
                    orig_bytes, recomp_bytes, diffs,
                    orig_off=orig_off, recomp_off=recomp_off,
                    orig_fix=orig_fix, recomp_fix=recomp_fix)
                if (diffs and not size_differs) else None
            )
            # Rule 4: cmp operand swap + complementary Jcc -- source-level
            # ambiguity (`a < b` vs `b > a`).  Same semantics, different
            # bytes (ModRM + Jcc opcode).  When EVERY diff is explained
            # by a Rule 4 swap, count as exact.
            r4_sites = (_rule4_only_diffs(orig_bytes, recomp_bytes, diffs)
                        if (diffs and not size_differs) else None)
            if (r4_sites is not None and donor_note is None
                    and not relocation_sites):
                n_exact += 1
                n_rule4 += 1
                bucket["exact"] += 1
                bucket["exact_func_bytes"] += func_size
                r103_note = _rule103_branchy_def_note(orig_bytes,
                                                      recomp_bytes)
                _status(
                    f"  ~  {name}  ({func_size}b)  semantics exact; "
                    f"{len(diffs)} byte(s) differ via Rule 4 cmp-swap "
                    f"({r4_sites} site{'s' if r4_sites > 1 else ''}; "
                    f"`a < b` vs `b > a` source ambiguity)"
                )
                if r103_note is not None:
                    _status(f"     {r103_note}")
                if json_out and not json_summary:
                    json_funcs.append({
                        "name":               name,
                        "address":            f"0x{addr:X}",
                        "file":               str(rel),
                        "size":               func_size,
                        "recomp_size":        func_size,
                        "size_differs":       False,
                        "diff_byte_count":    0,
                        "exact":              True,
                        "rule4_swap_diff":    len(diffs),
                        "rule4_swap_sites":   r4_sites,
                        "rule103_lever":      r103_note,
                        "style_hints":        _style_hints_for_json(name),
                        "global_cache_hint":  _global_cache_hints_for_json(name),
                    })
                continue

            if donor_note is not None and not relocation_sites:
                n_exact += 1
                n_donor_flip += 1
                bucket["exact"] += 1
                bucket["exact_func_bytes"] += func_size
                _status(
                    f"  ~  {name}  ({func_size}b)  body exact; "
                    f"{len(diffs)} byte(s) differ via {donor_note} "
                    f"(turtles up to wrong donor)"
                )
                if json_out and not json_summary:
                    json_funcs.append({
                        "name":               name,
                        "address":            f"0x{addr:X}",
                        "file":               str(rel),
                        "size":               func_size,
                        "recomp_size":        func_size,
                        "size_differs":       False,
                        "diff_byte_count":    0,
                        "exact":              True,
                        "donor_flip_diff":    len(diffs),
                        "donor_flip_note":    donor_note,
                        "style_hints":        _style_hints_for_json(name),
                        "global_cache_hint":  _global_cache_hints_for_json(name),
                    })
                continue

            if not diffs and not size_differs:
                if relocation_sites:
                    relocation_label = (
                        "relocation target" if len(relocation_sites) == 1
                        else "relocation targets"
                    )
                    relocation_verb = (
                        "DIVERGES" if len(relocation_sites) == 1 else "DIVERGE"
                    )
                    n_diff += 1
                    bucket["diff"] += 1
                    bucket["diff_func_bytes"] += func_size
                    _status(
                        f"  ✗  {name}  ({func_size}b)  bytes exact under "
                        f"the loader-fixup mask, but {len(relocation_sites)} "
                        f"{relocation_label} {relocation_verb}"
                    )
                    if verbose:
                        for site in relocation_sites:
                            _status(
                                f"       fixup @+{site['function_offset']:#x}: "
                                f"PS→{site.get('ps_target_name', site['ps_target'])}  "
                                f"RC→{site.get('rc_target_name', site['rc_target'])}"
                            )
                    if json_out and not json_summary:
                        json_funcs.append({
                            "name":              name,
                            "address":           f"0x{addr:X}",
                            "file":              str(rel),
                            "size":              func_size,
                            "recomp_size":       func_size,
                            "size_differs":      False,
                            "diff_byte_count":   0,
                            "exact":             False,
                            "relocation_target_sites": relocation_sites,
                            "style_hints":       _style_hints_for_json(name),
                            "global_cache_hint": _global_cache_hints_for_json(name),
                        })
                    continue
                # Bytes match under the mask — now audit what the mask
                # HIDES: resolve every masked rel-branch displacement
                # symbolically on both sides.  A mismatch is a REAL
                # divergence (wrong callee / different ComTail merge
                # point that includes or excludes whole statements).
                bt_sites = _branch_target_audit(
                    orig_bytes, recomp_bytes, orig_off, recomp_off,
                    orig_fix, recomp_fix, _bt_ps_resolve, _bt_rc_resolve,
                )
                if bt_sites:
                    n_diff += 1
                    bucket["diff"] += 1
                    bucket["byte_diff"] += sum(s["width"] for s in bt_sites)
                    bucket["diff_func_bytes"] += func_size
                    _status(
                        f"  ✗  {name}  ({func_size}b)  bytes exact under "
                        f"the rel-branch mask, but {len(bt_sites)} masked "
                        f"branch target(s) DIVERGE (Branch-target audit):"
                    )
                    for s in bt_sites:
                        _status(
                            f"       {s['mnem']} @+{s['insn_off']:#x}: "
                            f"PS→{s['ps_target']}  RC→{s['rc_target']}"
                        )
                    if json_out and not json_summary:
                        json_funcs.append({
                            "name":              name,
                            "address":           f"0x{addr:X}",
                            "file":              str(rel),
                            "size":              func_size,
                            "recomp_size":       func_size,
                            "size_differs":      False,
                            "diff_byte_count":   sum(s["width"]
                                                     for s in bt_sites),
                            "exact":             False,
                            "branch_target_sites": bt_sites,
                            "style_hints":       _style_hints_for_json(name),
                            "global_cache_hint": _global_cache_hints_for_json(name),
                        })
                    continue
                n_exact += 1
                bucket["exact"] += 1
                bucket["exact_func_bytes"] += func_size
                if corpus_builder is not None and recomp_line_map:
                    # Exact => RC bytes == PS bytes; the RC -d1 line table
                    # gives the certain source line for each code run.
                    insns = [(t[0], t[2]) for t in _disasm_for_diff(recomp_bytes)]
                    runs = extract_line_runs(
                        insns, recomp_off, recomp_fix,
                        recomp_line_map, cf,
                    )
                    corpus_builder.add_function(name, str(rel), runs)
                    # Sidecar for `c2 local-hints --validate`: statement-start
                    # offsets (relative to fn entry) -> OUR source line.
                    exact_line_sidecar[name] = {
                        "file": str(rel),
                        "starts": {
                            str(roff): recomp_line_map[recomp_off + roff]
                            for roff, _raw in insns
                            if (recomp_off + roff) in recomp_line_map
                        },
                    }
                if json_out and not json_summary:
                    json_funcs.append({
                        "name":              name,
                        "address":           f"0x{addr:X}",
                        "file":              str(rel),
                        "size":              func_size,
                        "recomp_size":       func_size,
                        "size_differs":      False,
                        "diff_byte_count":   0,
                        "exact":             True,
                        **_recon_bundle_for_json(
                            orig_bytes, orig_off, recomp_bytes, recomp_off,
                            orig_fix, recomp_fix, line_map, 0,
                        ),
                        "style_hints":       _style_hints_for_json(name),
                        "global_cache_hint": _global_cache_hints_for_json(name),
                    })
                continue

            n_diff += 1
            bucket["diff"] += 1
            bucket["byte_diff"] += len(diffs)
            bucket["diff_func_bytes"] += func_size

            if json_summary:
                continue

            if json_out:
                # Build the structured row stream once per diffing function;
                # JSON mode skips the textual rendering entirely.
                json_rows, json_hints = _build_diff_rows(
                    orig_bytes,   orig_off,
                    recomp_bytes, recomp_off,
                    orig_fix,     recomp_fix,
                    line_map,
                )
                json_funcs.append({
                    "name":              name,
                    "address":           f"0x{addr:X}",
                    "file":              str(rel),
                    "size":              func_size,
                    "recomp_size":       len(recomp_bytes),
                    "size_differs":      size_differs,
                    "diff_byte_count":   len(diffs),
                    "diff_byte_offsets": diffs,
                    "relocation_target_sites": relocation_sites,
                    "diff_row_count":    sum(
                        1 for r in json_rows if r["kind"] != "equal"
                    ),
                    "rule_hints":        dict(histogram(json_hints)),
                    "pragma_hint":       _pragma_hint_for_json(
                        orig_bytes, recomp_bytes,
                    ),
                    "tail_merge":        _tail_merge_to_json(
                        _scan_tail_merge_donor(
                            orig_bytes, orig_off, is_vaddr=False,
                        )
                    ),
                    "sibling_hint":      _sibling_hint_for_json(name),
                    "rule103_lever":     _rule103_branchy_def_note(
                        orig_bytes, recomp_bytes,
                    ),
                    "style_hints":       _style_hints_for_json(name),
                    "global_cache_hint": _global_cache_hints_for_json(name),
                    "reload_hint":       _reload_hint_for_json(
                        name, _disasm_for_diff(orig_bytes),
                    ),
                    "frame_hint":        _frame_hint_for_json(
                        orig_bytes, recomp_bytes, json_rows,
                    ),
                    "const_audit":       _const_audit_for_json(
                        orig_bytes, recomp_bytes_audit,
                        orig_off, recomp_off, orig_fix, recomp_fix,
                    ),
                    "arg_swap":          _argswap_for_json(
                        orig_bytes, recomp_bytes_audit,
                        orig_off, recomp_off, orig_fix, recomp_fix,
                        recomp_map,
                    ),
                    "crossbuild":        _crossbuild_for_json(name),
                    "moved_code":        _moved_code_for_json(name),
                    "loops":             _loops_for_json(name),
                    "dispatch_hint":     _dispatch_hint_for_json(
                        name, orig_bytes,
                    ),
                    "sched_hint":        _sched_hint_for_json(
                        name, orig_bytes, recomp_bytes, json_rows,
                    ),
                    "binir_shape_hint":  _binir_shape_hint_for_json(
                        json_rows,
                    ),
                    "decl_order_hint":   _decl_order_hint_for_json(
                        name, orig_bytes, recomp_bytes,
                        json_rows, json_hints,
                        dict(histogram(json_hints)),
                    ),
                    "byte_pump_hint":    _byte_pump_hint_for_json(name),
                    "byte_seat":         _byte_seat_for_json(
                        name, json_hints, orig_bytes,
                    ),
                    "slot_swap":         _slot_swap_for_json(
                        name, orig_bytes, recomp_bytes, json_rows,
                    ),
                    "loop_rotation":     _loop_rotation_for_json(
                        orig_bytes, recomp_bytes,
                    ),
                    **_recon_bundle_for_json(
                        orig_bytes, orig_off, recomp_bytes, recomp_off,
                        orig_fix, recomp_fix, line_map, len(diffs),
                        recomp_line_map=recomp_line_map,
                        recomp_audit=recomp_bytes_audit,
                    ),
                    "rows":              _diff_to_json_rows(
                        json_rows, json_hints,
                    ),
                })
                continue

            size_note = "  [size differs]" if size_differs else ""
            relocation_note = (
                f"  [{len(relocation_sites)} relocation "
                f"{'target' if len(relocation_sites) == 1 else 'targets'} "
                "diverge]"
                if relocation_sites else ""
            )
            # Per-function diff row: bytes + layered shape on ONE line,
            # with fixed-width columns so values align vertically across
            # rows in the bulk view.  Per Hard Rule #3 the JUDGE metric
            # is shape; the byte count is the DONE-oracle (0 = exact)
            # and a navigation aid.
            shape_cells = ""
            fix_next = ""
            try:
                _rb = _recon_bundle_for_json(
                    orig_bytes, orig_off, recomp_bytes, recomp_off,
                    orig_fix, recomp_fix, line_map, 0,
                    recomp_line_map=recomp_line_map,
                    recomp_audit=recomp_bytes_audit)
                _sd = _rb.get("shape_distance") or {}
                if _sd:
                    shape_cells = _format_shape_cols(_sd)
                    fix_next = f" → {_sd.get('fix_next','?')}"
            except Exception:
                pass
            name_col = f"{name:<36}"
            size_col = f"{func_size:>5}b"
            if diffs:
                bd_col = f"{len(diffs):>5}bd"
            else:
                bd_col = "   sz-mismatch"
            typer.echo(
                f"  ✗  {name_col}  {size_col}  {bd_col}  "
                f"{shape_cells}{fix_next}{size_note}{relocation_note}"
            )
            if verbose and relocation_sites:
                for site in relocation_sites:
                    _status(
                        f"       fixup @+{site['function_offset']:#x}: "
                        f"PS→{site.get('ps_target_name', site['ps_target'])}  "
                        f"RC→{site.get('rc_target_name', site['rc_target'])}"
                    )
            if function:
                _mac_hint(name)
                _win_hint(name)
                if mac_decompile:
                    mac_c = _mac_decompile_block(name)
                    if mac_c:
                        typer.echo("")
                        typer.echo("     mac-decompile (PEF-indirection collapsed):")
                        for ln in mac_c.splitlines():
                            typer.echo(f"     | {ln}")
                        typer.echo("")
                if win_decompile:
                    win_c = _win_decompile_block(name)
                    if win_c:
                        typer.echo("")
                        typer.echo("     win-decompile (MSVC 4.0 /Od, x86 source-shape):")
                        for ln in win_c.splitlines():
                            typer.echo(f"     | {ln}")
                        typer.echo("")
            if verbose:
                _ca = _const_audit_for_json(
                    orig_bytes, recomp_bytes_audit,
                    orig_off, recomp_off, orig_fix, recomp_fix,
                )
                if _ca:
                    _bits = []
                    for _ch, _lbl in (("cmp_threshold", "cmp-boundary"),
                                      ("eq", "eq"), ("plain", "plain")):
                        if _ch in _ca:
                            _ps = ",".join(f"{k:#x}" for k in
                                            sorted(_ca[_ch]["ps_only"]))
                            _rc = ",".join(f"{k:#x}" for k in
                                            sorted(_ca[_ch]["rc_only"]))
                            _bits.append(f"{_lbl}[PS:{_ps or '-'} RC:{_rc or '-'}]")
                    _flag = (" ⚠ off-by-one boundary (n vs n±1 / >,>=)"
                             if _ca.get("boundary_offby1") else "")
                    typer.secho(
                        f"  Const-audit: {_ca['n_div']} divergent "
                        f"constant(s){_flag} -- " + "  ".join(_bits)
                        + "  (regalloc-invariant; `c2 const-audit "
                        + f"{name}`)",
                        fg="yellow")
                _aw = _argswap_for_json(
                    orig_bytes, recomp_bytes_audit, orig_off, recomp_off,
                    orig_fix, recomp_fix, recomp_map,
                )
                if _aw:
                    from c2.commands.const_audit import _ARGNAME as _AN
                    for _s in _aw:
                        typer.secho(
                            f"  Arg-swap: {_s['callee']}() const "
                            f"{_s['const']:#x} -> PS {_AN[_s['ps_slot']]} but "
                            f"RC {_AN[_s['rc_slot']]} (out-of-order parameter; "
                            f"check the call's arg order)", fg="red")
                if full:
                    _render_diff(
                        orig_bytes,   orig_off,
                        recomp_bytes, recomp_off,
                        orig_fix,     recomp_fix,
                        line_map=line_map,
                    )
                elif compact:
                    _render_compact(
                        orig_bytes,   orig_off,
                        recomp_bytes, recomp_off,
                        orig_fix,     recomp_fix,
                        line_map=line_map,
                        name=name,
                    )
                else:
                    _render_side_by_side(
                        orig_bytes,   orig_off,
                        recomp_bytes, recomp_off,
                        orig_fix,     recomp_fix,
                        line_map=line_map,
                        recomp_line_map=recomp_line_map,
                        name=name,
                        recomp_code=recomp_code,
                        recomp_ranges=recomp_ranges,
                    )

    if not keep:
        _cleanup_work(work)
    _tick("compare + render diffs")

    if corpus_builder is not None:
        from c2.commands.line_corpus import CORPUS_PATH
        corpus_builder.save(
            merge_processed=_processed_funcs if _partial_pass else None)
        try:
            import json as _json
            _sidecar_path = CORPUS_PATH.parent / "exact-line-map.json"
            if _partial_pass and _sidecar_path.exists():
                # Merge: refresh the visited functions, preserve the rest.
                # A visited function that is no longer byte-exact (absent from
                # exact_line_sidecar) is dropped from the sidecar.
                try:
                    _existing = _json.loads(_sidecar_path.read_text()) or {}
                except (OSError, ValueError):
                    _existing = {}
                for _fn in _processed_funcs:
                    if _fn in exact_line_sidecar:
                        _existing[_fn] = exact_line_sidecar[_fn]
                    else:
                        _existing.pop(_fn, None)
                _sidecar_out = _existing
            else:
                _sidecar_out = exact_line_sidecar
            _tmp = _sidecar_path.with_suffix(f".tmp{os.getpid()}")
            _tmp.write_text(_json.dumps(_sidecar_out))
            _tmp.replace(_sidecar_path)
        except Exception:
            pass
        # Cache-write side-effect notice -- diagnostic only, never a result.
        # Keep it off the normal summary output (it used to land awkwardly
        # between the last per-function row and the summary); surface it on
        # stderr under --timings for anyone debugging corpus rebuilds.
        if timings:
            typer.echo(
                f"line-corpus: {'merged' if _partial_pass else 'indexed'} "
                f"{corpus_builder.n_runs} line-runs from "
                f"{corpus_builder.n_funcs} byte-exact functions -> {CORPUS_PATH}",
                err=True,
            )

    # The strict rebuild ran before the function loop so relocation defects
    # appeared in their owning TU rows.  Its detailed whole-image report lives
    # here, after the actionable listing.  --no-strict never enters this path.
    if strict:
        _status("\nStrict final-link verification …")
        for line in final_link_output.splitlines():
            _status(line)
        if final_link_failures:
            _status("  strict final-link FAILED:")
            for reason in final_link_failures:
                _status(f"    - {reason}")
        else:
            _status("  strict whole-file byte-exact (PS debug trailer grafted)")

    # ── Summary ───────────────────────────────────────────────────────────
    exact_func_bytes = sum(b.get("exact_func_bytes", 0)
                           for b in files_summary.values())
    diff_func_bytes = sum(b.get("diff_func_bytes", 0)
                          for b in files_summary.values())
    compared_func_bytes = sum(b.get("compared_func_bytes", 0)
                              for b in files_summary.values())
    # The structured result is built unconditionally so the function can
    # RETURN it to in-process callers (the pi toolapi / permute) without a
    # stdout round-trip; the CLI still echoes it under --json.
    result = {
        "summary": {
            "exact":        n_exact,
            "donor_flip": n_donor_flip,   # of the exact: body-exact,
                                          # donor coupling differs (~)
            "rule4_swap": n_rule4,        # of the exact: semantics-
                                          # exact, Rule 4 cmp-swap (~)
            "trailing_pad": n_pad,   # of the exact: code-exact with
                                     # post-ret jump-table filler diffs
                                     # (cluster #32; see per-function
                                     # trailing_pad_diff)
            "xmod_table": n_xmod,    # of the exact: code-exact; symbol
                                     # extent over-reaches into the next
                                     # module's leading switch/scan table
                                     # (bytes verified at RC site, NOT a
                                     # diff; see per-function xmod_table_diff)
            "diff":         n_diff,
            "not_found":    n_miss,
            "stub_skipped": n_stub,
            "compared":     total,
            "byte_diff":    sum(b.get("byte_diff", 0)
                                  for b in files_summary.values()),
            "relocation_target_mismatches": sum(
                b.get("relocation_target_mismatches", 0)
                for b in files_summary.values()),
            "exact_func_bytes": exact_func_bytes,
            "diff_func_bytes": diff_func_bytes,
            "compared_func_bytes": compared_func_bytes,
        },
        "files":     files_summary,
        "functions": json_funcs,
    }
    if final_link_report is not None:
        result["final_link"] = _final_link_json(
            final_link_report, final_link_failures)
    if json_out:
        # Single JSON document on stdout.  Top-level shape:
        #   { "summary": {...}, "files": {...}, "functions": [...] }
        typer.echo(json.dumps(result, indent=2))
    else:
        typer.echo(f"\n{'═' * 52}")
        # Top-level tallies -- one per row so the block stays scannable.
        _tallies = [
            (n_exact, "exact"),
            (n_diff,  "diff"),
            (n_miss,  "not-found"),
            (n_stub,  "stub-skipped"),
            (total,   "compared"),
        ]
        _tallies = [(c, lbl) for c, lbl in _tallies
                    if c or lbl in ("exact", "compared")]
        _tw = max(len(str(c)) for c, _ in _tallies)
        for c, lbl in _tallies:
            typer.echo(f"  {c:>{_tw}} {lbl}")
        # Sub-buckets of `exact` (code/semantics exact, benign residual
        # note).  One per line, short desc, so the headline stays clean.
        _exact_notes = [
            (n_pad,        "~pad",   "trailing jump-table filler differs"),
            (n_xmod,       "~xmod",  "extent over-reaches into next module's table"),
            (n_donor_flip, "~donor", "body exact, tail-merge donor differs"),
            (n_rule4,      "~r4",    "semantics exact, Rule 4 cmp-swap differs"),
        ]
        _exact_notes = [(c, t, d) for c, t, d in _exact_notes if c]
        if _exact_notes:
            typer.echo("  of the exact:")
            _cw = max(len(str(c)) for c, _, _ in _exact_notes)
            for c, tag, desc in _exact_notes:
                typer.echo(f"    {c:>{_cw}} {tag:<6} {desc}")
        if n_build_errors or n_build_warnings:
            typer.echo(
                f"  build:"
                + (f" {n_build_errors} error(s)" if n_build_errors else "")
                + (f" {n_build_warnings} warning(s)" if n_build_warnings else "")
            )
    if strict and (n_diff or n_miss or final_link_failures):
        raise typer.Exit(1)
    if strict_warnings and (n_build_errors or n_build_warnings):
        raise typer.Exit(2)
    return result

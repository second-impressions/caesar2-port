"""AST-based C source analysis and generation for the decomp pipeline.

Uses pycparser to parse C source files into an AST, then provides:
  - Declaration classification (extern vars, extern fns, owned globals, …)
  - Stub generation (extern decl → zero-initialised definition)
  - Header generation from symbols.json
  - Preprocessing shim for Watcom/pycparser compatibility

All regex-based parsing from decomp_verify.py and gen_header.py is
consolidated here behind a clean AST interface.
"""
from __future__ import annotations

import copy
import json
import re
from collections import defaultdict
from functools import lru_cache
from dataclasses import dataclass, field
from pathlib import Path

import os

import pycparser
from pycparser import c_ast, c_generator


# ── Preprocessing shim ─────────────────────────────────────────────────────────

# C constructs that pycparser can't handle — stripped or rewritten before
# parsing.  The original source is never modified; only the text fed to
# pycparser goes through this transform.

_CPP_DIRECTIVE_RE = re.compile(r"^\s*#[^\n]*$", re.MULTILINE)
_LINE_COMMENT_RE = re.compile(r"//[^\n]*")
_BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
_WATCOM_KW_RE = re.compile(
    r"\b(?:"
    r"__cdecl|__watcall|__pascal|__fortran|__syscall|__stdcall|__fastcall|"
    r"__far|__near|__huge|__based|__segment|__far16|"
    r"__interrupt|__saveregs|__loadds|__export"
    r")\b"
)

# Watcom's far-pointer "base operator" `seg :> offset` (builds a far
# pointer from a segment expression and a near-pointer offset; see the
# MK_FP macro in the toolchain's i86.h).  pycparser has no such token —
# rewrite it to binary `+` so both operands survive as subexpressions
# in the AST (the transform is parse-only, never compiled).  Padded to
# two chars to keep column alignment with the original source.  NB: ISO
# digraph `:>` (= `]`) is unused in this corpus, so the plain rewrite is
# safe.
_WATCOM_BASEOP_RE = re.compile(r":>")

# Calling-convention keywords that change Watcom's emitted symbol name
# and/or ABI.  pycparser's preprocess() strips these (above), so they
# never survive into the AST — the auto-stub generator therefore needs a
# separate text scan (scan_calling_conventions) to learn which external
# functions are __pascal / __cdecl / etc. and re-emit the keyword on the
# generated stub so the linker symbol matches the call site.
_CONV_KEYWORDS = {
    "__cdecl", "__watcall", "__pascal", "__fortran",
    "__syscall", "__stdcall", "__fastcall",
}
_CONV_MACRO_RE = re.compile(
    r"^\s*#\s*define\s+(\w+)\s+(__\w+)\s*$", re.MULTILINE
)

# Pointer-type qualifiers — also stripped by preprocess() above, but
# unlike calling conventions these go BETWEEN the base type and the
# pointer `*` of a pointer-returning decl (`char __far *name(...)`),
# not before the function name.  A far-pointer return occupies edx:eax
# (two registers), so the qualifier is load-bearing for Watcom's
# register contract; without re-injection a far-pointer-returning stub
# emits `char *name(...)` (near — eax only) and the build errors E1062
# (far-vs-near return mismatch) once the header declares the prototype
# far.  See docs/codegen-experiments/start_tune.py.
_PTR_QUALIFIERS = {"__far", "__near", "__huge", "__far16"}
_PTR_QUAL_RE = re.compile(
    r"\b(__far|__near|__huge|__far16)\s*\*\s*(\w+)\s*\("
)


def scan_calling_conventions(header_texts: list[str]) -> dict[str, str]:
    """Map function name → calling-convention keyword from header text.

    Scans raw header source (NOT the pycparser AST, which has already
    discarded convention keywords) for function declarations carrying a
    convention keyword — either a literal (`__pascal`, `__cdecl`, …) or
    an object-like macro that expands to one (e.g. RAD's
    ``#define RADEXPLINK __pascal``).  Used by the verifier's auto-stub
    generator so a stub for, say, ``SmackToScreen`` is emitted
    ``void __pascal SmackToScreen(...)`` and therefore links as the
    uppercase ``SMACKTOSCREEN`` symbol PS.EXE imports.
    """
    conv: dict[str, str] = {}
    for text in header_texts:
        # Resolve object-like macros that alias a convention keyword.
        macros = {
            m.group(1): m.group(2)
            for m in _CONV_MACRO_RE.finditer(text)
            if m.group(2) in _CONV_KEYWORDS
        }
        tokens = _CONV_KEYWORDS | set(macros)
        if not tokens:
            continue
        clean = _BLOCK_COMMENT_RE.sub("", _LINE_COMMENT_RE.sub("", text))
        tok_re = r"\b(?:" + "|".join(re.escape(t) for t in tokens) + r")\b"
        # Each `;`-terminated declaration that mentions a convention
        # token: the function name is the identifier just before the
        # first '(' (the parameter list).
        for chunk in clean.split(";"):
            if not re.search(tok_re, chunk):
                continue
            name_m = re.search(r"(\w+)\s*\(", chunk)
            if not name_m:
                continue
            tok_m = re.search(tok_re, chunk)
            kw = tok_m.group(0)
            conv[name_m.group(1)] = macros.get(kw, kw)
    return conv


def scan_pointer_qualifiers(header_texts: list[str]) -> dict[str, str]:
    """Map pointer-returning function name → pointer-qualifier keyword.

    Scans raw header source for declarations like
    ``char __far *_AIL_start_sequence(int)`` — which pycparser's
    preprocess() reduces to ``char *_AIL_start_sequence(int)`` (the
    ``__far`` is stripped before parsing, never reaching the AST).  The
    auto-stub generator re-emits the stripped qualifier so the stub
    matches the header's pointer size: a far-pointer return occupies
    edx:eax (two registers), not just eax.  Without this re-injection a
    far-returning stub emits ``char *name(...)`` (near) and the build
    errors E1062 (far-vs-near return mismatch).

    Pattern: a qualifier token immediately before ``*name(`` — anchored
    on the function name so parameter pointers (``char *param``, which
    precede a different identifier) are not matched.
    """
    qual: dict[str, str] = {}
    for text in header_texts:
        clean = _BLOCK_COMMENT_RE.sub("", _LINE_COMMENT_RE.sub("", text))
        for m in _PTR_QUAL_RE.finditer(clean):
            qual[m.group(2)] = m.group(1)
    return qual


# Annotations we care about — preserved in a side table, keyed by
# the *next* non-blank source line's line number.
_ANNOT_RE = re.compile(
    r"^\s*//\s*(FUNCTION|STUB):\s*(\w+)\s+(0x[0-9A-Fa-f]+)",
    re.MULTILINE,
)


@dataclass
class Annotation:
    """A ``// FUNCTION: C2 0xADDR`` or ``// STUB: C2 0xADDR`` comment."""
    kind: str      # "FUNCTION" or "STUB"
    module: str    # e.g. "C2"
    address: str   # e.g. "0x5910F"
    line: int      # 1-based line in the *original* source


def _collect_annotations(src: str) -> dict[int, Annotation]:
    """Scan original source for FUNCTION/STUB annotations.

    Returns a dict mapping the 1-based line number of the *annotated
    declaration/definition* (the next non-blank line after the comment)
    to the annotation.
    """
    annotations: dict[int, Annotation] = {}
    lines = src.splitlines()
    for m in _ANNOT_RE.finditer(src):
        comment_line = src[: m.start()].count("\n") + 1  # 1-based
        # Find next non-blank, non-comment line (the actual decl/def)
        for i in range(comment_line, len(lines)):
            stripped = lines[i].strip()
            if not stripped:
                continue
            if stripped.startswith("//") or stripped.startswith("/*"):
                continue
            annotations[i + 1] = Annotation(
                kind=m.group(1),
                module=m.group(2),
                address=m.group(3),
                line=comment_line,
            )
            break
    return annotations


def preprocess(src: str) -> str:
    """Transform C source so pycparser can parse it.

    Strips preprocessor directives, comments, and Watcom keywords.
    The result is *only* used for AST construction — never compiled.
    """
    # Preserve line numbers when stripping: replace removed runs with
    # an equivalent number of newlines so pycparser's reported line numbers
    # stay aligned with the *original* source (which is the coordinate
    # space used by the annotation extractor).
    def _keep_lines(m: re.Match) -> str:
        return "\n" * m.group(0).count("\n")
    text = _CPP_DIRECTIVE_RE.sub(_keep_lines, src)
    text = _LINE_COMMENT_RE.sub(_keep_lines, text)
    text = _BLOCK_COMMENT_RE.sub(_keep_lines, text)
    text = _WATCOM_KW_RE.sub("", text)
    text = _WATCOM_BASEOP_RE.sub("+ ", text)
    # pycparser needs typedef NAMES in scope to disambiguate
    # ``heading_t x;`` (a declaration) from ``heading_t * x`` (a
    # product).  The ``#include``s that would define them are stripped
    # above, so seed the parser with a ``typedef int NAME;`` for every
    # typedef declared in the project headers.  ``int`` is a lie the AST
    # never cares about (we only need structure / line-mapping), and it
    # is injected onto the START of line 1 (no extra newline) so every
    # reported coord stays aligned with the original source.
    names = _project_typedef_names()
    if names:
        preamble = "".join(f"typedef int {n};" for n in sorted(names))
        text = preamble + text
    return text


_TYPEDEF_ONELINE_RE = re.compile(
    r"typedef\s+[^;{}]+?\b(\w+)\s*;", re.MULTILINE)
_TYPEDEF_BRACE_RE = re.compile(
    r"typedef\s+(?:enum|struct|union)\b[^{;]*\{.*?\}\s*(\w+)\s*;", re.DOTALL)


@lru_cache(maxsize=1)
def _project_typedef_names() -> frozenset[str]:
    """Typedef names declared in ``decomp/include/*.h``.

    Scanned once per process.  Both one-liner ``typedef ... NAME;`` and
    multi-line ``typedef enum|struct|union {...} NAME;`` forms are
    picked up.  Array size-check typedefs (``typedef char foo[...];``)
    naturally don't match (the ``[]`` breaks the ``\\w+;`` tail) and
    would be harmless even if they did.  Returns an empty set when the
    include dir is absent (e.g. unit tests on synthetic source), leaving
    ``preprocess`` a no-op.
    """
    inc = Path("decomp/include")
    if not inc.is_dir():
        return frozenset()
    names: set[str] = set()
    for h in sorted(inc.glob("*.h")):
        try:
            txt = h.read_text(errors="replace")
        except OSError:
            continue
        txt = _BLOCK_COMMENT_RE.sub("", _LINE_COMMENT_RE.sub("", txt))
        for m in _TYPEDEF_ONELINE_RE.finditer(txt):
            names.add(m.group(1))
        for m in _TYPEDEF_BRACE_RE.finditer(txt):
            names.add(m.group(1))
    return frozenset(names)


# ── Parsing ────────────────────────────────────────────────────────────────────

_parser_instance: pycparser.CParser | None = None


def _get_parser() -> pycparser.CParser:
    global _parser_instance
    if _parser_instance is None:
        _parser_instance = pycparser.CParser()
    return _parser_instance


_AST_CACHE_DIR = Path(".c2-cache/ast")


@lru_cache(maxsize=512)
def _parse_c_cached(src: str, filename: str) -> c_ast.FileAST:
    # Two-level cache: in-process lru + cross-process pickle keyed by
    # content hash.  A fresh `c2 decomp-verify` process was re-parsing
    # ~75 file bodies (~9s of pycparser) on EVERY invocation -- the
    # pickle loads in ~5ms each.  ASTs are treated as read-only by all
    # callers (same contract as the lru cache).
    import hashlib
    import pickle
    key = hashlib.sha1(f"{filename}\x00{src}".encode()).hexdigest()
    pk = _AST_CACHE_DIR / f"{key}.ast.pkl"
    if pk.exists():
        try:
            with open(pk, "rb") as f:
                return pickle.load(f)
        except Exception:
            pass        # corrupt/stale -> reparse below
    clean = preprocess(src)
    ast = _get_parser().parse(clean, filename=filename)
    try:
        _AST_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        tmp = pk.with_suffix(f".tmp{os.getpid()}")
        with open(tmp, "wb") as f:
            pickle.dump(ast, f, protocol=pickle.HIGHEST_PROTOCOL)
        tmp.replace(pk)             # atomic vs concurrent sessions
    except Exception:
        pass
    return ast


def parse_c(src: str, filename: str = "<string>") -> c_ast.FileAST:
    """Parse C source text (after preprocessing) into an AST.

    Memoised by (source, filename): the verifier's hint detectors each parse the
    SAME file source many times per run (classify_source was called 224x in a
    45s profile, almost all re-parses of a handful of files), so caching cuts
    the dominant cost of ``-v``. The AST is treated as read-only by callers."""
    return _parse_c_cached(src, filename)


# ── Declaration classification ─────────────────────────────────────────────────

@dataclass
class FileDecls:
    """Classified declarations from a single C source file."""
    extern_vars: list[c_ast.Decl] = field(default_factory=list)
    extern_fns: list[c_ast.Decl] = field(default_factory=list)
    forward_fns: list[c_ast.Decl] = field(default_factory=list)
    owned_vars: list[c_ast.Decl] = field(default_factory=list)
    struct_defs: list[c_ast.Decl] = field(default_factory=list)
    func_defs: list[c_ast.FuncDef] = field(default_factory=list)
    annotations: dict[int, Annotation] = field(default_factory=dict)


def classify(ast: c_ast.FileAST,
             annotations: dict[int, Annotation] | None = None) -> FileDecls:
    """Walk a FileAST and bucket every top-level node."""
    result = FileDecls(annotations=annotations or {})
    func_def_names: set[str] = set()

    # First pass: collect function definition names
    for node in ast.ext:
        if isinstance(node, c_ast.FuncDef):
            func_def_names.add(node.decl.name)

    # Second pass: classify everything
    for node in ast.ext:
        if isinstance(node, c_ast.FuncDef):
            result.func_defs.append(node)
            continue

        if not isinstance(node, c_ast.Decl):
            continue

        is_extern = "extern" in (node.storage or [])
        is_func = isinstance(node.type, c_ast.FuncDecl)
        is_struct_def = (
            isinstance(node.type, (c_ast.Struct, c_ast.Union))
            and getattr(node.type, "decls", None) is not None
            and node.name is None
        )

        if is_struct_def:
            result.struct_defs.append(node)
        elif is_extern and is_func:
            result.extern_fns.append(node)
        elif is_extern:
            result.extern_vars.append(node)
        elif is_func and node.name not in func_def_names:
            # Forward declaration without 'extern' keyword
            result.forward_fns.append(node)
        elif not is_func and node.name:
            result.owned_vars.append(node)

    return result


@lru_cache(maxsize=512)
def _classify_source_cached(src: str, filename: str) -> FileDecls:
    annotations = _collect_annotations(src)
    ast = parse_c(src, filename)
    return classify(ast, annotations)


def classify_source(src: str, filename: str = "<string>") -> FileDecls:
    """Parse + classify in one call, preserving annotations.  Memoised by
    content (read-only result) -- see :func:`parse_c`."""
    return _classify_source_cached(src, filename)


# ── Stub generation ────────────────────────────────────────────────────────────

_gen_instance: c_generator.CGenerator | None = None


def _get_generator() -> c_generator.CGenerator:
    global _gen_instance
    if _gen_instance is None:
        _gen_instance = c_generator.CGenerator()
    return _gen_instance


def _is_void_return(func_decl: c_ast.FuncDecl) -> bool:
    """Check whether a FuncDecl returns void."""
    ret = func_decl.type
    return (
        isinstance(ret, c_ast.TypeDecl)
        and isinstance(ret.type, c_ast.IdentifierType)
        and "void" in ret.type.names
    )


def _return_type_str(func_decl: c_ast.FuncDecl) -> str:
    """Render the return type of a FuncDecl as a C type string.

    Used by strip_stub_bodies() to cast the per-stub address literal
    to the right type — otherwise a stub returning ``char`` triggers
    W106 ("constant out of range") when given a 17-bit return value.
    Falls back to ``"int"`` when the return type is non-trivial
    (pointer, struct, etc.) — int is always assignable to int and
    the only failure mode in this fallback is a missed warning, not
    bad codegen.
    """
    ret = func_decl.type
    if isinstance(ret, c_ast.TypeDecl) and isinstance(
        ret.type, c_ast.IdentifierType
    ):
        return " ".join(ret.type.names)
    return "int"


def decl_to_stub(decl: c_ast.Decl) -> c_ast.Node:
    """Turn an extern declaration AST node into a stub definition node.

    - Extern var  → zero-initialised global (arrays get dim=1)
    - Extern func → empty body (void) or ``{ return 0; }``
    """
    stub = copy.deepcopy(decl)
    stub.storage = []  # drop 'extern'

    if isinstance(stub.type, c_ast.FuncDecl):
        if _is_void_return(stub.type):
            body = c_ast.Compound([], stub.coord)
        else:
            body = c_ast.Compound(
                [c_ast.Return(c_ast.Constant("int", "0"), stub.coord)],
                stub.coord,
            )
        return c_ast.FuncDef(stub, None, body, stub.coord)

    # Variable — set init to 0
    if isinstance(stub.type, c_ast.ArrayDecl):
        # Fix unsized arrays → [1]
        _fix_array_dim(stub.type)
        stub.init = c_ast.InitList(
            [c_ast.Constant("int", "0")], stub.coord
        )
    elif isinstance(stub.type, c_ast.TypeDecl) and isinstance(
        stub.type.type, c_ast.Struct
    ):
        # Struct: ``= {0}`` — Watcom rejects ``= 0`` for aggregate
        # types but accepts an aggregate initializer with a single
        # zero, which zero-fills the whole struct.
        stub.init = c_ast.InitList(
            [c_ast.Constant("int", "0")], stub.coord
        )
    else:
        stub.init = c_ast.Constant("int", "0")

    return stub


def _fix_array_dim(arr: c_ast.ArrayDecl) -> None:
    """Recursively set unsized array dimensions to 1."""
    if arr.dim is None:
        arr.dim = c_ast.Constant("int", "1")
    if isinstance(arr.type, c_ast.ArrayDecl):
        _fix_array_dim(arr.type)


def generate_stubs(source_text: str, filename: str,
                   header_text: str | None = None) -> str:
    """Generate a stubs.c source string from declarations in source_text.

    If header_text is provided (contents of c2_data.h), those declarations
    are included too.  Duplicate symbols are suppressed.
    """
    gen = _get_generator()
    parts: list[str] = [f"/* Auto-generated stubs for {filename} */\n"]
    seen: set[str] = set()

    # Parse all sources
    sources: list[str] = []
    if header_text:
        sources.append(header_text)
    sources.append(source_text)

    for src in sources:
        try:
            ast = parse_c(src, filename)
        except pycparser.c_parser.ParseError:
            continue
        decls = classify(ast)

        for d in decls.extern_vars + decls.extern_fns + decls.forward_fns:
            if d.name and d.name not in seen:
                seen.add(d.name)
                stub_node = decl_to_stub(d)
                if isinstance(stub_node, c_ast.FuncDef):
                    parts.append(gen.visit(stub_node))
                else:
                    parts.append(gen.visit(stub_node) + ";")

    return "\n".join(parts) + "\n"


# ── STUB body stripping ───────────────────────────────────────────────────────

_STUB_ANNOT_RE = re.compile(r"\s*//\s*STUB:\s*\w+\s+0x[0-9A-Fa-f]+")
# Captures the hex address from a STUB annotation so we can bake it
# into each stub's body as a per-stub discriminator constant — see
# strip_stub_bodies() below.
_STUB_ADDR_RE = re.compile(r"//\s*STUB:\s*\w+\s+0x([0-9A-Fa-f]+)")
# Just for extracting the function name from a declarator string —
# pycparser handles the void-vs-non-void decision (see _build_void_map
# below).  The function name is always the last identifier before the
# opening paren of the parameter list.
_DECL_NAME_RE = re.compile(r"(\w+)\s*\(")


def _build_void_map(source: str) -> dict[str, bool]:
    """Map every top-level function-name in ``source`` to its void-ness.

    Uses pycparser (via ``parse_c``) so calling-convention keywords,
    pointer returns, multi-line declarators, and other quirks are
    handled correctly without fragile regex hacks.

    Returns an empty dict when parsing fails (e.g. the source contains
    a construct pycparser can't handle); callers should treat a
    missing entry as "non-void" (the safer default — emits ``return 0``
    which compiles cleanly even for void functions in most settings,
    though we deliberately fall back rather than risk a wrong stub
    body).
    """
    try:
        ast = parse_c(source)
    except Exception:  # noqa: BLE001 — parse_c can raise many things
        return {}
    void_map: dict[str, bool] = {}
    for node in ast.ext:
        if not isinstance(node, c_ast.FuncDef):
            continue
        name = node.decl.name
        if not name:
            continue
        ftype = node.decl.type
        if isinstance(ftype, c_ast.FuncDecl):
            void_map[name] = _is_void_return(ftype)
    return void_map


def _build_return_type_map(source: str) -> dict[str, str]:
    """Map every top-level function-name in ``source`` to its return-type
    string (e.g. ``"char"``, ``"unsigned char"``, ``"int"``).

    Used by strip_stub_bodies to cast the address-marker literal to
    the correct return type; W106 ("constant out of range") fires
    on stubs declared as ``char foo(void)`` when the body returns
    a multi-byte address literal.  Casting silences the warning and
    keeps the per-stub uniqueness intact (the cast preserves the
    low byte, which is still distinct per stub at this scale).
    """
    try:
        ast = parse_c(source)
    except Exception:  # noqa: BLE001 — parse_c can raise many things
        return {}
    rt: dict[str, str] = {}
    for node in ast.ext:
        if not isinstance(node, c_ast.FuncDef):
            continue
        name = node.decl.name
        if not name:
            continue
        ftype = node.decl.type
        if isinstance(ftype, c_ast.FuncDecl):
            rt[name] = _return_type_str(ftype)
    return rt


def strip_stub_bodies(source: str) -> str:
    """Rewrite STUB-annotated function bodies to a non-inlinable canonical
    form, keeping the function definition *in the same translation unit*.

    Handles both the single-line form
        // STUB: C2 0x1234
        void foo(void) {}
    and the multi-line form
        // STUB: C2 0x1234
        // Lines 100–105
        void foo(void)
        {
        }

    The body is replaced by either::

        { __stub_sentinel(); }                  /* void return */
        { __stub_sentinel(); return 0; }        /* non-void return */

    where ``__stub_sentinel`` is a forward-declared external (defined
    once in stubs.c).  The sentinel call has two effects:

      1. Watcom 10.0a cannot inline the body across the call boundary
         (the sentinel's implementation isn't visible in this TU), so
         calls *to* the stub get emitted as real ``call`` / ``jmp``
         instructions instead of being inlined away — which is what
         used to destroy byte-equivalence with PS.EXE.
      2. The stub stays *physically* in the same .obj as its callers,
         so short relative jumps (``eb XX``) work — exactly matching
         PS.EXE's layout where each stubbed function lives in its own
         original source file.

    Previously this function replaced the body with a forward
    declaration (``;``) so the symbol moved to ``stubs.c``; the linker
    placed ``stubs.obj`` after every other object, making the byte
    distance from each call site to its stub far enough that Watcom
    promoted the encoding to ``e9 XX XX XX XX`` (5 bytes).  The new
    in-place form preserves the short encoding.
    """
    # Pre-scan the source with pycparser to determine which top-level
    # functions return void.  Pycparser sees through ``__cdecl`` /
    # ``__watcall`` / pointer-return / multi-line declarators that a
    # regex would mis-classify.  See _build_void_map() above.
    void_map = _build_void_map(source)
    rt_map   = _build_return_type_map(source)

    lines = source.splitlines(keepends=True)
    result: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if not _STUB_ANNOT_RE.match(line):
            result.append(line)
            i += 1
            continue

        # Capture the hex address from the STUB annotation; we'll bake
        # it into the rewritten body as a per-stub discriminator (see
        # below) so identical-bodies don't get merged by Watcom 10.0a's
        # identical-function-folding pass.
        addr_match = _STUB_ADDR_RE.search(line)
        stub_addr_hex = addr_match.group(1) if addr_match else "0"

        # Found STUB annotation — keep it and any subsequent comment-only
        # lines (e.g. "// Lines NNN–MMM") then process the function
        # declarator that follows.
        result.append(line)
        i += 1
        while i < len(lines) and (
            lines[i].lstrip().startswith("//") or not lines[i].strip()
        ):
            result.append(lines[i])
            i += 1

        # Now we should be at the function declarator.  Collect the
        # declarator line(s) up to and including the closing brace.
        decl_buf: list[str] = []
        brace_depth = 0
        seen_brace = False
        while i < len(lines):
            cur = lines[i]
            decl_buf.append(cur)
            for ch in cur:
                if ch == "{":
                    brace_depth += 1
                    seen_brace = True
                elif ch == "}":
                    brace_depth -= 1
            i += 1
            if seen_brace and brace_depth == 0:
                break

        if not decl_buf:
            continue

        joined = "".join(decl_buf)
        # Extract the function name (last identifier before the first
        # `(` in the declarator portion) and look up its return type
        # in the AST-derived void-map.  Falls back to non-void if
        # parsing failed or the name isn't found — a `return 0` body
        # is valid in any function signature where 0 is convertible
        # to the return type, which is true for every stub we emit.
        decl_part = joined.split("{", 1)[0]
        name_match = _DECL_NAME_RE.search(decl_part)
        is_void = (
            void_map.get(name_match.group(1), False)
            if name_match
            else False
        )
        ret_type = (
            rt_map.get(name_match.group(1), "int")
            if name_match
            else "int"
        )
        # Embed the sentinel forward decl *inside* the stub body so the
        # stripped TU stays self-contained (no top-level injection
        # required, no header-file changes).  Watcom 10.0a accepts a
        # function-scope ``extern`` declaration without complaint.
        #
        # The sentinel takes the stub's PS.EXE address as an int
        # discriminator: this gives every stub a unique compiled body
        # (each one starts with ``mov eax, <unique_imm>``), which
        # defeats Watcom 10.0a's identical-function folding.  Without
        # the discriminator the linker collapses every same-shape stub
        # to a single 16-byte landing pad — every stub would resolve
        # to the same address, so symbol references during byte-diff
        # would all hit one merged body and the per-stub layout PS.EXE
        # encodes is impossible to reproduce.
        # Each stub body writes the stub's PS.EXE address to a shared
        # ``volatile`` global, then returns 0 (or nothing, for void).
        # Three things matter for byte-equivalence with PS.EXE:
        #
        #   1. The store ``__stub_log = 0x<unique>`` produces a body
        #      that's unique per stub (different immediate), so the
        #      linker's identical-function folding pass can't collapse
        #      same-shape stubs into one landing pad.
        #   2. The body ends in an explicit ``ret`` (or ``xor eax, eax;
        #      ret``), *not* a tail-call to an external — this stops
        #      Watcom 10.0a from doing ``RetAftrCall``, and therefore
        #      stops the cross-function adjacency / fall-through
        #      optimisation that places the stub right after its only
        #      tail-caller and elides the intervening jmp.
        #   3. The store target (``__stub_log``) is ``volatile`` so
        #      Watcom can't elide it as dead.
        #
        # See the docstring of strip_stub_bodies() for the broader
        # rationale and the discovery commit message for the OW source
        # citations (RetAftrCall in optpush.c, Untangle1 in optins.c).
        if is_void:
            body = (
                "{ extern volatile int __stub_log; "
                f"__stub_log = 0x{stub_addr_hex}; "
                "}"
            )
        else:
            # Returning the stub's PS.EXE address (rather than 0) gives
            # every non-void stub a unique end-of-body byte sequence
            # (``mov eax, <unique_imm>; ret``).  This stops Watcom 10.0a
            # from merging the stub's epilogue with an adjacent
            # neighbour that happens to start with ``xor eax, eax``
            # (Rule 15 cross-function tail-merge).
            # Cast the literal to the return type — without it,
            # ``char foo() { return 0x2881B; }`` triggers W106
            # (constant out of range).  The low-byte distinctness
            # still gives Watcom enough material to keep the
            # compiled bodies unique at the per-stub scale we care
            # about (see Rule 15 / identical-function folding).
            body = (
                "{ extern volatile int __stub_log; "
                f"__stub_log = 0x{stub_addr_hex}; "
                f"return ({ret_type})0x{stub_addr_hex}; }}"
            )
        # Replace the brace block with the new non-inlinable body.
        rewritten = re.sub(
            r"\s*\{[\s\S]*\}\s*\n?",
            " " + body + "\n",
            joined,
            count=1,
        )
        result.append(rewritten)

    return "".join(result)


# ── Header generation ─────────────────────────────────────────────────────────

# CRT-managed data symbols that ship with the Watcom runtime.
# PS.EXE was statically linked, so the CRT data shows up in symbols.json,
# but redeclaring it conflicts with the real definitions in the standard
# headers (<stdlib.h>, <stdio.h>, <errno.h>, …).  Anything matching is
# omitted from c2_data.h — use the proper #include in the .c file instead.
_CRT_DATA_SYMBOLS: frozenset[str] = frozenset({
    "errno", "environ",
    # stdio.h
    "stdin", "stdout", "stderr",
    # iostream extras seen in some headers (mostly C++)
    "cin", "cout", "cerr", "clog",
    # <time.h> globals — owned by clib3r.lib (tzset/localtime modules).
    # PS.EXE's data segment carries them, but the same linked CRT supplies
    # them, so we neither define nor redeclare them (no game code references
    # them).  Dropping our datainit.c copies lets the library own them.
    "timezone", "daylight", "tzname",
    # Miles (AIL) library data globals — provided by the AIL runtime, never
    # referenced by our decompiled code.  Only the AIL *functions* (declared
    # in ail.h) are called; these data symbols are pure import clutter.
    "AIL_driver", "AIL_error", "AIL_last_IO_attempt", "AIL_preference",
})


# Manual overrides where size-based heuristic picks the wrong C type.
_TYPE_OVERRIDES: dict[str, tuple[str, str] | None] = {
    # LZHUF bit-buffer (pump.c).  PS used Okumura/Yoshizaki's 16-bit MSDOS
    # LZHUF.C (Borland/Turbo-C, alloc.h, int==16-bit), where `unsigned getbuf`
    # was a 16-bit value.  Ported to 32-bit Watcom it is `unsigned short`:
    # every access is `word ptr`/`mov ax`, and this is what makes the refill
    # shift count zero-extend in 16-bit (`xor ch,ch`) and GetByte read it
    # unsigned (`and eax,0xffff`).  Verified byte-exact against the published
    # source (see docs/codegen-experiments/get_bit_natural.py).
    "getbuf":                ("unsigned short", ""),
    # LZHUF output bit-buffer — same 16-bit `unsigned` as getbuf (USHORT).
    "putbuf":                ("unsigned short", ""),
    # Byte tables whose size happens to be a multiple of 4
    # Per-house tile graphics LUT — byte-stride access
    # (`mov bl, byte ptr [house_gfxdat+0x64]` in reduce_villa_to_domus).
    "house_gfxdat":          ("unsigned char", "[]"),
    # Declared in entities.h as struct wall_gfx_rec; wall_gfxdat spans the
    # adjacent aquaduct_gfxdat table for tile ids 0xC1..0xD4.
    "wall_gfxdat":           None,
    "aquaduct_gfxdat":       None,
    "sailable_sea":          ("unsigned char", "[]"),
    # 8-byte direction LUT — byte-stride access in get_wf_dirc
    # (`mov dl, [esi + wf_battle_dircs]`).
    "wf_battle_dircs":        ("signed char", "[]"),
    # House-quality level: PS reads it with `movsx` everywhere (signed
    # promotion-level, can go negative).  Declared `char` (unsigned in this
    # build) forced `(signed char)q_lv` casts at every read site; declaring
    # it `signed char` lets direct reads re-load it signed, matching PS's
    # inline-global movsx pattern in show_query_house_advice / get_query_info.
    "q_lv":                   ("signed char", ""),
    "events": None,
    # Message queue: array of {int msg; int param} (struct msg_slot in
    # entities.h).  Was declared int[] and cast (struct msg_slot *)&message_list
    # at every accessor; typed correctly here so accessors index directly.
    "message_list":           ("struct msg_slot", "[]"),
    # Smacker video filename table, defined in message.c as char[40][14].
    # Auto-derived type was int[]; the mismatch is tolerated by 10.0a but
    # rejected by Watcom 9.x (E1129).  Declare it to match the definition.
    "smacks": ("char", "[40][14]"),
    # Text-rendering scratch pointer set by get_text_pointer(); used as
    # a char* throughout lib32/controls.
    "text_pointer": ("char *", ""),
    # Backing-store screen buffer allocated by init code; used as
    # an unsigned-char[] buffer everywhere (readfile, copy, indexed
    # zero-out loops, greyscale conversion).  PS source had this as
    # a pointer, not int.
    "internal_screen": ("unsigned char *", ""),
    # Heap-allocated data-blob pointers (4-byte slot each, set by
    # the loader from disk).  Every consumer does
    # '((unsigned char *)X)[idx + N]' — the cast is pure noise.
    # PS source declared these as 'unsigned char *X;'.
    "fixt_data":         ("unsigned char *", ""),
    "people_data":       ("unsigned char *", ""),
    "house_data":        ("unsigned char *", ""),
    "building_data1":    ("unsigned char *", ""),
    "building_data2":    ("unsigned char *", ""),
    "building_data3":    ("unsigned char *", ""),
    "building_data4":    ("unsigned char *", ""),
    "tops_data":         ("unsigned char *", ""),
    # Shared scratch buffer allocated by init_general; passed by
    # address-of to many APIs and accessed via SCRATCH_BUFFER /
    # SCRATCH_BYTES / SCRATCH_CHARS macros in c2_types.h.  PS
    # source had this as 'unsigned char *' (the macros wrap it).
    "scratch_buffer":    ("unsigned char *", ""),
    # Per-figure sprite-data pointers loaded by
    # load_a_battle_gfx_file() and consumed by build_units_figures /
    # create_arrow via figure_rec.arrow_data_ptr +
    # arrow_rec.arrow_data_ptr.  4-byte slots holding heap pointers.
    "figure1_data":      ("unsigned char *", ""),
    "figure2_data":      ("unsigned char *", ""),
    "figure3_data":      ("unsigned char *", ""),
    "figure4_data":      ("unsigned char *", ""),
    "figure5_data":      ("unsigned char *", ""),
    "figure6_data":      ("unsigned char *", ""),
    "figure7_data":      ("unsigned char *", ""),
    "figure8_data":      ("unsigned char *", ""),
    "figure9_data":      ("unsigned char *", ""),
    "figure10_data":     ("unsigned char *", ""),
    # Pointer to the filename of the currently-loaded Smacker video;
    # set by show_smacker, consumed by cd_path(char *) and the RAD
    # SMACKOPEN ABI.
    "smack_filename":    ("char *", ""),
    # 8-byte rolling hotkey/cheat-code buffer in hotkeys.c.  Debug data
    # `old_key_buffer` is a `char *` in PS, not a `char[]`.  The fixup
    # at this slot points at an unnamed 9-byte data-segment buffer
    # holding "        \0".  hotkeys.c owns both the buffer and the
    # pointer (`static char old_key_buf[9] = "        "; char
    # *old_key_buffer = old_key_buf;`) so callers can keep their
    # natural `old_key_buffer[i]` / `strcmp(old_key_buffer, ...)` use.
    "old_key_buffer":    ("char *", ""),
    # Active ferret/pathfinding map base; common.c treats it as a
    # byte-addressed map buffer (city_map / region_map / battle_map).
    "ferret_map":        ("unsigned char *", ""),
    # 48-byte static buffer filled by DPMI int 0x31 fn 0x500.
    # get_dos_memory writes r.x.edi = memory then reads the result
    # via '*(int *)((char *)memory + 0x1c)'.  PS source had this as
    # a fixed-size unsigned char buffer.
    "memory":            ("unsigned char", "[48]"),
    # Current city-map cell pointer used by evolver.c.  The symbol is a
    # data pointer; byte-wise arithmetic matches city_map's 20-byte cells.
    "city_qptr": ("unsigned char *", ""),
    # Tiny numeric suffix strings used by controls.c::font_no calls.
    "data_000AEC": ("char", "[]"),
    "data_000AEF": ("char", "[]"),
    "data_000AF1": ("char", "[]"),
    # 200 short entries (400 bytes) — PS uses `movsx eax, word ptr
    # [ebx*2 + help_history]` in rewind_help_history.
    "help_history":           ("short", "[]"),
    "svga_refresh_table": ("char", "[]"),
    # svga_refresh_data is declared as `struct svga_cell
    # svga_refresh_data[1200]` in entities.h — skip the
    # auto-generated `int[]` extern.
    "svga_refresh_data": None,
    # 4 huts × 3 bytes (kind, x, y).  put_a_hut/clear_huts/save_huts
    # all read byte-at-a-time.
    "hut_list": None,
    # Tutorial-page filenames table.  14 bytes per entry
    # (page * 7 * 2), confirmed by act_back_tutorial_page:
    # Tutorial file tables — 32 records × 14-byte fixed filename.
    "tut_files": None,
    "tut_palfiles": None,
    # 10×10 grid of fire-zone intensity bytes; clear_fire_zones
    # walks it via `eax = x*10 + y` byte offsets.
    "fire_zones": ("signed char", "[]"),
    # Read via `movsx` in garden_an_area / clear_basic / etc.
    "stone_random_count": ("signed char", ""),
    # Random-byte table indexed by stone_random_count;
    # garden_an_area / clear_basic load via 1-byte stride.
    "stone_random_data": ("unsigned char", "[]"),
    "positive_buffer": ("char", "[]"),
    "negative_buffer": ("char", "[]"),
    "button_speed_profile": ("char", "[]"),
    # 4 skill rows × 4 trouble-type columns, declared in entities.h.
    "skill_to_trouble_honeymoons": None,
    "skill_to_trouble_frequency":  None,
    "skill_to_trouble_debar":      None,
    "sample_buffer": None,
    "db_file": None,
    "speech_filaname": None,
    "lang_file": None,
    "media_file": None,
    "speech_files": None,
    "text_buf": None,
    "lson": None,
    "rson": None,
    "dad": None,
    "freq": None,
    "prnt": None,
    "son": None,
    "refresh_bank_switch_data": None,
    "forum_menu": None,
    "pmp_inbuff": None,
    "pmp_outbuff": None,
    # 256-byte palette → grayscale lookup built by grey_a_screen and read
    # one-byte-at-a-time when applying the greyscale filter.
    "greying_data": ("unsigned char", "[256]"),
    # 1300-byte directory listing: 100 entries × 13 bytes/name (DOS 8.3
    # name + null).  Read byte-at-a-time from _dos_findfirst/findnext
    # buffer offset 0x1e in get_directory.
    "directory": ("char", "[]"),
    # 5-int lookup tables for skill-tier scaling.  Size 21 includes
    # one trailing alignment byte that confuses the auto-sizer; PS
    # reads via `mov edx, [eax*4 + base]` (DWORD stride).
    "skill_to_denarii_reduction": ("int", "[5]"),
    # Army state / intelligence dispatch tables: declared as
    # `void (*[N])(void)` in entities.h — LE fixups confirm every entry
    # is a function pointer at an entry point
    # (sa00_null…sa16_army_lurk_round_coast / a00_null…a08_raider_ship).
    # Four 28-byte arrow-sprite offset tables also declared in
    # entities.h as `signed char[28]` (Watcom reads them with
    # `movsx ecx, byte ptr [base + idx]`).  Auto-sizer would have
    # emitted these as int[7] (28 bytes / sizeof(int)) because no
    # element-type hint is available from symbols.json alone.
    # getlen is a single byte but the next symbol (dummy_sav) is at
    # +3 due to alignment padding, so the auto-sizer infers 3 bytes
    # → "char getlen[]".  Pin it as a scalar so GetBit / Putcode can
    # do `getlen <= 8` and `getlen += 8` without lvalue errors.
    "getlen": ("char", ""),
    # c2inf is 64-byte settings record; declared as
    # `extern struct c2inf_rec c2inf` in entities.h.
    "c2inf": None,
    # request_message is a 0x68-byte mixed-purpose control block;
    # declared as `extern struct request_message request_message`
    # in entities.h.
    "request_message": None,
    # city_map is 80x80 cells * 20 bytes/cell = 128_000.
    # Declared as `extern struct city_cell city_map[6400]` in entities.h.
    "city_map":   None,
    # region_map is 60x60 cells * 8 bytes/cell = 28_800.
    # Declared as `extern unsigned char region_map[...]` in entities.h
    # along with REGION_W/REGION_H/REGION_CELL_BYTES dimension defines
    # and the RM_* field-access macros.  PS source used the byte-array
    # form (zero word/dword accesses across 84 instruction-level refs).
    "region_map": None,



    # Battle AI/animation byte tables (PS reads as char[]).
    "tribe_ai_data":      None,
    "river_data":         None,
    "road_data":          None,
    "wall_data":          None,
    "tower_data":         None,
    "gateway_data":       None,
    "gateway2_data":      None,
    "wallaqua_data":      None,
    "aquawall_data":      None,
    "aquaroad_data":      None,
    "aquaduct_data":      None,
    "regwallroad_data":   None,
    "resevoir_data":      None,
    "coast_data":         None,
    "rotated_map":        None,
    "rotated2_map":       None,
    "init_salary":        None,
    "temp_route":         None,
    "gmn_ofsets":         None,
    "elephant_stampede":  None,
    "help_redir_ent_history": None,
    "house_lv_effect":    None,
    "forum_lv_effect":    None,
    "temple_lv_effect":   None,
    "house_evolution":    None,
    "well_evolution":     None,
    "fountain_evolution": None,
    "baths_evolution":    None,
    "forum_evolution":    None,
    "temple_evolution":   None,
    "temple_populations1": None,
    "temple_populations2": None,
    "temple_populations3": None,
    "house_type_to_unrest": None,
    "stretch_ofsets_2x2": None,
    "stretch_ofsets_3x3": None,
    "directory": None,
    "vesa_info": None,
    "vesa_mode_info": None,
    "card_ids": ("char", "[]"),
    "rotated_bank0":  ("unsigned char", "[]"),
    "rotated_bank1":  ("unsigned char", "[]"),
    "rotated_bank2":  ("unsigned char", "[]"),
    "rotated_bank3":  ("unsigned char", "[]"),
    "rotated_bank4":  ("unsigned char", "[]"),
    "rotated2_bank0": ("unsigned char", "[]"),
    "rotated2_bank1": ("unsigned char", "[]"),
    "rotated2_bank2": ("unsigned char", "[]"),
    "rotated2_bank3": ("unsigned char", "[]"),
    "mice":           ("unsigned char", "[]"),
    "forum_gfxdat":   ("unsigned char", "[]"),
    "lf_tiles":       ("unsigned char", "[]"),
    "p_len":          ("unsigned char", "[]"),
    "p_code":         ("unsigned char", "[]"),
    "d_len":          ("unsigned char", "[]"),
    "d_code":         ("unsigned char", "[]"),
    "promotion_levels": None,
    "promotion_av_levels": None,
    "province_completion_to_promotion": None,
    # init_slave_data is the tail of the same per-difficulty welfare/slave
    # table; suppress the duplicate declaration in favour of init_salary[].
    "init_slave_data":    None,
    "line_flank_data":    None,
    "col_flank_data":     None,
    "putouts1":           None,
    "putouts2":           None,
    "putouts3":           None,
    "putouts4":           None,
    "fire_offs":          None,
    "walking_x_ofsets_zoom0": None,
    "walking_y_ofsets_zoom0": None,
    "walking_x_ofsets_zoom1": None,
    "walking_y_ofsets_zoom1": None,
    "walking_x_ofsets_zoom2": None,
    "walking_y_ofsets_zoom2": None,
    "fig_walking_x_ofsets_z1": None,
    "fig_walking_y_ofsets_z1": None,
    "fig_walking_x_ofsets_z2": None,
    "fig_walking_y_ofsets_z2": None,
    "arena_top_data":     None,
    "colos_top_data":     None,
    "attack_pos_data":    None,
    "losses_to_morale":   ("unsigned char", "[]"),
    # Per-zoom graphics-table arrays (filename+size records); declared
    # in entities.h as struct gfx_entry.
    "c2_map_gfx": None,
    "c2_overlay_gfx": None,
    "c2_battle_gfx": None,
    "c2_battle_aux_gfx": None,
    # Menu table — declared as struct menu_rec in entities.h.
    "main_menu": None,
    # Help/media records — declared as structs in entities.h.
    "this_media_entry": None,
    "help_page_hot_spots": None,
    "media_line_buffer": ("char", "[]"),
    # Save/load entry tables — declared as struct save_entry in entities.h.
    "savegame_entries": None,
    "model_entries": None,
    # Function-pointer dispatch tables; declared in entities.h.
    "city_actions": None,
    "region_actions": None,
    # UI/build selection descriptor arrays (0x14-byte records); declared
    # as `extern struct selection_rec ...[]` in entities.h.
    "ovmap_selection": None,
    "rm_security_selection": None,
    "rm_industry_selection": None,
    "education_selection": None,
    "entertainment_selection": None,
    "farm_selection": None,
    "forum_selection": None,
    "gardens_plaza_selection": None,
    "health_selection": None,
    "houses_selection": None,
    "industry_selection": None,
    "mine_selection": None,
    "quarry_selection": None,
    "security_selection": None,
    "temple_selection": None,
    "water_selection": None,
    # UI button descriptor arrays (0x18-byte records); declared as
    # `extern struct button_rec ...[]` in entities.h.
    "confirming_buttons": None,
    "help_buttons": None,
    "queery_buttons": None,
    "query_buttons2": None,
    "adjusting_buttons": None,
    "skill1_buttons": None,
    "skill2_buttons": None,
    "exit_buttons": None,
    "loadsave_buttons": None,
    "tunes_buttons": None,
    "samples_buttons": None,
    "tog_anims_buttons": None,
    "tog_yearend_buttons": None,
    "promotion_buttons": None,
    "request_buttons": None,
    "goto_mess_buttons": None,
    "admin_buttons": None,
    "career_buttons": None,
    "donation_buttons": None,
    "clerk_buttons": None,
    "army_buttons": None,
    "cohort_buttons": None,
    "mercenary_buttons": None,
    "slave1_buttons": None,
    "slave2_buttons": None,
    "rome1_buttons": None,
    "rome2_buttons": None,

    # Landfill sprite bank is byte-packed: 16-byte descriptors followed by pixels.
    "landfill": ("unsigned char", "[]"),
    # City minimap/help entry table is read as 16-bit words.
    "city_mm_enties": ("short", "[]"),
    # Region aqueduct graphics metadata is a 12-byte byte table; +8 is footprint.
    "reg_aquaduct_gfxdat": ("char", "[]"),
    # Per-cell landfill kind (80×80 cells, 1 byte each).
    "landfill_pool": ("char", "[]"),
    # Diamond stamp offsets for region drawing — small byte tables
    # (4 / 9 / 16 entries for 2×2 / 3×3 / 4×4 stamps).  PS reads via
    # `mov dl, byte ptr [eax + diamond_ofsets_2x]` (byte-stride scan).
    "diamond_ofsets_2x": ("char", "[]"),
    "diamond_ofsets_3x": ("char", "[]"),
    "diamond_ofsets_4x": ("char", "[]"),
    # gmn — global match-needs flag table.  16-byte size; choose_from
    # / init_choices / invert_gmn read/write byte-at-a-time via
    # `cmp byte ptr [eax + gmn], 0` and `mov byte ptr [eax + gmn], al`.
    "gmn": ("char", "[]"),
    # Empire / tribe lookup tables — size-not-multiple-of-4 strides
    # (4 bytes per province for region_borders, 7 bytes per tribe for
    # tribe_battle_setup, 10 bytes per province for region_sources, …)
    # All accessed as char arrays in PS.EXE.
    "region_borders":         None,
    "empire":                 ("unsigned char", "[]"),
    "region_sources":         None,
    "tribe_type":             ("char", "[]"),
    "tribe_battle_setup":     None,
    "tribe_to_troops":        ("char", "[]"),
    "tribe_to_troop_numbers": None,
    # Per-tribe lookup giving the standard sprite (1 byte each, indexed
    # by army.tribe_id at +0x9D).  Read in get_enemy_image via
    # `mov dl, byte ptr [edx + tribe_to_standard]`.
    "tribe_to_standard":      ("unsigned char", "[]"),
    # web[] is declared in entities.h as ``struct web_node web[]``;
    # skip the auto-generated extern.
    "web":        None,
    # Struct/array anchors accessed as a scalar (first-field only)
    "ss_entries": None,
    # 10-int startup parameter table (data.c, 40 bytes at data+0x65f9):
    # {7, 20, 80, 40, 20, 4, 0, 0, 0, 0}.  Read by formulae.c as
    # main_paras[1] = regular-cohort baseline, [2..4] = recruit caps
    # (aux/irr/reg), [5] = imperial_tax reset base.
    "main_paras": ("int", "[10]"),
    # Per-message-id goto-map flag table (data.c, 60 bytes at data+0x3e60):
    # 1 = the message's goto target is on the REGION map, 0 = city map.
    # Indexed as mess_goto_map[msg - 80] (message ids start at 80; Watcom
    # folds the -80 into the base address, so PS carries no direct xref).
    "mess_goto_map": ("unsigned char", "[]"),
    # `adjust_var` holds a *pointer* to the variable currently bound to the
    # adjust dialog; act_adjust_up/_down deref it directly (mov edx, [eax]).
    "adjust_var": ("int *", ""),
    # `key_ascii` is a 1-byte scalar (per PS debug info; the next 27
    # bytes are unnamed adjacent buffer used as a kbd shadow). The
    # auto-derived size is 28 (distance to next named symbol
    # `svga_refresh_data`), but data.asm shows `db 1 dup(?)` here.
    # PS reads it via `xor eax,eax; mov al, [key_ascii]; cmp eax, …`
    # so the C type must be a byte scalar. Same shape as the sibling
    # `key_ascii_was`, `key_code`, `key_ready` (all 1-byte char).
    "key_ascii":  ("char", ""),
    # `extension` is a 4-byte file-extension buffer (3 chars + null),
    # used in lib32.c as `extension[0..3]`. Auto-derived size of 4
    # would give `int`, but the access pattern is char-based.
    "extension":  ("char", "[4]"),
    # Per-citizen-type movement speed lookup (8 entries, signed —
    # PS reads via movsx).  citizen_go_to_target uses these as
    # `int speed_max = citizen_speed_on_road[type]`.  Default `char`
    # is unsigned in Watcom 10.0a, so explicitly mark as signed.
    "citizen_speed_on_road":  ("signed char", "[]"),
    "citizen_speed_off_road": ("signed char", "[]"),
    # 17 short slots cleared via STOSB (size 0x22 / sizeof(short) = 17),
    # accessed by check_highlight_list via word_ptr.  Size in symtab is
    # 36 (padded) but the type is short[].
    "highlight_goods_list": ("short", "[]"),
    "selection_goods_list": ("short", "[]"),
    "empire_flag_positions": None,
    # Icon-header tables — 232 shorts each (size 0x1D0 = 464 bytes),
    # accessed in action.c get_icon_over with stride 16 (8 shorts per
    # icon: x, y, w, h plus 4 trailing fields).  Auto-derived `int[]`
    # type is wrong; PS reads via `mov ax, word ptr [...]`.
    "int_battle_header": ("unsigned short", "[]"),
    "int_city_header":   ("unsigned short", "[]"),
    "int_region_header": ("unsigned short", "[]"),
    # Per-army patrol-route table — stride 0x20 bytes per army; fields
    # at +0x00 (int target_ptr), +0x0c..0x0f (4 chars: army_x/y, over_x/y),
    # +0x10..+0x12 (clear-to-zero waypoints), +0x1a..+0x1b (saved coords).
    # Auto-derived `int[]` is wrong; PS reads via byte/dword pointer
    # arithmetic rooted at a `char *` cast.  Until we name the record
    # type, expose as raw `char[]`.
    "army_routes": None,
    # Ambient-sound list — per-slot 70-byte records; struct ambient_rec
    # is declared in entities.h.
    "ambient_list": None,
    # battle_map is 52x52 cells * 4 bytes/cell = 10_816.
    # Declared as `extern unsigned char battle_map[...]` in entities.h
    # along with BATTLE_W/BATTLE_H/BATTLE_CELL_BYTES dimension defines
    # and the BM_* field-access macros.
    "battle_map": None,
    # pseudo_map is the isometric projection of city_map: 161 rows
    # of 81 int cells (4 bytes each = 52 164 bytes total).  Each
    # cell is a tagged-union dword: either a sprite marker
    # (>= PM_SPRITE_TAG) or a raw cm_ptr byte offset into city_map.
    # Declared as `extern int pseudo_map[PM_H][PM_W]` (2D) in
    # entities.h — see comment there for why 2D matches PS
    # codegen and 1D doesn't.
    "pseudo_map": None,
    # lib32.c byte-array globals — accessed with `name[i]` byte
    # indexing (see swap_background_to_red, set_palette, format-buffer
    # text routines).  Auto-derived `int[]` makes Watcom emit dword
    # loads instead of byte loads, breaking byte-equivalence with
    # PS.EXE.  Match the access pattern: `char[]`.
    "current_palette":   ("char", "[]"),
    "temp_palette":      ("char", "[]"),
    "format_buffer":     ("char", "[]"),
    "text_buffer":       ("char", "[]"),
    "insert_text":       ("char", "[]"),
    "mouse_background":  ("char", "[]"),
    "path_name":         ("char", "[]"),
    "cbd":               None,           # deferred-mouse callback buf (struct mouse_cbd in entities.h)
    "smk":               None,           # struct smk_handle * in smacker.h
    "VesaInfo":          ("struct dpmi_real_block", ""),
    "VesaModeInfo":      ("struct dpmi_real_block", ""),
    "memory":            ("struct dpmi_mem_info", ""),
    # Per-letter sprite-index lookup (224 bytes, indexed by
    # `letter - 0x20`).  PS reads via `mov al, [letter_table - 0x20 + letter]`
    # zero-extended; default `int[]` would force dword loads.
    "letter_table":      ("unsigned char", "[]"),
    # Empire-screen icon coordinates — 176 bytes = 88 shorts, two
    # shorts per region (x, y).  Auto-derived `int[]` is wrong;
    # empire map province positions are 44 x/y short pairs.
    "empire_positions":  None,
    # LFSR seeds for big_random / scatter — used with logical right
    # shift (`>> 1`), so must be `unsigned int` to compile as `shr`
    # rather than `sar`.  Auto-derived `int` is wrong.
    "randseed":  ("unsigned int", ""),
    "scatseed":  ("unsigned int", ""),
    # `slave_requirements` is owned by formulae.c which defines it
    # as `struct slave_req[8]` (8 classes × {int current; int max}).
    # The struct lives in entities.h.  Suppress the auto-generated
    # extern so c2_data.h doesn't double-declare.
    "slave_requirements": None,
    # Char scalars whose gap to next symbol > 1
    "warned_of_cutbacks": ("char", ""),
    "web_directions":     ("char", ""),
    # Byte arrays that happen to be 4 bytes (not int)
    "empire_connections": ("char", "[4]"),
    # Palettes — passed to set_palette(char *).  Auto-derived int[].
    "city_palette":          ("char", "[]"),
    "region_palette":        ("char", "[]"),
    "black_out_data":        ("char", "[]"),  # 768-byte all-zero palette
    # NOTE: scratch_buffer is a pointer-stored-as-int — lib32.c
    # init code does `scratch_buffer = (int)malloc(...)`.  Cannot be
    # an array.  Auto-derived `int` is correct; W113 at call sites
    # (passing int to char *) handled with `(char *)scratch_buffer`
    # casts at use sites instead.
    # `misc` is the small per-screen UI sprite buffer; passed to
    # write_image(unsigned char *).  Default int[] mismatches.
    "misc":                  ("unsigned char", "[]"),
    "system_panel":          ("unsigned char", "[]"),
    "game_panels":           ("unsigned char", "[]"),
    "logos":                 ("unsigned char", "[]"),
    "font1":                 ("unsigned char", "[]"),
    "font2":                 ("unsigned char", "[]"),
    # Double-buffered AIL streaming sample chunks; stores two pointers into
    # scratch_buffer, not integer sample data.
    "db_buf":                ("unsigned char *", "[]"),
    # 27,500-byte MDI sequence staging area loaded from disk and handed to AIL.
    "tune_buffer":           ("unsigned char", "[]"),
    # Entity lists — declared with struct types in entities.h
    "figure_list": None,
    "citizen_list": None,
    "unit_list": None,
    "arrow_list": None,
    # Empire / mercenary tables — also declared as struct arrays in
    # entities.h.  province_industries[8].{kind,is_trader,...},
    # mercenary_type[44].{mercs_from,category,max_allowed,cost_per_50,...}.
    "province_industries": None,
    "mercenary_type":      None,
    "industry":            None,
}


def _size_to_type(size: int) -> tuple[str, str]:
    """(base_type, array_suffix) from byte size."""
    if size == 1:
        return "char", ""
    if size == 2:
        return "short", ""
    if size == 4:
        return "int", ""
    if size % 4 == 0:
        return "int", "[]"
    return "char", "[]"


def _compute_sizes(data_syms: list[dict]) -> dict[str, int]:
    """Symbol name → byte size, from adjacent offsets within each segment."""
    by_seg: dict[int, list[dict]] = defaultdict(list)
    for s in data_syms:
        by_seg[s["segment"]].append(s)
    sizes: dict[str, int] = {}
    for seg_syms in by_seg.values():
        seg_syms.sort(key=lambda s: s["offset"])
        for i, s in enumerate(seg_syms):
            size = (
                seg_syms[i + 1]["offset"] - s["offset"]
                if i + 1 < len(seg_syms)
                else 4
            )
            if size > 0:
                sizes[s["name"]] = size
    return sizes


def _find_owned_definitions(src_dir: Path) -> set[str]:
    """Find file-local *static* variable names defined in any .c file.

    These cannot be referenced across translation units, so the header
    generator must not emit an `extern` for them (Watcom would complain
    about a static/extern conflict).

    Non-static globals defined in a .c file (e.g. those harvested into
    `datainit.c` by `c2 data-init`) still need an extern decl in
    c2_data.h so other TUs can reference them, so they're deliberately
    not included here.
    """
    owned: set[str] = set()
    for path in src_dir.glob("*.c"):
        try:
            src = path.read_text(errors="replace")
            ast = parse_c(src, path.name)
        except pycparser.c_parser.ParseError:
            continue
        for node in ast.ext:
            if (
                isinstance(node, c_ast.Decl)
                and node.name
                and "extern" not in (node.storage or [])
                and "static" in (node.storage or [])
                and not isinstance(node.type, c_ast.FuncDecl)
            ):
                owned.add(node.name)
    return owned


def _find_hand_header_externs(include_dir: Path) -> set[str]:
    """Find data symbols already declared in hand-written headers.

    Generated headers (c2_data.h / c2_funcs.h) are skipped so we can
    rebuild them cleanly; everything else under decomp/include is
    treated as the source of truth for typed extern declarations and
    the generator must not duplicate those symbols with auto-inferred
    char[]/int[] types.
    """
    skip = {"c2_data.h", "c2_funcs.h"}
    names: set[str] = set()
    for path in include_dir.glob("*.h"):
        if path.name in skip:
            continue
        try:
            ast = parse_c(path.read_text(errors="replace"), path.name)
        except pycparser.c_parser.ParseError:
            continue
        for node in ast.ext:
            if (
                isinstance(node, c_ast.Decl)
                and node.name
                and "extern" in (node.storage or [])
                and not isinstance(node.type, c_ast.FuncDecl)
            ):
                names.add(node.name)
    return names


# Functions that must NOT appear in c2_funcs.h so callers fall back to
# C89's implicit-int rule (Rule 37 in docs/watcom-codegen-patterns.md).
#
# These functions are declared as a narrower-than-int return type
# (`char` / `signed char` / `unsigned char`) in their defining TU,
# but PS.EXE's call sites emit `test eax, eax` rather than `test al,
# al` because the original PS source apparently didn't have a
# prototype visible at the call site.  When the prototype IS visible,
# Watcom emits the narrower test, breaking byte-exact verification at
# every caller.  Excluding the function from c2_funcs.h restores PS's
# call-site shape.
_IMPLICIT_INT_FUNCTIONS: set[str] = {
    "colour_cycle_delay1",
    "colour_cycle_delay2",
    # click_handler is an `__interrupt __far` mouse-driver callback.
    # pycparser drops those modifiers when building the c2_funcs.h
    # prototype, so emitting a header decl would conflict with the
    # definition (`Modifiers disagree`).  install_mouse takes its
    # address through a file-local forward decl in lib32.c.
    "click_handler",
    # get_heading's body reads arg5 as `mov al, byte ptr [esp+0xc]`
    # (8-bit), so the def must be `char mode`.  But its 2 callers
    # (sa08_army_stuck, sa13_army_sail_round_coast) pass a
    # `signed char` field via `movsx edx, byte ptr [...]; push edx`.
    # When the prototype is visible with `char mode`, Watcom emits
    # `xor edx, edx; mov dl, byte; push edx` instead, breaking the
    # caller-side byte-exact match.  Excluding from c2_funcs.h lets
    # callers fall back to implicit-int (Rule 37) so they keep
    # using `movsx` per the C89 default-promotion rules.
    "get_heading",
}


# Functions defined with `__cdecl` storage — detected by a regex over
# the raw source text (pycparser strips Watcom keywords before parsing
# so the AST has no record of them).  Used by `generate_header` to
# re-emit the `__cdecl` qualifier on the extern decl so callers see
# the same calling convention as the definition.
# Any non-default calling convention placed directly before a function
# name (definition or declaration).  Used to re-insert the qualifier on
# generated c2_funcs.h prototypes so they agree with the defining TU
# (e.g. smacker.c's `void __pascal radfree(...)`).  __watcall is the
# project default and never needs re-emitting.
_CONV_DEF_RE = re.compile(
    r"\b(?P<conv>__cdecl|__pascal|__fortran|__stdcall|__fastcall|__syscall)"
    r"\b\s+(?P<name>[A-Za-z_]\w*)\s*\(",
)

_CDECL_DEF_RE = re.compile(
    r"\b__cdecl\b\s+(?P<name>[A-Za-z_]\w*)\s*\(",
)


def _scan_cdecl_functions(src_dir: Path) -> set[str]:
    """Return the set of function names declared with `__cdecl` in any
    .c file under `src_dir`.  Both forward decls and definitions are
    scanned, so a name appears whether the qualifier is on the proto,
    the body, or both."""
    out: set[str] = set()
    for path in sorted(src_dir.glob("*.c")):
        try:
            text = path.read_text(errors="replace")
        except OSError:
            continue
        for m in _CDECL_DEF_RE.finditer(text):
            out.add(m.group("name"))
    return out


def _scan_convention_functions(src_dir: Path) -> dict[str, str]:
    """Map function name → non-default calling-convention keyword for any
    function defined or declared with one (``__pascal``, ``__fortran``,
    ``__stdcall`` …) in the .c sources.  The qualifier must be re-inserted
    on the generated c2_funcs.h prototype so it agrees with the defining
    TU; otherwise Watcom raises E1057 (modifiers disagree).  ``__cdecl``
    is also covered here but kept in the dedicated scanner for back-compat.
    """
    out: dict[str, str] = {}
    for path in sorted(src_dir.glob("*.c")):
        try:
            text = path.read_text(errors="replace")
        except OSError:
            continue
        text = _BLOCK_COMMENT_RE.sub("", _LINE_COMMENT_RE.sub("", text))
        for m in _CONV_DEF_RE.finditer(text):
            out.setdefault(m.group("name"), m.group("conv"))
    return out


def _collect_function_definitions(
    src_dir: Path,
    *,
    include_stubs: bool = False,
) -> list[tuple[str, c_ast.Decl]]:
    """Walk every .c file in `src_dir` and collect non-static function
    definitions (FuncDef nodes).  Returns a list of (name, (file, Decl))
    pairs sorted by function name; the Decl is the func-decl half of
    the FuncDef and can be lowered to an `extern` declaration directly.

    A function is **canonical** (the source of truth) ONLY IF:
      * it lives at file scope (any .c in src_dir),
      * its storage class is not `static`,
      * its body is **non-empty** (i.e. a real decompilation, not a
        ``// STUB:``-marked empty body).

    Stub bodies (`{}`) are EXCLUDED by default because their
    signatures are auto-generated from `c2 decomp`'s heuristics
    (default `void X(void)`) and are frequently **wrong** — the
    real signature is what we'd see if the function had been
    decompiled.  When a stub's signature is wrong, hand-written
    per-file `extern` decls in callers may carry the corrected
    type; canonicalising the stub would clobber those corrections.

    Pass ``include_stubs=True`` to fold stubs in too — useful when
    you specifically want a directory-wide signature inventory and
    are willing to accept that stubs may carry bogus prototypes.
    """
    real: dict[str, tuple[str, c_ast.Decl]] = {}
    stub: dict[str, tuple[str, c_ast.Decl]] = {}
    for path in sorted(src_dir.glob("*.c")):
        try:
            src = path.read_text(errors="replace")
            ast = parse_c(src, path.name)
        except pycparser.c_parser.ParseError:
            continue
        for node in ast.ext:
            if not isinstance(node, c_ast.FuncDef):
                continue
            decl = node.decl
            if "static" in (decl.storage or []):
                continue
            name = decl.name
            body = node.body
            is_stub = (
                isinstance(body, c_ast.Compound)
                and (not body.block_items)
            )
            target = stub if is_stub else real
            target[name] = (path.name, decl)
    out: dict[str, tuple[str, c_ast.Decl]] = {}
    if include_stubs:
        out.update(stub)
    out.update(real)  # real always wins on name collision
    return sorted(out.items(), key=lambda kv: kv[0])


def _funcdef_to_extern_decl(decl: c_ast.Decl) -> c_ast.Decl:
    """Convert a FuncDef's Decl into an `extern fn(...)` declaration.

    The original Decl carries the function header (return type +
    parameter list) but with no `extern` storage class; we clone it
    with storage=['extern'] and strip any `init` / `bitsize` to
    produce a forward declaration that reads like:

        extern void foo(int x);
    """
    return c_ast.Decl(
        name=decl.name,
        quals=list(decl.quals or []),
        align=list(decl.align or []),
        storage=["extern"],
        funcspec=list(decl.funcspec or []),
        type=decl.type,
        init=None,
        bitsize=None,
    )


def _strip_decl_names(node):
    """Recursively clear `name` and `declname` fields on a type subtree
    so the generated text contains only types, not identifiers."""
    if node is None:
        return
    if hasattr(node, "declname"):
        node.declname = None
    if hasattr(node, "name") and isinstance(node, c_ast.Decl):
        node.name = None
    if isinstance(node, c_ast.Decl):
        _strip_decl_names(node.type)
    elif isinstance(node, c_ast.TypeDecl):
        # TypeDecl wraps an IdentifierType / Struct / etc.
        _strip_decl_names(node.type)
    elif isinstance(node, c_ast.PtrDecl):
        _strip_decl_names(node.type)
    elif isinstance(node, c_ast.ArrayDecl):
        _strip_decl_names(node.type)
    elif isinstance(node, c_ast.FuncDecl):
        _strip_decl_names(node.type)
        if isinstance(node.args, c_ast.ParamList):
            for p in node.args.params:
                _strip_decl_names(p)


def _normalise_fn_signature(decl: c_ast.Decl) -> str:
    """Normalise a FuncDecl for cross-file signature comparison.

    Strips `extern`, parameter names, and whitespace, leaving just
    the return type + parameter type list — so

        extern void foo(int param_1);
        void  foo(int x);

    both normalise to the same string ``"void foo(int)"``.
    """
    import copy as _copy
    if not isinstance(decl.type, c_ast.FuncDecl):
        return ""
    gen = _get_generator()
    fn_decl = _copy.deepcopy(decl.type)
    # Strip return-type's declname (set by pycparser to the fn name)
    if isinstance(fn_decl.type, c_ast.TypeDecl):
        fn_decl.type.declname = None
    elif isinstance(fn_decl.type, c_ast.PtrDecl):
        _strip_decl_names(fn_decl.type)
    # Strip parameter names
    if isinstance(fn_decl.args, c_ast.ParamList):
        for p in fn_decl.args.params:
            _strip_decl_names(p)
        param_types: list[str] = []
        for p in fn_decl.args.params:
            if isinstance(p, c_ast.Typename):
                param_types.append(gen.visit(p))
            elif isinstance(p, c_ast.Decl):
                bare_p = c_ast.Decl(
                    name=None, quals=[], align=[], storage=[],
                    funcspec=[], type=p.type, init=None, bitsize=None,
                )
                param_types.append(gen.visit(bare_p))
            elif isinstance(p, c_ast.EllipsisParam):
                param_types.append("...")
            else:
                param_types.append(gen.visit(p))
        joined = ", ".join(param_types).strip()
        if not joined:
            joined = "void"
    else:
        joined = "void"
    ret_decl = c_ast.Decl(
        name=None, quals=[], align=[], storage=[],
        funcspec=[], type=fn_decl.type, init=None, bitsize=None,
    )
    ret = gen.visit(ret_decl).strip()
    text = f"{ret} {decl.name}({joined})"
    return " ".join(text.split())


def _collect_per_file_fn_decls(src_dir: Path) -> dict[str, list[tuple[str, c_ast.Decl]]]:
    """Walk every .c file and collect file-scope function declarations
    (extern decls AND plain forward decls — both are FuncDecl nodes
    with no body).  Returns name -> list of (file, decl) pairs.
    """
    out: dict[str, list[tuple[str, c_ast.Decl]]] = {}
    for path in sorted(src_dir.glob("*.c")):
        try:
            src = path.read_text(errors="replace")
            ast = parse_c(src, path.name)
        except pycparser.c_parser.ParseError:
            continue
        for node in ast.ext:
            if (
                isinstance(node, c_ast.Decl)
                and isinstance(node.type, c_ast.FuncDecl)
                and node.name
            ):
                out.setdefault(node.name, []).append((path.name, node))
    return out


def _make_extern_decl(name: str, base_type: str,
                      array_suffix: str) -> c_ast.Decl:
    """Build an ``extern <type> <name><suffix>;`` AST node."""
    type_names = base_type.split()  # handles "signed char" etc.
    ident = c_ast.IdentifierType(type_names)
    type_decl = c_ast.TypeDecl(name, [], None, ident)

    if array_suffix:
        # Parse one or more dimensions from a suffix like "[]", "[4]",
        # or "[40][14]".  Nest ArrayDecls inner-to-outer so that
        # "[40][14]" yields char[40][14] (outer dim 40, inner dim 14).
        import re
        dims = re.findall(r'\[(\d*)\]', array_suffix) or ['']
        decl_type = type_decl
        for d in reversed(dims):
            dim = c_ast.Constant('int', d) if d else None
            decl_type = c_ast.ArrayDecl(decl_type, dim, [], None)
    else:
        decl_type = type_decl

    return c_ast.Decl(
        name=name,
        quals=[],
        align=[],
        storage=["extern"],
        funcspec=[],
        type=decl_type,
        init=None,
        bitsize=None,
    )


def generate_header_ast(src_dir: Path,
                        symbols_json: Path) -> c_ast.FileAST:
    """Build a FileAST for c2_data.h from symbols.json."""
    data = json.loads(symbols_json.read_text())
    data_syms = [s for s in data["symbols"] if s.get("is_data")]
    sizes = _compute_sizes(data_syms)
    owned = _find_owned_definitions(src_dir)
    # Hand-written headers (entities.h, smacker.h, c2_types.h, ...) are
    # the source of truth for typed extern decls; never re-emit those
    # symbols with the auto-inferred char[]/int[] shape.
    hand_externs = _find_hand_header_externs(src_dir.parent / "include")

    decls: list[c_ast.Decl] = []
    seen: set[str] = set()

    for s in sorted(data_syms, key=lambda s: s["name"]):
        name = s["name"]
        if name in seen or name in owned or name in hand_externs:
            continue
        # CRT-managed data symbols live in the static-linked Watcom
        # runtime that PS.EXE bundles.  These names collide with the
        # real declarations in <stdlib.h>, <stdio.h>, <errno.h>, etc.
        # We skip every leading-underscore symbol (no game code
        # references any of them — verified by grep), plus a few
        # un-prefixed CRT names like errno / environ.
        if name.startswith("_"):
            continue
        if name in _CRT_DATA_SYMBOLS:
            continue
        # Static (file-local) symbols cannot be referenced across translation
        # units; declaring them extern is incorrect and misleading.
        if s.get("is_static"):
            continue
        seen.add(name)

        size = sizes.get(name, 4)
        override = _TYPE_OVERRIDES.get(name)
        if override is None and name in _TYPE_OVERRIDES:
            continue  # explicitly excluded (e.g. struct-typed in entities.h)
        base, suffix = override or _size_to_type(size)
        decls.append(_make_extern_decl(name, base, suffix))

    return c_ast.FileAST(decls)


def _scan_asm_primitives(src_dir: Path) -> dict[str, str]:
    """Build a {name: canonical_extern_decl} map for every PUBLIC
    symbol in the hand-written .asm files (library.asm, sprites.asm,
    dia_ptrs.asm, dialarga.asm, dialargb.asm, dia_medi.asm,
    dia_smal.asm).  Watcom mangles __watcall public names with a
    trailing underscore (`place_2x2_block_`), which we strip to get
    the C-visible identifier.

    The signature is sourced from existing per-file `extern` decls
    in the .c files (since the .asm files themselves don't carry
    C signatures).  When multiple .c files declare the same primitive
    with different signatures, the most-info-rich form wins:
      * fewer-`void` params preferred over `(void)`,
      * higher arg count preferred,
      * pointer types preferred over `int` for the same arg count.

    Primitives that have NO per-file extern anywhere are skipped
    (they're either unused from C or referenced only via the asm
    side).  Add them manually to c2_data.h if a C caller ever needs
    a prototype.
    """
    asm_pubs: set[str] = set()
    for p in src_dir.glob("*.asm"):
        for line in p.read_text().splitlines():
            m = re.match(r"^PUBLIC\s+(\w+)_$", line.strip())
            if m:
                asm_pubs.add(m.group(1))

    extern_by_name: dict[str, list[str]] = defaultdict(list)
    for p in sorted(src_dir.glob("*.c")):
        text = p.read_text(errors="replace")
        for m in re.finditer(r"^extern\s+([^;{]+);", text, re.MULTILINE):
            decl = m.group(1).strip()
            nm = re.search(r"(?:\*\s*)?(\b[a-zA-Z_][\w]*)\s*(?:\(|\[|$)", decl)
            if not nm:
                continue
            name = nm.group(1)
            if name in asm_pubs:
                extern_by_name[name].append(re.sub(r"\s+", " ", decl))

    def _score(decl: str) -> int:
        if "(void)" in decl:
            return 0
        try:
            paren = decl[decl.index("("):]
        except ValueError:
            return 0
        nargs = paren.count(",") + 1
        has_ptr = "*" in paren
        return nargs * 10 + (5 if has_ptr else 0)

    # Known-conflicting primitives where different .c files call the
    # function with incompatible argument shapes (some pass typed
    # pointers, others pass int, others use the 0-arg implicit-int
    # form).  Adopting any single prototype would trigger E1071 /
    # E1151 at the conflicting call sites.  Skip c2_funcs.h emission
    # and leave per-file externs in charge for these.
    _ASM_PRIMITIVE_SIG_CONFLICTS = {
        "write_i_sprite",          # display.c (int) vs lib32.c (char*) vs pm_map1.c ()
        "write_i_left_sprite",     # same shape
        "write_i_right_sprite",    # same shape
        "place_16x16_block",       # int vs int* vs int (panel_addr)
        "place_32x32_block",       # int vs int*
    }

    canon: dict[str, str] = {}
    for name, decls in extern_by_name.items():
        if name in _ASM_PRIMITIVE_SIG_CONFLICTS:
            continue
        unique = list(set(decls))
        if len(unique) > 1:
            continue
        canon[name] = unique[0]
    return dict(sorted(canon.items()))


def generate_header(src_dir: Path, out_path: Path,
                    symbols_json: Path) -> None:
    """Generate the Caesar II compatibility header set.

    Emits two layers:

    * ``c2_data.h`` -- data externs only; safe to include without
      changing call prototypes.
    * ``c2_funcs.h`` -- optional canonical function prototypes.

    The historical ``caesar2.h`` umbrella header and ``c2macro.h``
    wrapper are no longer generated -- they were never #included from
    any source TU in the decompilation corpus and existed only as
    relic compatibility names.  ``out_path`` is kept in the signature
    for backwards compatibility but is not written.
    """
    ast = generate_header_ast(src_dir, symbols_json)
    gen = _get_generator()

    out_dir = out_path.parent
    data_path = out_dir / "c2_data.h"
    funcs_path = out_dir / "c2_funcs.h"

    data_lines = [
        "#ifndef C2_DATA_H",
        "#define C2_DATA_H",
        "",
        "/* Auto-generated — do not edit. Run: uv run c2 gen-header */",
        "/* Data externs only; safe to include without changing call prototypes. */",
        "",
        "/* Hand-written shared structs/macros (figure_list, city_map, ...). */",
        "#include \"c2_types.h\"",
        "",
        "/* ── Data externs (from symbols.json) ───────────────── */",
        "",
    ]

    for decl in ast.ext:
        data_lines.append(gen.visit(decl) + ";")

    data_lines += ["", "#endif /* C2_DATA_H */"]
    data_path.write_text("\n".join(data_lines) + "\n")

    fn_pairs = _collect_function_definitions(src_dir)
    per_file_decls = _collect_per_file_fn_decls(src_dir)
    cdecl_fns = _scan_cdecl_functions(src_dir)
    conv_fns = _scan_convention_functions(src_dir)

    funcs_lines = [
        "#ifndef C2_FUNCS_H",
        "#define C2_FUNCS_H",
        "",
        "/* Auto-generated — do not edit. Run: uv run c2 gen-header */",
        "/* Optional canonical function prototypes.  Do not include this layer",
        " * blindly when matching PS.EXE call-site prototype visibility. */",
        "",
        "#include \"c2_types.h\"",
        "",
        "/* ── Function externs (from decomp/src/*.c definitions) ── */",
        "",
        "/* Functions are emitted only when their definition signature",
        "   matches every per-file forward declaration that references",
        "   them.  Conflicts are listed in the section below — fix the",
        "   stub or the forward decl manually, then regenerate. */",
        "",
    ]

    conflicts: list[tuple[str, str, str, list[str]]] = []  # (name, def_sig, def_file, [conflicting])
    skipped_implicit: list[str] = []
    emitted_fn_count = 0
    for _name, (file, decl) in fn_pairs:
        if _name in _IMPLICIT_INT_FUNCTIONS:
            skipped_implicit.append(_name)
            continue
        def_sig = _normalise_fn_signature(_funcdef_to_extern_decl(decl))
        # Check every per-file forward decl for this function name
        bad: list[str] = []
        for fwd_file, fwd_decl in per_file_decls.get(_name, []):
            fwd_sig = _normalise_fn_signature(fwd_decl)
            if fwd_sig and fwd_sig != def_sig:
                bad.append(f"{fwd_file}: {fwd_sig}")
        if bad:
            conflicts.append((_name, def_sig, file, bad))
            continue  # skip emission — leave per-file decls in charge
        ext_decl = _funcdef_to_extern_decl(decl)
        text = gen.visit(ext_decl) + ";"
        # pycparser strips calling-convention keywords before parsing, so
        # re-insert the qualifier before the function name.  Watcom expects
        # it between the return type and the name, e.g.:
        #   extern void __cdecl mood_modfication(int seq);
        #   extern void __pascal radfree(void *ptr);
        # Without it, the prototype disagrees with the defining TU (E1057).
        conv = conv_fns.get(_name) or ("__cdecl" if _name in cdecl_fns else None)
        if conv:
            text = re.sub(
                r"\b" + re.escape(_name) + r"\s*\(",
                f"{conv} {_name}(",
                text,
                count=1,
            )
        funcs_lines.append(text)
        emitted_fn_count += 1

    if skipped_implicit:
        funcs_lines += [
            "",
            "/* Excluded from c2_funcs.h to preserve PS.EXE's implicit-int call",
            " * shape (Rule 37 reverse case) — these functions are declared",
            " * with a narrower-than-int return in their defining TU but PS",
            " * call sites emit 'test eax, eax' because the original source",
            " * had no prototype visible.  See _IMPLICIT_INT_FUNCTIONS in",
            " * c2/commands/c_source.py.",
            " *",
            " * " + ", ".join(skipped_implicit),
            " */",
        ]

    asm_primitives = _scan_asm_primitives(src_dir)
    if asm_primitives:
        funcs_lines += [
            "",
            "/* ── Asm-module primitives (library.asm, sprites.asm, dia_*.asm) ─ */",
            "/* Canonical signatures auto-derived from per-file extern decls.   */",
            "/* Conflicting forms are resolved by picking the most-typed variant.*/",
            "",
        ]
        for _name, decl in asm_primitives.items():
            funcs_lines.append(f"extern {decl};")

    if conflicts:
        funcs_lines += [
            "",
            "/* ── Conflicting fn signatures (NOT emitted above) ──────── */",
            "/* These functions have a definition in one .c file whose    */",
            "/* signature disagrees with at least one per-file forward    */",
            "/* declaration.  Resolve manually, then regenerate.          */",
            "",
        ]
        for name, def_sig, def_file, bad in conflicts:
            funcs_lines.append(f"/* {name}:")
            funcs_lines.append(f"     def  {def_file}: {def_sig}")
            for b in bad:
                funcs_lines.append(f"     fwd  {b}")
            funcs_lines.append("*/")

    funcs_lines += ["", "#endif /* C2_FUNCS_H */"]
    funcs_path.write_text("\n".join(funcs_lines) + "\n")

    n_data = len(ast.ext)
    n_fn = len(fn_pairs)
    print(
        f"Wrote {data_path} ({n_data} data), "
        f"{funcs_path} ({emitted_fn_count}/{n_fn} fn declarations)"
    )

# ── Module C stub generation ──────────────────────────────────────────────────
#
# Builds a complete FileAST for a C2 game module .c file from the data
# already available in symbols.json + the fixup maps.  The caller
# (genasm.py) drives the name-unmangling and fixup scanning; this module
# is responsible for constructing well-typed AST nodes and emitting them
# via CGenerator.
#
# The generated file has this structure:
#
#   // D:\C2\CODE\<source_file>
#
#   extern int   foo;               ← data externs from fixups
#   extern void  bar(void);         ← code externs from fixups
#
#   // STUB: C2 0xADDR
#   void func_name(void) {}
#
# Each "// STUB:" annotation is injected as a Pragma node (pycparser
# models #pragma as a first-class node; we abuse it for line comments
# that survive the round-trip through CGenerator).  We use a tiny custom
# subclass of CGenerator that renders our pseudo-pragma as a plain //
# comment instead.


from dataclasses import dataclass as _dc


@_dc
class ExternVar:
    """One extern variable entry for a module stub file."""
    name: str
    base_type: str           # "int", "char", "signed char", …
    array_suffix: str        # "" or "[]"
    pragma_aux: str | None   # raw "#pragma aux …" string, or None
    is_static: bool = False  # file-local (static linkage) — emits definition not extern decl


@_dc
class ExternFn:
    """One extern function entry for a module stub file."""
    name: str
    calling_convention: str  # "watcall", "cdecl", or "raw"


@_dc
class StubFn:
    """One stub function in a module stub file."""
    name: str
    address: int             # C2 virtual address (offset + 0x10000)
    calling_convention: str  # "watcall", "cdecl", or "raw"
    pragma_aux: str | None   # raw "#pragma aux …" string, or None
    is_static: bool = False  # file-local (static linkage)
    line_start: int | None = None  # first source line (from debug info)
    line_end:   int | None = None  # last source line (from debug info)


@_dc
class ModuleSpec:
    """Everything needed to emit a complete module .c stub file."""
    source_file: str                    # e.g. "D:\\C2\\CODE\\hotkeys.c"
    extern_vars: list[ExternVar]
    extern_fns: list[ExternFn]
    stubs: list[StubFn]


class _AnnotatingGenerator(c_generator.CGenerator):
    """CGenerator subclass that turns Pragma nodes into // STUB comments.

    pycparser's Pragma node is a convenient carrier for the annotation
    strings we want to appear directly above each stub function.  The
    standard CGenerator renders them as ``#pragma …``; we override
    visit_Pragma to render ``// STUB: C2 0xADDR`` instead.
    """

    def visit_Pragma(self, n: c_ast.Pragma) -> str:
        return f"// {n.string}"


def _make_void_func_decl(name: str) -> c_ast.FuncDecl:
    """Build a ``void name(void)`` FuncDecl node."""
    void_param = c_ast.Typename(
        name=None, quals=[], align=None,
        type=c_ast.TypeDecl(
            declname=None, quals=[], align=None,
            type=c_ast.IdentifierType(["void"]),
        ),
    )
    param_list = c_ast.ParamList([void_param])
    ret_type = c_ast.TypeDecl(
        declname=name, quals=[], align=None,
        type=c_ast.IdentifierType(["void"]),
    )
    return c_ast.FuncDecl(args=param_list, type=ret_type)


def _make_stub_funcdef(name: str, address: int) -> list[c_ast.Node]:
    """Return [Pragma-annotation, FuncDef] for one stub function."""
    annotation = c_ast.Pragma(f"STUB: C2 0x{address:05X}")

    decl = c_ast.Decl(
        name=name, quals=[], align=[], storage=[], funcspec=[],
        type=_make_void_func_decl(name),
        init=None, bitsize=None,
    )
    func_def = c_ast.FuncDef(
        decl=decl,
        param_decls=None,
        body=c_ast.Compound(block_items=[], coord=None),
        coord=None,
    )
    return [annotation, func_def]


def _make_extern_fn_decl(name: str) -> c_ast.Decl:
    """Build an ``extern void name(void);`` Decl node."""
    return c_ast.Decl(
        name=name, quals=[], align=[], storage=["extern"], funcspec=[],
        type=_make_void_func_decl(name),
        init=None, bitsize=None,
    )


def emit_module_c(spec: ModuleSpec) -> str:
    """Render a ModuleSpec to a complete .c source string.

    Calling conventions that pycparser cannot represent (__cdecl, raw)
    are emitted as verbatim lines; everything else goes through the AST.
    """
    gen = _AnnotatingGenerator()
    lines: list[str] = [f"// {spec.source_file}", ""]

    # ── Extern variable declarations (AST) ─────────────────────────────
    for ev in spec.extern_vars:
        if ev.is_static:
            # Static file-local definition: `static int name;`
            node = _make_extern_decl(ev.name, ev.base_type, ev.array_suffix)
            node.storage = ["static"]
        else:
            node = _make_extern_decl(ev.name, ev.base_type, ev.array_suffix)
        lines.append(gen.visit(node) + ";")
        if ev.pragma_aux:
            lines.append(ev.pragma_aux)

    if spec.extern_vars:
        lines.append("")

    # ── Extern function declarations ────────────────────────────────────
    for ef in spec.extern_fns:
        if ef.calling_convention == "cdecl":
            # pycparser doesn't parse __cdecl — emit verbatim
            lines.append(f"extern void __cdecl {ef.name}(void);")
        elif ef.calling_convention == "raw":
            node = _make_extern_fn_decl(ef.name)
            lines.append(gen.visit(node) + ";")
            lines.append(f'#pragma aux {ef.name} "*"')
        else:
            node = _make_extern_fn_decl(ef.name)
            lines.append(gen.visit(node) + ";")

    if spec.extern_fns:
        lines.append("")

    # ── Stub function definitions ────────────────────────────────────────
    for stub in spec.stubs:
        storage = ["static"] if stub.is_static else []
        lines.append(f"// STUB: C2 0x{stub.address:05X}")
        if stub.line_start is not None and stub.line_end is not None:
            lines.append(f"// Lines {stub.line_start}\u2013{stub.line_end}")
        if stub.calling_convention == "cdecl":
            prefix = "static " if stub.is_static else ""
            lines.append(f"{prefix}void __cdecl {stub.name}(void) {{}}")
        elif stub.calling_convention == "raw":
            decl = c_ast.Decl(
                name=stub.name, quals=[], align=[], storage=storage, funcspec=[],
                type=_make_void_func_decl(stub.name),
                init=None, bitsize=None,
            )
            func_def = c_ast.FuncDef(decl, None,
                                     c_ast.Compound([], None), None)
            lines.append(gen.visit(func_def).rstrip())
            lines.append(f'#pragma aux {stub.name} "*"')
        else:
            # Common case: watcall (public or static)
            decl = c_ast.Decl(
                name=stub.name, quals=[], align=[], storage=storage, funcspec=[],
                type=_make_void_func_decl(stub.name),
                init=None, bitsize=None,
            )
            func_def = c_ast.FuncDef(decl, None,
                                     c_ast.Compound([], None), None)
            lines.append(gen.visit(func_def).rstrip())
        lines.append("")

    return "\n".join(lines) + "\n"

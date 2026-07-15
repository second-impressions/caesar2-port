"""Self-contained scratch builder.

Given a function's body, extract just the declarations it needs from
project headers and inline them at the top of ``scratch.c``.  The agent
then sees ONE file with everything required to compile -- no
``#include`` chasing through 100KB headers.

Algorithm:

  1. Parse the project headers ONCE per project (cached) to build:
     - func_protos: name -> `extern <type> <name>(<args>);`
     - data_externs: name -> `extern <type> <name>;`
     - structs: name -> `struct <name> { ... };`
     - typedefs: name -> `typedef ... <name>;`
  2. Walk the function body, collect all C identifiers.
  3. For each identifier, look it up in the symbol tables.
  4. For each struct type added, recursively extract identifiers from
     ITS definition and resolve those too (transitive type closure).
  5. Emit the bundled scratch in stable order: typedefs, structs (topo
     by dep), data externs, function prototypes, then the function body.

Missing symbols fail SILENTLY -- the resulting compile will surface the
real error to the agent, who can add the declaration manually.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path


# C reserved words + primitive type keywords.  Identifiers matching
# these are never looked up.
_C_KEYWORDS = frozenset({
    "auto", "break", "case", "char", "const", "continue", "default", "do",
    "double", "else", "enum", "extern", "float", "for", "goto", "if",
    "inline", "int", "long", "register", "restrict", "return", "short",
    "signed", "sizeof", "static", "struct", "switch", "typedef", "union",
    "unsigned", "void", "volatile", "while",
    # Watcom-specific
    "__watcall", "__cdecl", "__fastcall", "__pascal", "__stdcall", "__interrupt",
    "__far", "__near", "__huge", "_Packed",
    # Standard library names the bundler does NOT inline (rely on
    # <stdlib.h>, <string.h>, <stdio.h> etc. that scratch can include)
    "NULL", "size_t", "FILE", "stdin", "stdout", "stderr",
    "malloc", "calloc", "realloc", "free", "exit", "abort",
    "memcpy", "memmove", "memset", "memcmp", "strcpy", "strncpy",
    "strcmp", "strncmp", "strlen", "strcat", "strncat", "strchr",
    "strstr", "sprintf", "printf", "fprintf", "scanf", "fscanf",
    "fopen", "fclose", "fread", "fwrite", "fseek", "ftell",
    "atoi", "atol", "atof", "rand", "srand", "abs", "labs",
    "getcwd", "getchar", "putchar", "puts", "gets",
    "TRUE", "FALSE",
})

# C identifier pattern (matches names, not type prefixes like `unsigned`).
_IDENT_RE = re.compile(r"\b([A-Za-z_]\w*)\b")

# Strip C comments + string/char literals before identifier extraction so
# we don't pick up symbols mentioned in prose.
_STRIP_RE = re.compile(
    r'/\*.*?\*/'      # block comment
    r'|//.*?$'        # line comment
    r'|"(?:[^"\\]|\\.)*"'   # string literal
    r"|'(?:[^'\\]|\\.)*'",  # char literal
    re.DOTALL | re.MULTILINE,
)


def collect_identifiers(c_text: str) -> set[str]:
    """Return the set of C identifiers referenced in ``c_text``."""
    stripped = _STRIP_RE.sub(" ", c_text)
    return {m.group(1) for m in _IDENT_RE.finditer(stripped)
            if m.group(1) not in _C_KEYWORDS}


# ── Symbol-table building ────────────────────────────────────────────────


@dataclass(frozen=True)
class Decl:
    """One header-derived declaration we may inline into scratch.c."""

    name: str
    text: str                       # the raw declaration line(s)
    header: str                     # source file basename, for traceability
    kind: str                       # "func" | "data" | "struct" | "typedef"


@dataclass(frozen=True)
class SymbolTable:
    func_protos: dict[str, Decl]    # foo -> `extern T foo(...);`
    data_externs: dict[str, Decl]   # bar -> `extern T bar;`
    structs: dict[str, Decl]        # tag -> `struct tag { ... };`
    typedefs: dict[str, Decl]       # name -> `typedef ... name;`
    macros: dict[str, Decl]         # M -> `#define M(...) ...`

    def lookup(self, name: str) -> Decl | None:
        # Data externs and function prototypes win over macros: an
        # identifier that's both an enum member AND a global should
        # resolve to the global (the function body references the
        # global, not the enum member with the same name).
        return (
            self.data_externs.get(name)
            or self.func_protos.get(name)
            or self.typedefs.get(name)
            or self.structs.get(name)
            or self.macros.get(name)
        )


_EXTERN_FUNC_RE = re.compile(
    r"^\s*extern\s+[\w\s\*]+?\b(\w+)\s*\([^;]*?\)\s*;\s*$",
    re.MULTILINE,
)
_EXTERN_DATA_RE = re.compile(
    # Last identifier before optional [...]+; that's the name.
    # Allow MULTIPLE bracket suffixes for multi-dim arrays
    # (e.g. ``extern int city_jars_x_off[][4];``).
    r"^\s*extern\s+(?:struct\s+\w+\s*\*?|[\w\s\*]+?)\b(\w+)\s*(?:\[[^\]]*\])*\s*;\s*$",
    re.MULTILINE,
)
_ENUM_DEF_RE = re.compile(
    r"^\s*enum(?:\s+(\w+))?\s*\{([^}]*)\}\s*;",
    re.MULTILINE | re.DOTALL,
)
_STRUCT_DEF_RE = re.compile(
    r"^\s*(?:typedef\s+)?struct\s+(\w+)\s*\{",
    re.MULTILINE,
)
_TYPEDEF_SIMPLE_RE = re.compile(
    r"^\s*typedef\s+[\w\s\*]+?\b(\w+)\s*;\s*$",
    re.MULTILINE,
)
_MACRO_DEFINE_RE = re.compile(
    r"^\s*#\s*define\s+(\w+)(?:\([^)]*\))?\s+([^\n]*?)\s*$",
    re.MULTILINE,
)


def _scan_header(text: str, header_name: str) -> tuple[dict[str, Decl], dict[str, Decl], dict[str, Decl], dict[str, Decl], dict[str, Decl]]:
    """Extract every declaration we know how to inline from one header."""
    funcs: dict[str, Decl] = {}
    data: dict[str, Decl] = {}
    structs: dict[str, Decl] = {}
    typedefs: dict[str, Decl] = {}
    macros: dict[str, Decl] = {}

    # Function externs -- match the full line for `text`
    for m in _EXTERN_FUNC_RE.finditer(text):
        name = m.group(1)
        funcs[name] = Decl(name=name, text=m.group(0).strip(),
                           header=header_name, kind="func")

    # Data externs -- skip those that match the func pattern (already taken)
    func_names = set(funcs)
    for m in _EXTERN_DATA_RE.finditer(text):
        name = m.group(1)
        if name in func_names:
            continue
        # Filter out matches where the "name" is actually a type keyword
        if name in _C_KEYWORDS:
            continue
        data[name] = Decl(name=name, text=m.group(0).strip(),
                          header=header_name, kind="data")

    # Struct definitions (brace-match span)
    for m in _STRUCT_DEF_RE.finditer(text):
        name = m.group(1)
        span = _struct_span(text, m.start(), m.end() - 1)
        if span is None:
            continue
        structs[name] = Decl(name=name, text=text[span[0]:span[1]].strip(),
                             header=header_name, kind="struct")

    # Simple typedefs (one-liners; ignore typedef-struct for now \u2014 handled
    # by the struct path when the tag matches)
    for m in _TYPEDEF_SIMPLE_RE.finditer(text):
        name = m.group(1)
        if name in structs or name in _C_KEYWORDS:
            continue
        typedefs[name] = Decl(name=name, text=m.group(0).strip(),
                              header=header_name, kind="typedef")

    # Object-like and function-like macros (`#define NAME ...` or
    # `#define NAME(args) ...`).  We only capture single-line macros;
    # multi-line continuations are skipped.
    for m in _MACRO_DEFINE_RE.finditer(text):
        name = m.group(1)
        if name in _C_KEYWORDS or name in structs or name in typedefs:
            continue
        # Skip include guards (NAME ending in _H)
        if name.endswith("_H") and not m.group(2):
            continue
        macros[name] = Decl(name=name, text=m.group(0).strip(),
                            header=header_name, kind="macro")

    # Enum members: treat each named member as a constant.  We inline the
    # WHOLE enum block when any member is referenced (cheaper than
    # synthesising individual `#define`s, and preserves the original
    # numbering when members use `=` initialisers).
    for m in _ENUM_DEF_RE.finditer(text):
        # Strip comments from the enum body before extracting identifiers
        # so an unrelated identifier mentioned in a /* ... */ note isn't
        # registered as an enum member.
        enum_body = _STRIP_RE.sub(" ", m.group(2))
        # Only true enum members live BEFORE an `=` or `,`; everything
        # after `=` is the (possibly-identifier-bearing) initializer.
        # We treat the LHS of each `,`-separated entry as the member name.
        block_text = m.group(0).strip()
        for entry in enum_body.split(","):
            lhs = entry.split("=")[0].strip()
            mm = re.match(r"^([A-Za-z_]\w*)\s*$", lhs)
            if not mm:
                continue
            name = mm.group(1)
            if name in _C_KEYWORDS:
                continue
            if name in macros:
                continue
            macros[name] = Decl(name=name, text=block_text,
                                header=header_name, kind="macro")

    return funcs, data, structs, typedefs, macros


def _struct_span(text: str, start: int, open_brace: int) -> tuple[int, int] | None:
    """Find the end of a `struct {...};` block starting at ``open_brace``."""
    depth = 1
    i = open_brace + 1
    n = len(text)
    while i < n and depth > 0:
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        i += 1
    if depth != 0:
        return None
    # Eat optional trailing identifier (typedef-style) + `;`
    while i < n and text[i] not in ";\n":
        i += 1
    if i < n and text[i] == ";":
        i += 1
    return start, i


_TU_FUNC_DEF_RE = re.compile(
    # Capture the signature line(s) of a top-level function definition:
    # optional storage-class modifiers, return type, name, parens, then `{`.
    # We look for the `{` at column 0 (after the signature) to skip
    # nested definitions inside ifdefs / macro bodies.
    r"^((?:(?:static|extern|inline|__watcall|__cdecl|__fastcall|"
    r"__interrupt|__far|__near|__loadds)\s+)*"
    r"[\w\s\*]+?\b(\w+)\s*\([^;{]*?\))\s*\{",
    re.MULTILINE | re.DOTALL,
)


def tu_local_symbols(tu_text: str, tu_name: str) -> SymbolTable:
    """Extract supplementary declarations from a single .c TU.

    The PROJECT headers (c2_funcs.h etc.) deliberately omit a handful of
    declarations that need special storage-class modifiers
    (``__far``/``__interrupt`` etc.) since the header generator can't
    represent them.  Those decls live INLINE in the .c file, ahead of
    every function that uses them.  This pass picks them up so the
    bundler can inline them into scratch alongside the header-derived
    decls.

    Also synthesises prototypes for file-local function DEFINITIONS in
    the TU.  Some helpers (e.g. ``cbc_end`` in lib32.c) are file-private
    and never declared extern, but other functions in the same TU still
    call or take their address.  Without a prototype the compile errors;
    we extract the signature and emit ``extern <signature>;``.
    """
    f, d, s, t, m = _scan_header(tu_text, tu_name)
    # Strip strings/chars/comments so we don't match identifiers inside them.
    clean = _STRIP_RE.sub(" ", tu_text)
    for match in _TU_FUNC_DEF_RE.finditer(clean):
        sig = " ".join(match.group(1).split())  # collapse whitespace
        name = match.group(2)
        if name in f:
            continue
        f[name] = Decl(name=name, text=f"extern {sig};",
                       header=tu_name, kind="func")
    return SymbolTable(
        func_protos=f, data_externs=d, structs=s, typedefs=t, macros=m,
    )


def merge_symbol_tables(*tables: SymbolTable) -> SymbolTable:
    """Right-most table wins on conflicts."""
    funcs: dict[str, Decl] = {}
    data: dict[str, Decl] = {}
    structs: dict[str, Decl] = {}
    typedefs: dict[str, Decl] = {}
    macros: dict[str, Decl] = {}
    for t in tables:
        funcs.update(t.func_protos)
        data.update(t.data_externs)
        structs.update(t.structs)
        typedefs.update(t.typedefs)
        macros.update(t.macros)
    return SymbolTable(
        func_protos=funcs, data_externs=data,
        structs=structs, typedefs=typedefs, macros=macros,
    )


@lru_cache(maxsize=8)
def build_symbol_table(headers_dir_str: str) -> SymbolTable:
    """Parse every header in ``headers_dir`` and merge into one SymbolTable."""
    headers_dir = Path(headers_dir_str)
    funcs: dict[str, Decl] = {}
    data: dict[str, Decl] = {}
    structs: dict[str, Decl] = {}
    typedefs: dict[str, Decl] = {}
    macros: dict[str, Decl] = {}
    for h in sorted(headers_dir.glob("*.h")):
        text = h.read_text()
        hf, hd, hs, ht, hm = _scan_header(text, h.name)
        funcs.update(hf)
        data.update(hd)
        structs.update(hs)
        typedefs.update(ht)
        macros.update(hm)
    return SymbolTable(
        func_protos=funcs, data_externs=data,
        structs=structs, typedefs=typedefs, macros=macros,
    )


# ── Dependency resolution ────────────────────────────────────────────────


def resolve_needed(
    function_body: str, symbols: SymbolTable,
    *, exclude_names: frozenset[str] = frozenset(),
) -> list[Decl]:
    """Return the ordered list of declarations needed for ``function_body``.

    Order: typedefs first, structs in dependency order (deps before
    dependents), data externs, function prototypes.  Excludes anything
    in ``exclude_names`` (e.g. the function being decompiled itself).
    """
    # needed is keyed by (kind, name) because C has multiple namespaces
    # \u2014 a struct tag and a variable can share an identifier (the very
    # common ``extern struct request_message request_message;`` shape).
    needed: dict[tuple[str, str], Decl] = {}
    queue: set[tuple[str, str]] = set()
    # Body identifiers go in as "?" kind (unknown namespace);
    # lookup() picks the highest-priority decl.
    for name in collect_identifiers(function_body):
        if name in exclude_names:
            continue
        decl = symbols.lookup(name)
        if decl is not None:
            queue.add((decl.kind, name))

    def _struct_or_typedef_lookup(nm: str) -> Decl | None:
        return symbols.structs.get(nm) or symbols.typedefs.get(nm) or symbols.macros.get(nm)

    while queue:
        key = queue.pop()
        if key in needed:
            continue
        kind, name = key
        if name in exclude_names:
            continue
        needed[key] = symbols.macros.get(name) if kind == "macro" else (
            symbols.func_protos.get(name) if kind == "func" else
            symbols.data_externs.get(name) if kind == "data" else
            symbols.structs.get(name) if kind == "struct" else
            symbols.typedefs.get(name)
        )
        decl = needed[key]
        if decl is None:
            del needed[key]
            continue
        # Recurse: STRUCT / TYPEDEF type references in this decl's text.
        # For data/func decls those refs land in the struct/typedef
        # namespace (so a variable named ``request_message`` and a struct
        # ``request_message`` can both be needed).
        if decl.kind in ("struct", "typedef", "data", "func"):
            for ref in _type_references(decl.text, symbols):
                if ref in exclude_names:
                    continue
                ref_decl = _struct_or_typedef_lookup(ref)
                if ref_decl is None:
                    continue
                queue.add((ref_decl.kind, ref))
        if decl.kind == "macro":
            # Macros expand inline; the expansion may reference any kind
            # of symbol \u2014 a function, an extern, another macro, a struct.
            for ident in collect_identifiers(decl.text):
                if ident in exclude_names:
                    continue
                ref_decl = symbols.lookup(ident)
                if ref_decl is not None:
                    queue.add((ref_decl.kind, ident))

    # Topo-sort by kind: macros first (constants used in array dims),
    # typedefs, structs in dependency order, data externs, then function
    # prototypes.  Within each group, sort by dependency or name.
    macro_decls = [d for d in needed.values() if d.kind == "macro"]
    typedef_decls = [d for d in needed.values() if d.kind == "typedef"]
    struct_decls = [d for d in needed.values() if d.kind == "struct"]
    data_decls = [d for d in needed.values() if d.kind == "data"]
    func_decls = [d for d in needed.values() if d.kind == "func"]

    struct_decls = _topo_sort_structs(struct_decls)
    macro_decls.sort(key=lambda d: d.name)
    typedef_decls.sort(key=lambda d: d.name)
    data_decls.sort(key=lambda d: d.name)
    func_decls.sort(key=lambda d: d.name)

    return [*macro_decls, *typedef_decls, *struct_decls, *data_decls, *func_decls]


_STRUCT_REF_RE = re.compile(r"\bstruct\s+(\w+)\b")


def _type_references(decl_text: str, symbols: SymbolTable) -> set[str]:
    """Extract TYPE / MACRO references from a decl's body.

    Picks up:
      * ``struct <name>`` references (the explicit form)
      * Bare typedef names that resolve to a known typedef
      * Bare macro names that resolve to a known macro (so array
        dimensions like ``extern foo[CITY_W * CITY_H]`` pull in the
        CITY_W / CITY_H ``#define`` lines).

    Skips bare identifiers that aren't structs / typedefs / macros \u2014 most
    field names inside a struct body are noise.
    """
    out: set[str] = set()
    for m in _STRUCT_REF_RE.finditer(decl_text):
        out.add(m.group(1))
    for tok in re.findall(r"\b([A-Za-z_]\w*)\b", decl_text):
        if tok in _C_KEYWORDS:
            continue
        if tok in symbols.typedefs or tok in symbols.macros:
            out.add(tok)
    return out


def _topo_sort_structs(decls: list[Decl]) -> list[Decl]:
    """Order struct decls so each one's referenced struct types appear first."""
    by_name = {d.name: d for d in decls}
    visited: set[str] = set()
    order: list[Decl] = []

    def visit(name: str) -> None:
        if name in visited:
            return
        visited.add(name)
        decl = by_name.get(name)
        if decl is None:
            return
        # Find struct references INSIDE the body of this struct.
        body_text = decl.text
        # `struct <other>` references
        for m in re.finditer(r"\bstruct\s+(\w+)\b", body_text):
            ref = m.group(1)
            if ref != name and ref in by_name:
                visit(ref)
        order.append(decl)

    for d in decls:
        visit(d.name)
    return order


# ── Composition ──────────────────────────────────────────────────────────


def render_bundled_scratch(
    *, header_comment: str,
    function_text: str,
    function_name: str,
    symbols: SymbolTable,
    extra_includes: list[str] | None = None,
    additional_functions: list[tuple[str, str]] | None = None,
) -> str:
    """Build the full ``scratch.c`` content.

    ``function_text`` is the function definition (signature + body).
    ``extra_includes`` are ``#include <...>`` lines to pre-pend (e.g. for
    standard library use).  ``additional_functions`` is a list of
    ``(name, definition_text)`` pairs for AUXILIARY function definitions
    that should sit in the same TU as the function under test — most
    commonly the tail-merge donor, whose body must be present in the
    same object so the linker can ComTail-merge the two epilogues.  The
    auxiliary functions' identifiers feed dependency resolution (their
    types / externs / called helpers are inlined too) and their names
    are excluded from the prototype set (so the bundler doesn't emit
    a forward `extern` that would conflict with the definition).  The
    bundler inlines everything else.
    """
    additional_functions = additional_functions or []
    aux_names = frozenset(n for n, _ in additional_functions)
    combined_for_deps = function_text + "\n\n" + "\n\n".join(
        body for _n, body in additional_functions
    )
    decls = resolve_needed(
        combined_for_deps, symbols,
        exclude_names=frozenset({function_name}) | aux_names,
    )

    parts: list[str] = [header_comment.rstrip() + "\n\n"]

    if extra_includes:
        parts.append("\n".join(extra_includes) + "\n\n")

    if decls:
        macros = [d for d in decls if d.kind == "macro"]
        typedefs = [d for d in decls if d.kind == "typedef"]
        structs = [d for d in decls if d.kind == "struct"]
        data = [d for d in decls if d.kind == "data"]
        funcs = [d for d in decls if d.kind == "func"]

        if macros:
            parts.append("/* === Macros === */\n")
            # Deduplicate by text: enum blocks may be reached via several
            # of their member names and would otherwise be emitted N times.
            seen: set[str] = set()
            for d in macros:
                if d.text in seen:
                    continue
                seen.add(d.text)
                parts.append(d.text + "\n")
            parts.append("\n")
        if typedefs:
            parts.append("/* === Typedefs === */\n")
            parts.extend(d.text + "\n" for d in typedefs)
            parts.append("\n")
        if structs:
            parts.append("/* === Types === */\n")
            parts.extend(d.text + "\n\n" for d in structs)
        if data:
            parts.append("/* === Externs === */\n")
            parts.extend(d.text + "\n" for d in data)
            parts.append("\n")
        if funcs:
            parts.append("/* === Prototypes === */\n")
            parts.extend(d.text + "\n" for d in funcs)
            parts.append("\n")

    parts.append("/* === Function === */\n")
    parts.append(function_text.rstrip() + "\n")

    if additional_functions:
        parts.append(
            "\n/* === Auxiliary functions (same-TU companions, e.g. "
            "tail-merge donors so the linker can ComTail-merge\n"
            " *     the shared epilogue with the function above).  "
            "DO NOT EDIT — these are the project's\n"
            " *     decomp sources, lifted verbatim so wcc386 sees "
            "both functions in one .obj.\n"
            " */\n"
        )
        for _name, body in additional_functions:
            parts.append(body.rstrip() + "\n\n")

    return "".join(parts)

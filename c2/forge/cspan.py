"""Byte-span-accurate C AST index backed by tree-sitter-c.

Why a second parser?  Forge's design invariant is TEXT-PRESERVING
edits: every lever emits ``TextEdit`` byte ranges against the RAW
on-disk source.  pycparser cannot provide those ranges reliably --
it parses a *preprocessed shadow* of the file (comments / Watcom
keywords stripped) so its coords keep line fidelity but the COLUMNS
drift on any line with a block comment, and node END positions don't
exist at all.  That forced the older levers into regex/lexical scans.

tree-sitter-c parses the raw text directly (comments and all) and
every node carries ``start_byte`` / ``end_byte`` -- exactly the
currency a ``TextEdit`` needs.  The new lever presets therefore do
BOTH discovery and span extraction on the tree-sitter AST; pycparser
remains in place for the older, proven levers and for type-level
queries.

The module is import-light: tree-sitter is only loaded on first use,
and parses are memoised per source text (LRU) so a preset battery that
derives ten levers from one file parses it once (~5-10 ms).
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Iterator


def available() -> bool:
    """True when tree-sitter-c is importable (it is a project dep;
    this exists so presets can degrade to no-op instead of raising in
    a stripped-down environment)."""
    try:
        import tree_sitter  # noqa: F401
        import tree_sitter_c  # noqa: F401
        return True
    except Exception:                       # noqa: BLE001
        return False


@lru_cache(maxsize=1)
def _parser():
    import tree_sitter
    import tree_sitter_c
    lang = tree_sitter.Language(tree_sitter_c.language())
    return tree_sitter.Parser(lang)


@lru_cache(maxsize=16)
def _parse_cached(src_bytes: bytes):
    return _parser().parse(src_bytes)


def walk(node) -> Iterator:
    """Pre-order walk of every node (named and anonymous)."""
    stack = [node]
    while stack:
        n = stack.pop()
        yield n
        stack.extend(reversed(n.children))


def walk_named(node) -> Iterator:
    stack = [node]
    while stack:
        n = stack.pop()
        yield n
        stack.extend(reversed(n.named_children))


_COMPARISON_OPS = frozenset({"==", "!=", "<", ">", "<=", ">="})

_SIDE_EFFECT_TYPES = frozenset({
    "call_expression", "assignment_expression", "update_expression",
})


def side_effect_free(node) -> bool:
    """No calls, assignments, or ``++``/``--`` anywhere in the subtree."""
    return not any(n.type in _SIDE_EFFECT_TYPES for n in walk_named(node))


def unparen(node):
    """Descend through parenthesized_expression wrappers."""
    while node is not None and node.type == "parenthesized_expression":
        inner = [c for c in node.named_children if c.type != "comment"]
        if len(inner) != 1:
            return node
        node = inner[0]
    return node


def lvalue_base(node) -> str | None:
    """The base identifier name of an lvalue expression (bytes decoded),
    descending through subscripts / field accesses / derefs / parens /
    casts.  ``None`` when the base is not a plain identifier."""
    cur = node
    while cur is not None:
        t = cur.type
        if t == "identifier":
            return cur.text.decode()
        if t == "subscript_expression":
            cur = cur.child_by_field_name("argument")
        elif t == "field_expression":
            cur = cur.child_by_field_name("argument")
        elif t == "pointer_expression":
            cur = cur.child_by_field_name("argument")
        elif t == "parenthesized_expression":
            cur = unparen(cur)
            if cur is not None and cur.type == "parenthesized_expression":
                return None
        elif t == "cast_expression":
            cur = cur.child_by_field_name("value")
        else:
            return None
    return None


def identifiers(node) -> set[str]:
    """Every identifier name in the subtree (field names EXCLUDED --
    ``a.x`` reads ``a``, not ``x``)."""
    out: set[str] = set()
    for n in walk_named(node):
        if n.type != "identifier":
            continue
        p = n.parent
        if p is not None and p.type == "field_expression" \
                and p.child_by_field_name("field") == n:
            continue
        out.add(n.text.decode())
    return out


def stmt_reads_writes(stmt) -> tuple[set[str], set[str], bool]:
    """(reads, writes, has_call) for one statement subtree.

    Writes are the BASE identifiers of assignment / update lvalues
    (``arr[i].f = ..`` writes ``arr``).  Reads are every other
    identifier.  Matches the conservative policy of the older
    pycparser ``_stmt_rw`` so the two lever families agree on what
    "independent" means.
    """
    reads: set[str] = set()
    writes: set[str] = set()
    has_call = False
    for n in walk_named(stmt):
        if n.type == "call_expression":
            has_call = True
        elif n.type == "assignment_expression":
            lhs = n.child_by_field_name("left")
            base = lvalue_base(lhs) if lhs is not None else None
            if base:
                writes.add(base)
                # subscript / field / deref components of the lvalue read
                if lhs.type != "identifier":
                    reads |= identifiers(lhs) - {base}
                op = n.child_by_field_name("operator")
                if op is not None and op.text != b"=":
                    reads.add(base)
            else:
                # unknown lvalue base (pointer arithmetic): treat as
                # memory write -- poison both sets so callers refuse.
                writes.add("*mem*")
                if lhs is not None:
                    reads |= identifiers(lhs)
        elif n.type == "update_expression":
            arg = n.child_by_field_name("argument")
            base = lvalue_base(arg) if arg is not None else None
            if base:
                writes.add(base)
                reads.add(base)
            else:
                writes.add("*mem*")
    all_ids = identifiers(stmt)
    reads |= all_ids - writes
    return reads, writes, has_call


@dataclass
class FnSpan:
    """tree-sitter view of ONE function definition in a file.

    OFFSET CONTRACT: every ``start_byte``/``end_byte`` this index (and
    every node it hands out) reports is a CHARACTER offset into
    ``text``.  The parse buffer is an ASCII SHADOW -- exactly one byte
    per char, non-ASCII chars (they occur only in comments) replaced
    with ``?`` -- so tree-sitter's byte offsets compose directly with
    the str-based ``TextEdit`` pipeline.  Use :meth:`src` (which
    slices the ORIGINAL text) whenever content matters; ``node.text``
    is safe only for identifiers / operators / literals.
    """

    text: str                    # the full raw file text (str)
    data: bytes                  # ASCII shadow, len(data) == len(text)
    fn_node: object              # function_definition
    body: object                 # compound_statement


    @classmethod
    def load(cls, text: str, function: str) -> "FnSpan | None":
        """Locate ``function``'s definition in ``text``.  Returns None
        when tree-sitter is unavailable or the function isn't found."""
        if not available():
            return None
        data = text.encode("ascii", errors="replace")
        tree = _parse_cached(data)
        want = function.encode()
        for node in tree.root_node.children:
            if node.type != "function_definition":
                continue
            decl = node.child_by_field_name("declarator")
            # descend to the innermost function_declarator's identifier
            name = None
            cur = decl
            while cur is not None:
                if cur.type == "function_declarator":
                    ident = cur.child_by_field_name("declarator")
                    if ident is not None and ident.type == "identifier":
                        name = ident.text
                    break
                cur = cur.child_by_field_name("declarator")
            if name != want:
                continue
            body = node.child_by_field_name("body")
            if body is None:
                continue
            return cls(text=text, data=data, fn_node=node, body=body)
        return None


    def src(self, node) -> str:
        """ORIGINAL source slice of a node (char-offset exact -- see
        the class OFFSET CONTRACT)."""
        return self.text[node.start_byte:node.end_byte]

    def line_start(self, byte_off: int) -> int:
        nl = self.data.rfind(b"\n", 0, byte_off)
        return nl + 1

    def line_end(self, byte_off: int) -> int:
        """Offset just PAST the newline of the line containing off."""
        nl = self.data.find(b"\n", byte_off)
        return len(self.data) if nl < 0 else nl + 1

    def indent_of(self, node) -> str:
        ls = self.line_start(node.start_byte)
        seg = self.text[ls:node.start_byte]
        ws = seg[:len(seg) - len(seg.lstrip())]
        return ws if not seg.strip() else "    "

    def owns_line(self, node) -> bool:
        """True when the node's text is the ONLY content on its
        line(s): nothing but whitespace before it on the first line and
        nothing but whitespace (or nothing) after it on the last."""
        ls = self.line_start(node.start_byte)
        if self.data[ls:node.start_byte].strip():
            return False
        le = self.line_end(node.end_byte - 1)
        return not self.data[node.end_byte:le].strip(b"\n \t")

    def full_line_span(self, node) -> tuple[int, int]:
        """(start, end) covering the node's whole line block --
        line-start of its first line through the newline of its last."""
        return (self.line_start(node.start_byte),
                self.line_end(node.end_byte - 1))

    def line_no(self, node) -> int:
        return node.start_point[0] + 1


    def local_names(self) -> set[str]:
        """Every declared local (any depth) + every parameter name."""
        names: set[str] = set()
        for n in walk_named(self.body):
            if n.type != "declaration":
                continue
            for d in n.named_children:
                names |= _declared_names(d)
        decl = self.fn_node.child_by_field_name("declarator")
        for n in walk_named(decl) if decl is not None else ():
            if n.type == "parameter_declaration":
                for d in n.named_children:
                    names |= _declared_names(d)
        return names

    def addr_taken(self) -> set[str]:
        """Locals whose address is taken (``&name``) anywhere in the
        body -- calls may alias these, so they can't be proven
        call-invariant."""
        out: set[str] = set()
        for n in walk_named(self.body):
            if n.type == "pointer_expression" \
                    and n.child(0) is not None and n.child(0).type == "&":
                arg = n.child_by_field_name("argument")
                if arg is not None and arg.type == "identifier":
                    out.add(arg.text.decode())
        return out

    def call_free_locals(self) -> set[str]:
        """Locals + params that no call can observe or modify: declared
        in this function and never address-taken."""
        return self.local_names() - self.addr_taken()

    def top_decl_anchor(self) -> int | None:
        """Byte offset where an injected decl line goes: just before
        the first non-declaration statement of the top-level body
        (C89-safe, end of the leading decl run)."""
        for c in self.body.named_children:
            if c.type == "comment":
                continue
            if c.type != "declaration":
                return self.line_start(c.start_byte)
        return None


    def nodes(self, *types: str) -> list:
        return [n for n in walk_named(self.body) if n.type in types]

    def compounds(self) -> list:
        return [self.body] + [n for n in walk_named(self.body)
                              if n.type == "compound_statement"
                              and n != self.body]

    def statements_of(self, compound) -> list:
        return [c for c in compound.named_children if c.type != "comment"]


def _declared_names(declarator) -> set[str]:
    """Identifier(s) introduced by a declarator subtree."""
    out: set[str] = set()
    t = declarator.type
    if t == "identifier":
        out.add(declarator.text.decode())
    elif t in ("init_declarator", "pointer_declarator",
               "array_declarator", "function_declarator",
               "parenthesized_declarator"):
        d = declarator.child_by_field_name("declarator")
        if d is not None:
            out |= _declared_names(d)
    return out


@lru_cache(maxsize=16)
def _fnspan_cached(text: str, function: str):
    return FnSpan.load(text, function)


def fnspan(text: str, function: str) -> FnSpan | None:
    """Memoised FnSpan lookup (per (text, function))."""
    return _fnspan_cached(text, function)

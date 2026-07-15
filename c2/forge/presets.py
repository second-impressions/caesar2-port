"""Lever presets -- tree-sitter-driven bulk hypothesis generators.

2026-07-05 rewrite: every preset now does BOTH site discovery and
byte-span extraction on the tree-sitter AST of the RAW source (see
:mod:`c2.forge.cspan`).  The previous generation mixed pycparser
walks (line-accurate but column-drifting -- it parses a preprocessed
shadow of the file) with regex/lexical scans; that implementation is
gone.  tree-sitter nodes carry exact ``start_byte``/``end_byte``, so
packed lines, comments, and multi-line statements are handled by
construction rather than by defensive string checks.

Each preset is a function ``(forge, **opts) -> int`` that identifies
every legal site for its transformation and appends ONE candidate per
site via ``forge.candidate`` (text-preserving ``TextEdit``s only --
never an AST regeneration).  A few presets together build a candidate
pool of 100-500 entries; the cartesian/beam search does the rest.

The 2026-07-03..05 byte-exact commits are mirrored here as levers;
each new preset's docstring cites its evidence commits.
"""

from __future__ import annotations

import itertools

from c2.forge import cspan
from c2.forge.cspan import (
    FnSpan, _declared_names, identifiers, lvalue_base, side_effect_free,
    stmt_reads_writes, unparen, walk_named,
)
from c2.forge.edits import TextEdit


def _fs(forge) -> FnSpan | None:
    return cspan.fnspan(forge.text, forge.function)


def _norm(s: str) -> str:
    return " ".join(s.split())


def _int_of(node) -> int | None:
    """Parse a number_literal node.  None for floats / parse failures."""
    if node is None or node.type != "number_literal":
        return None
    t = node.text.decode().rstrip("uUlL")
    try:
        return int(t, 0)
    except ValueError:
        return None


def _stmt_of(node):
    """Ascend to the statement that directly sits in a compound."""
    cur = node
    while cur is not None:
        p = cur.parent
        if p is not None and p.type == "compound_statement":
            return cur
        cur = p
    return None


def _starts_line(fs: FnSpan, node) -> bool:
    ls = fs.line_start(node.start_byte)
    return not fs.data[ls:node.start_byte].strip()


def _single_line(node) -> bool:
    return node.start_point[0] == node.end_point[0]


def _expr_of_stmt(stmt):
    """The expression inside an expression_statement (or None)."""
    if stmt is None or stmt.type != "expression_statement":
        return None
    kids = [c for c in stmt.named_children if c.type != "comment"]
    return kids[0] if len(kids) == 1 else None


def _else_arm(if_node):
    alt = if_node.child_by_field_name("alternative")
    if alt is None:
        return None
    if alt.type == "else_clause":
        kids = [c for c in alt.named_children if c.type != "comment"]
        return kids[0] if kids else None
    return alt


def _is_primary(node) -> bool:
    """Expression that needs no parens when embedded as an operand."""
    return node is not None and node.type in (
        "identifier", "number_literal", "char_literal",
        "parenthesized_expression", "call_expression",
        "field_expression", "subscript_expression",
    )


def _paren(fs: FnSpan, node) -> str:
    t = fs.src(node)
    return t if _is_primary(node) else f"({t})"


def _has_scoped_continue(body) -> bool:
    """``continue`` belonging to THIS loop (nested loops rescoped)."""
    stack = list(body.named_children)
    while stack:
        n = stack.pop()
        if n.type == "continue_statement":
            return True
        if n.type in ("for_statement", "while_statement", "do_statement"):
            continue                    # continue inside binds to that loop
        stack.extend(n.named_children)
    return False


def _top_decl_runs(fs: FnSpan) -> list[list]:
    """Runs of consecutive single-declarator, no-init, own-line decls
    in the top-level body (comments don't break a run)."""
    runs: list[list] = []
    cur: list = []
    for c in fs.body.named_children:
        if c.type == "comment":
            continue
        ok = False
        if c.type == "declaration" and _single_line(c) and fs.owns_line(c):
            declrs = c.children_by_field_name("declarator")
            if len(declrs) == 1 and declrs[0].type != "init_declarator":
                ok = True
        if ok:
            cur.append(c)
            continue
        if len(cur) >= 2:
            runs.append(cur)
        cur = []
        if c.type != "declaration":
            break                       # decl region ended (C89)
    if len(cur) >= 2:
        runs.append(cur)
    return runs


def _decl_name(decl) -> str | None:
    declrs = decl.children_by_field_name("declarator")
    if len(declrs) != 1:
        return None
    names = _declared_names(declrs[0])
    return next(iter(names)) if len(names) == 1 else None


def preset_tie_group(forge, **opts) -> int:
    """decl order + statement order -- the verified regalloc-tie group
    (the dominant lever family for ``fix_next=seat`` residues)."""
    n = 0
    n += preset_decl_swap_all(forge, **opts)
    n += preset_stmt_reorder_deep(forge, **opts)
    return n


def preset_decl_swap_all(forge, restrict=None, **opts) -> int:
    """One candidate per PAIR of decls in the same top-level run
    (Rule 115 seat ties).  ``restrict=[names...]`` narrows."""
    fs = _fs(forge)
    if fs is None:
        return 0
    restrict_set = set(restrict) if restrict else None
    n_added = 0
    for run in _top_decl_runs(fs):
        for a, b in itertools.combinations(run, 2):
            na, nb = _decl_name(a), _decl_name(b)
            if na is None or nb is None:
                continue
            if restrict_set is not None \
                    and na not in restrict_set and nb not in restrict_set:
                continue
            sa, ea = fs.full_line_span(a)
            sb, eb = fs.full_line_span(b)
            forge.candidate(
                f"swap_decls({na},{nb})",
                TextEdit(start=sa, end=ea,
                         replacement=fs.text[sb:eb], note="A<-B"),
                TextEdit(start=sb, end=eb,
                         replacement=fs.text[sa:ea], note="B<-A"),
            )
            n_added += 1
    return n_added


def preset_decl_perm(forge, max_run: int = 5, window: int = 4,
                     restrict=None, **opts) -> int:
    """Full-order permutations of small decl runs (windowed for long
    runs).  ``decl_swap_all`` reaches only TRANSPOSITIONS -- two swaps
    sharing a line overlap and can't compose -- so 3-cycles and deeper
    orders were unreachable.

    Evidence: 71669746 test_zone_for_closest_fire BYTE-EXACT (Rule 107
    slot order = a 7-decl permutation, previously solved only by an
    external shellsort sim); 980929b7 (Rule 115); 835f27a4, 3b10e7e9.
    """
    fs = _fs(forge)
    if fs is None:
        return 0
    restrict_set = set(restrict) if restrict else None
    n_added = 0
    for run in _top_decl_runs(fs):
        if len(run) < 3:
            continue
        spans = [fs.full_line_span(d) for d in run]
        texts = [fs.text[a:b] for a, b in spans]
        if restrict_set is not None:
            # TIGHT restricted mode: permute ONLY the positions of the
            # target-var decls among themselves (hold every other decl
            # fixed).  k target vars => k! orders, k capped by `window`.
            tgt = [i for i, d in enumerate(run)
                   if _decl_name(d) in restrict_set]
            if len(tgt) < 2:
                continue
            windows = [tgt[:window]]
        else:
            windows = ([list(range(len(run)))] if len(run) <= max_run else
                       [list(range(i, i + window))
                        for i in range(0, len(run) - window + 1)])
        for idxs in windows:
            for perm in itertools.permutations(idxs):
                if list(perm) == idxs:
                    continue
                edits = [TextEdit(start=spans[i][0], end=spans[i][1],
                                  replacement=texts[p])
                         for i, p in zip(idxs, perm) if i != p]
                order = ",".join(str(p) for p in perm)
                forge.candidate(
                    f"decl_perm(L{fs.line_no(run[idxs[0]])}:{order})",
                    *edits)
                n_added += 1
    return n_added


def preset_decl_init_split(forge, **opts) -> int:
    """Split init-decls into bare decl + first-statement assignment
    (strict-C89, observed-source-style §0 -- the corpus norm)."""
    fs = _fs(forge)
    if fs is None:
        return 0
    anchor = fs.top_decl_anchor()
    if anchor is None:
        return 0
    n_added = 0
    for c in fs.body.named_children:
        if c.type == "comment":
            continue
        if c.type != "declaration":
            break
        declrs = c.children_by_field_name("declarator")
        if len(declrs) != 1 or declrs[0].type != "init_declarator":
            continue
        if not (_single_line(c) and fs.owns_line(c)):
            continue
        inner = declrs[0].child_by_field_name("declarator")
        value = declrs[0].child_by_field_name("value")
        if inner is None or value is None:
            continue
        names = _declared_names(inner)
        if len(names) != 1:
            continue
        name = next(iter(names))
        ls, le = fs.full_line_span(c)
        indent = fs.text[ls:c.start_byte]
        bare = (f"{indent}"
                f"{fs.text[c.start_byte:inner.end_byte]};\n")
        forge.candidate(
            f"decl_init_split({name})",
            TextEdit(start=ls, end=le, replacement=bare,
                     note="strip init"),
            TextEdit(start=anchor, end=anchor,
                     replacement=f"    {name} = {fs.src(value)};\n",
                     note="insert assign"),
        )
        n_added += 1
    return n_added


def preset_decl_hoist(forge, **opts) -> int:
    """Hoist nested (block-scoped) declarations to the top-of-function
    decl run -- the strict-C89 corpus norm.

    PROVEN LEVER 2026-06-30 (show_battlemap_base L135): nested name
    births reorder the allocation queue's ConfBefore ties (§13).
    Emits one candidate per site PLUS one combined candidate per
    same-named group.  Init-decls hoist as bare decl + in-place
    assignment.
    """
    fs = _fs(forge)
    if fs is None:
        return 0
    anchor = fs.top_decl_anchor()
    if anchor is None:
        return 0
    top_names: set[str] = set()
    for c in fs.body.named_children:
        if c.type != "declaration":
            continue
        for d in c.children_by_field_name("declarator"):
            top_names |= _declared_names(d)

    sites: dict[str, list[tuple]] = {}
    for n in walk_named(fs.body):
        if n.type != "declaration" or n.parent is None \
                or n.parent.type != "compound_statement" \
                or n.parent == fs.body:
            continue
        if not (_single_line(n) and fs.owns_line(n)):
            continue
        declrs = n.children_by_field_name("declarator")
        if len(declrs) != 1:
            continue
        d = declrs[0]
        init_src = None
        inner = d
        if d.type == "init_declarator":
            inner = d.child_by_field_name("declarator")
            value = d.child_by_field_name("value")
            if inner is None or value is None:
                continue
            init_src = fs.src(value)
        names = _declared_names(inner)
        if len(names) != 1:
            continue
        name = next(iter(names))
        if name in top_names:
            continue
        tnode = n.child_by_field_name("type")
        if tnode is None:
            continue
        decl_body = f"{fs.src(tnode)} {fs.src(inner)}"
        sites.setdefault(name, []).append((n, decl_body, init_src, name))

    def _removal(node, name, init_src):
        ls, le = fs.full_line_span(node)
        if init_src is None:
            return TextEdit(start=ls, end=le, replacement="",
                            note="drop nested decl")
        indent = fs.text[ls:node.start_byte]
        return TextEdit(start=ls, end=le,
                        replacement=f"{indent}{name} = {init_src};\n",
                        note="decl -> assign")

    n_added = 0
    for name, occ in sites.items():
        decl_line = f"    {occ[0][1]};\n"
        for node, _body, init_src, _n in occ:
            forge.candidate(
                f"decl_hoist({name}@L{fs.line_no(node)})",
                _removal(node, name, init_src),
                TextEdit(start=anchor, end=anchor, replacement=decl_line,
                         note="hoisted decl"),
            )
            n_added += 1
        if len(occ) > 1:
            edits = [_removal(node, name, init_src)
                     for node, _b, init_src, _n in occ]
            edits.append(TextEdit(start=anchor, end=anchor,
                                  replacement=decl_line,
                                  note="hoisted decl (combined)"))
            forge.candidate(f"decl_hoist_all({name})", *edits)
            n_added += 1
    return n_added


def preset_stmt_reorder_deep(forge, call_permissive: bool = True,
                             restrict=None, **opts) -> int:
    """Every adjacent independent statement pair, at ANY nesting depth
    (the union of the old top-level-only ``stmt_swap_adjacent`` +
    ``firstassign`` levers, which this preset replaces).

    Evidence for depth: f6c90572 get_region_revolt_points (south-block
    order, inside an if-arm); 41b6cb00 get_fire_target (prev_range
    load moved inside a guard).

    Policy: scalar dependencies always block a swap.  A memory write
    blocks a swap against any statement touching memory (STRICTER than
    the old lever, which treated opaque lvalues as no-write).  Calls
    block a swap unless BOTH statements are bare local-scalar assigns
    -- the verified call-permissive firstassign policy.
    """
    fs = _fs(forge)
    if fs is None:
        return 0
    local_names = fs.local_names()
    restrict_set = set(restrict) if restrict else None

    def _mem_touch(stmt) -> bool:
        return any(n.type in ("subscript_expression", "field_expression",
                              "pointer_expression")
                   for n in walk_named(stmt))

    def _bare_scalar_assign(stmt) -> bool:
        e = _expr_of_stmt(stmt)
        if e is None or e.type != "assignment_expression":
            return False
        lhs = e.child_by_field_name("left")
        return lhs is not None and lhs.type == "identifier"

    n_added = 0
    for comp in fs.compounds():
        all_sts = fs.statements_of(comp)
        for i in range(len(all_sts) - 1):
            a, b = all_sts[i], all_sts[i + 1]
            if a.type != "expression_statement" \
                    or b.type != "expression_statement":
                continue
            rA, wA, cA = stmt_reads_writes(a)
            rB, wB, cB = stmt_reads_writes(b)
            if "*mem*" in wA or "*mem*" in wB:
                continue
            if (wA & (rB | wB)) or (wB & rA):
                continue
            wA_mem = any(w not in local_names for w in wA)
            wB_mem = any(w not in local_names for w in wB)
            if (wA_mem and _mem_touch(b)) or (wB_mem and _mem_touch(a)):
                continue
            if cA or cB:
                if not call_permissive:
                    continue
                if not (_bare_scalar_assign(a) and _bare_scalar_assign(b)):
                    continue
            if restrict_set is not None and not (
                    (rA | wA | rB | wB) & restrict_set):
                continue                # neither statement touches a target
            forge.candidate(
                f"swap_stmts(L{fs.line_no(a)},L{fs.line_no(b)})",
                TextEdit(start=a.start_byte, end=a.end_byte,
                         replacement=fs.src(b)),
                TextEdit(start=b.start_byte, end=b.end_byte,
                         replacement=fs.src(a)),
            )
            n_added += 1
    return n_added


def preset_stmt_swap_adjacent(forge, **opts) -> int:
    """Call-free variant of :func:`preset_stmt_reorder_deep` (kept as a
    named entry for older experiment files)."""
    opts.pop("call_permissive", None)
    return preset_stmt_reorder_deep(forge, call_permissive=False, **opts)


_COMMUTATIVE_OPS = frozenset({"+", "*", "&", "|", "^", "==", "!="})
_REL_FLIP = {"<": ">", "<=": ">=", ">": "<", ">=": "<="}


def _binops(fs: FnSpan):
    for n in walk_named(fs.body):
        if n.type != "binary_expression":
            continue
        op = n.child_by_field_name("operator")
        l = n.child_by_field_name("left")
        r = n.child_by_field_name("right")
        if op is None or l is None or r is None:
            continue
        yield n, op.text.decode(), l, r


def preset_commute_all(forge, op: str | None = None, restrict=None,
                       **opts) -> int:
    """One candidate per commutable binop (operand emit order -- the
    Rule 28a/4 family; e.g. 7bdd8da9 start_move BYTE-EXACT via
    ``(x + y*0x34)`` operand order)."""
    fs = _fs(forge)
    if fs is None:
        return 0
    restrict_set = set(restrict) if restrict else None
    n_added = 0
    for n, op_t, l, r in _binops(fs):
        if op_t not in _COMMUTATIVE_OPS or (op is not None and op_t != op):
            continue
        lt, rt = fs.src(l), fs.src(r)
        if _norm(lt) == _norm(rt):
            continue
        if not (side_effect_free(l) and side_effect_free(r)):
            continue                    # order of effects must not change
        if restrict_set is not None and not (
                (identifiers(l) | identifiers(r)) & restrict_set):
            continue                    # binop doesn't touch a target var
        forge.candidate(
            f"commute({op_t}@L{fs.line_no(n)})",
            TextEdit(start=l.start_byte, end=r.end_byte,
                     replacement=f"{_paren(fs, r)} {op_t} {_paren(fs, l)}"),
        )
        n_added += 1
    return n_added


def preset_relorder_all(forge, **opts) -> int:
    """Swap+flip every relational compare (``a < b`` -> ``b > a`` --
    semantics-preserving, flips the cmp emit order; Rule 4 family,
    e.g. 980929b7 stage-2 count-first compares)."""
    fs = _fs(forge)
    if fs is None:
        return 0
    n_added = 0
    for n, op_t, l, r in _binops(fs):
        if op_t not in _REL_FLIP:
            continue
        lt, rt = fs.src(l), fs.src(r)
        if _norm(lt) == _norm(rt):
            continue
        if not (side_effect_free(l) and side_effect_free(r)):
            continue
        forge.candidate(
            f"relorder({op_t}@L{fs.line_no(n)})",
            TextEdit(start=l.start_byte, end=r.end_byte,
                     replacement=(f"{_paren(fs, r)} {_REL_FLIP[op_t]} "
                                  f"{_paren(fs, l)}")),
        )
        n_added += 1
    return n_added


#: The native integer scalar types the sweep tries.  Every register
#: class / width / signedness a Watcom 10.0a int-family local can take.
#: float/double are deliberately EXCLUDED: they are not register-class-
#: compatible with an integer local (bit/integer ops fail or change
#: meaning), so they only waste compiles.
#: Exactly the DISTINCT codegen classes on the PS target (-4r, 32-bit,
#: unsigned-char default).  The redundant spellings are aliased away
#: below -- on this target they produce BYTE-IDENTICAL code, so sweeping
#: them is pure wasted probes (~1/3 of the type/cast sweep):
#:   char        == unsigned char   (unsigned-char default, no -j)
#:   long        == int             (both 32-bit)
#:   unsigned long == unsigned int  (both 32-bit)
NATIVE_INT_TYPES: tuple[str, ...] = (
    "signed char", "unsigned char",
    "short", "unsigned short",
    "int", "unsigned int",
)

#: Every other integer spelling collapsed to its canonical distinct
#: class above, so the sweep never emits a byte-identical re-spelling
#: (of a local's own type OR as a target).
_TYPE_ALIASES: dict[str, str] = {
    "char": "unsigned char",
    "signed": "int", "signed int": "int",
    "unsigned": "unsigned int",
    "short int": "short", "signed short": "short",
    "signed short int": "short", "unsigned short int": "unsigned short",
    "long": "int", "long int": "int", "signed long": "int",
    "signed long int": "int",
    "unsigned long": "unsigned int", "unsigned long int": "unsigned int",
}


def _canon_int_type(s: str) -> str | None:
    """Canonical native-integer type for ``s`` (alias-collapsed), or
    ``None`` when ``s`` is not a native integer scalar (pointer,
    struct, float, typedef -- left untouched by the sweep)."""
    t = _TYPE_ALIASES.get(_norm(s), _norm(s))
    return t if t in NATIVE_INT_TYPES else None


def preset_type_sweep(forge, restrict=None, **opts) -> int:
    """Every native-integer local x every OTHER native integer type
    (char/short/int/long, signed AND unsigned), at any depth.

    The sweep is width- and sign-AGNOSTIC on purpose: it does NOT
    trust the declared type or its width (a wrong-width / wrong-sign
    local is one of the commonest shape defects -- Rule 151 -- and a
    byte-neutral width/class change is a proven regalloc-seat
    perturbation, the lever that reaches ``city_test_for_road``'s
    seat=0 bridge basin).  Width fixes were the ROOT of several wins
    (980929b7 count_archers short->int; a3286ce2 loop counter int not
    unsigned short; f76bc477 signed-char gate)."""
    fs = _fs(forge)
    if fs is None:
        return 0
    restrict_set = set(restrict) if restrict else None
    n_added = 0
    seen: set[str] = set()
    for n in walk_named(fs.body):
        if n.type != "declaration":
            continue
        declrs = n.children_by_field_name("declarator")
        if len(declrs) != 1:
            continue
        d = declrs[0]
        if d.type == "init_declarator":
            d = d.child_by_field_name("declarator")
        if d is None or d.type != "identifier":
            continue                    # pointers/arrays: type is riskier
        name = d.text.decode()
        if name in seen:
            continue
        if restrict_set is not None and name not in restrict_set:
            continue
        tnode = n.child_by_field_name("type")
        if tnode is None:
            continue
        cur = _canon_int_type(fs.src(tnode))
        if cur is None:
            continue                    # not a native integer scalar
        seen.add(name)
        for t in NATIVE_INT_TYPES:
            if t == cur:
                continue
            forge.candidate(
                f"type({name}={t})",
                TextEdit(start=tnode.start_byte, end=tnode.end_byte,
                         replacement=t),
            )
            n_added += 1
    return n_added


def _fn_declarator_name(declarator):
    """Innermost function_declarator identifier text for a declarator
    subtree, or None."""
    cur = declarator
    while cur is not None:
        if cur.type == "function_declarator":
            ident = cur.child_by_field_name("declarator")
            if ident is not None and ident.type == "identifier":
                return ident.text.decode(), cur
            return None, cur
        cur = cur.child_by_field_name("declarator")
    return None, None


def _param_type_nodes(func_declarator):
    """Ordered list of (parameter_declaration, type_node,
    declarator_node) for a function_declarator's parameter list."""
    out = []
    plist = func_declarator.child_by_field_name("parameters")
    if plist is None:
        for c in func_declarator.named_children:
            if c.type == "parameter_list":
                plist = c
                break
    if plist is None:
        return out
    for pd in plist.named_children:
        if pd.type != "parameter_declaration":
            continue
        out.append((pd, pd.child_by_field_name("type"),
                    pd.child_by_field_name("declarator")))
    return out


def preset_param_type_sweep(forge, restrict=None, **opts) -> int:
    """Every native-integer PARAMETER of the function x every OTHER
    native integer type (char/short/int/long, signed AND unsigned).

    The signature sibling of :func:`preset_type_sweep`.  A parameter
    typed ``int`` where PS declared it ``signed char`` (its actual
    field type) is byte-INVISIBLE at its own use site -- __watcall
    passes it in a full register, so every decompiler (Watcom, Mac,
    MSVC) types it ``int`` with a ``(char)`` cast -- yet the wrong
    dword conflict class reseats an UNRELATED equal-savings register
    tie elsewhere in the body.  ``city_test_for_road`` was byte-exact
    the instant ``world_dir`` became ``signed char`` (a64b9900): the
    x/y EDI/EBP seat flipped with zero other byte change.  When a seat
    tie resists every statement-shape lever, the defect is often a
    param width/sign three arguments away.

    Each candidate re-types the parameter in BOTH the definition and
    every matching same-TU prototype declaration, so the variant
    compiles (a prototype/definition type mismatch is a hard C error).
    """
    fs = _fs(forge)
    if fs is None:
        return 0
    restrict_set = set(restrict) if restrict else None
    decl = fs.fn_node.child_by_field_name("declarator")
    name, func_declarator = _fn_declarator_name(decl)
    if func_declarator is None:
        return 0
    def_params = _param_type_nodes(func_declarator)

    # Same-TU prototype declarations of this function: map param index
    # -> list of type nodes to keep in sync with the definition.
    proto_types: dict[int, list] = {}
    root = fs.fn_node.parent
    if root is not None:
        for n in root.named_children:
            if n.type != "declaration":
                continue
            pname, pfd = _fn_declarator_name(
                n.child_by_field_name("declarator"))
            if pfd is None or pname != name:
                continue
            for i, (_pd, ptn, _pdc) in enumerate(_param_type_nodes(pfd)):
                if ptn is not None:
                    proto_types.setdefault(i, []).append(ptn)

    n_added = 0
    for i, (_pd, tnode, dnode) in enumerate(def_params):
        if tnode is None or dnode is None:
            continue
        if dnode.type != "identifier":
            continue                    # pointers/arrays: type is riskier
        pname = dnode.text.decode()
        if restrict_set is not None and pname not in restrict_set:
            continue
        cur = _canon_int_type(fs.src(tnode))
        if cur is None:
            continue                    # not a native integer scalar
        for t in NATIVE_INT_TYPES:
            if t == cur:
                continue
            edits = [TextEdit(start=tnode.start_byte, end=tnode.end_byte,
                              replacement=t)]
            for ptn in proto_types.get(i, ()):
                edits.append(TextEdit(start=ptn.start_byte,
                                      end=ptn.end_byte, replacement=t))
            forge.candidate(f"paramtype({pname}={t})", *edits)
            n_added += 1
    return n_added


def preset_shift1(forge, **opts) -> int:
    """``x << 1``  <->  ``x + x`` toggles (both parenthesised -- the
    surrounding context may bind tighter than the new operator)."""
    fs = _fs(forge)
    if fs is None:
        return 0
    n_added = 0
    for n, op_t, l, r in _binops(fs):
        if op_t == "<<" and _int_of(unparen(r)) == 1 \
                and l.type == "identifier":
            ident = fs.src(l)
            forge.candidate(
                f"shift1->add({ident}@L{fs.line_no(n)})",
                TextEdit(start=n.start_byte, end=n.end_byte,
                         replacement=f"({ident} + {ident})"),
            )
            n_added += 1
        elif op_t == "+" and l.type == "identifier" \
                and r.type == "identifier" and fs.src(l) == fs.src(r):
            ident = fs.src(l)
            forge.candidate(
                f"add->shift1({ident}@L{fs.line_no(n)})",
                TextEdit(start=n.start_byte, end=n.end_byte,
                         replacement=f"({ident} << 1)"),
            )
            n_added += 1
    return n_added


def preset_bytemask(forge, **opts) -> int:
    """``E & 0xff``  ->  ``(unsigned char)E`` (low-byte realisation
    toggle)."""
    fs = _fs(forge)
    if fs is None:
        return 0
    n_added = 0
    for n, op_t, l, r in _binops(fs):
        if op_t != "&" or _int_of(unparen(r)) != 0xFF:
            continue
        if not side_effect_free(l):
            continue
        forge.candidate(
            f"and0xff->ucast(L{fs.line_no(n)})",
            TextEdit(start=n.start_byte, end=n.end_byte,
                     replacement=f"(unsigned char){_paren(fs, l)}"),
        )
        n_added += 1
    return n_added


_RMW_OPS = frozenset({"&", "|", "^", "+", "-", "*", "/", "%", "<<", ">>"})


def preset_compound_assign_expand(forge, **opts) -> int:
    """``x OP= E``  ->  ``x = x OP E`` (Rule 17b RMW realisation
    family; safe lvalues only, so nothing is double-evaluated)."""
    fs = _fs(forge)
    if fs is None:
        return 0
    n_added = 0
    for st in fs.nodes("expression_statement"):
        e = _expr_of_stmt(st)
        if e is None or e.type != "assignment_expression":
            continue
        op = e.child_by_field_name("operator")
        lv = e.child_by_field_name("left")
        rhs = e.child_by_field_name("right")
        if op is None or lv is None or rhs is None:
            continue
        op_t = op.text.decode()
        if not op_t.endswith("=") or op_t in ("=", "==", "<=", ">=", "!="):
            continue
        if not side_effect_free(lv):
            continue
        binop = op_t[:-1]
        lv_t = fs.src(lv)
        forge.candidate(
            f"compound_expand({op_t}@L{fs.line_no(st)})",
            TextEdit(start=e.start_byte, end=e.end_byte,
                     replacement=f"{lv_t} = {lv_t} {binop} "
                                 f"{_paren(fs, rhs)}"),
        )
        n_added += 1
    return n_added


def preset_compound_assign_contract(forge, **opts) -> int:
    """``x = x OP E``  ->  ``x OP= E`` (the reverse direction; both
    directions are codegen-load-bearing on memory lvalues)."""
    fs = _fs(forge)
    if fs is None:
        return 0
    n_added = 0
    for st in fs.nodes("expression_statement"):
        e = _expr_of_stmt(st)
        if e is None or e.type != "assignment_expression":
            continue
        op = e.child_by_field_name("operator")
        lv = e.child_by_field_name("left")
        rhs = unparen(e.child_by_field_name("right"))
        if op is None or op.text != b"=" or lv is None or rhs is None:
            continue
        if rhs.type != "binary_expression" or not side_effect_free(lv):
            continue
        rop = rhs.child_by_field_name("operator")
        rl = rhs.child_by_field_name("left")
        rr = rhs.child_by_field_name("right")
        if rop is None or rl is None or rr is None:
            continue
        rop_t = rop.text.decode()
        if rop_t not in _RMW_OPS or _norm(fs.src(rl)) != _norm(fs.src(lv)):
            continue
        forge.candidate(
            f"compound_contract({rop_t}=@L{fs.line_no(st)})",
            TextEdit(start=e.start_byte, end=e.end_byte,
                     replacement=f"{fs.src(lv)} {rop_t}= {fs.src(rr)}"),
        )
        n_added += 1
    return n_added


def preset_incdec_toggle(forge, **opts) -> int:
    """``x++;`` <-> ``x += 1;`` <-> ``x = x + 1;`` statement forms
    (Rule 17b; selects ``inc [m]`` vs load/add/store)."""
    fs = _fs(forge)
    if fs is None:
        return 0
    n_added = 0
    for st in fs.nodes("expression_statement"):
        e = _expr_of_stmt(st)
        if e is None:
            continue
        if e.type == "update_expression":
            arg = e.child_by_field_name("argument")
            op = e.child_by_field_name("operator")
            if arg is None or op is None or not side_effect_free(arg):
                continue
            sign = "+" if op.text == b"++" else "-"
            lv = fs.src(arg)
            for tag, repl in ((f"cmpd", f"{lv} {sign}= 1"),
                              (f"full", f"{lv} = {lv} {sign} 1")):
                forge.candidate(
                    f"incdec_{tag}({lv}@L{fs.line_no(st)})",
                    TextEdit(start=e.start_byte, end=e.end_byte,
                             replacement=repl),
                )
                n_added += 1
        elif e.type == "assignment_expression":
            op = e.child_by_field_name("operator")
            lv = e.child_by_field_name("left")
            rhs = e.child_by_field_name("right")
            if op is None or lv is None \
                    or op.text.decode() not in ("+=", "-=") \
                    or _int_of(unparen(rhs)) != 1 \
                    or not side_effect_free(lv):
                continue
            sign = "++" if op.text == b"+=" else "--"
            forge.candidate(
                f"incdec_bare({fs.src(lv)}@L{fs.line_no(st)})",
                TextEdit(start=e.start_byte, end=e.end_byte,
                         replacement=f"{fs.src(lv)}{sign}"),
            )
            n_added += 1
    return n_added


def _del_stmt_edit(fs: FnSpan, stmt, note: str) -> TextEdit:
    """Delete a statement: the whole line block when the statement owns
    it, otherwise just the statement span + trailing whitespace (packed
    lines -- 1b731cfd find_enemy packs assign + guard on ONE line)."""
    if _single_line(stmt) and fs.owns_line(stmt):
        s, e = fs.full_line_span(stmt)
        return TextEdit(start=s, end=e, replacement="", note=note)
    end = stmt.end_byte
    while end < len(fs.text) and fs.text[end] in " \t":
        end += 1
    return TextEdit(start=stmt.start_byte, end=end, replacement="",
                    note=note)


def de_invent_candidates(forge, only: str | None = None) -> int:
    """The Rule 67 / §10 de-invent lever, exact-span edition.

    Covers both corpus forms (``T x = E;`` init-decls and the
    strict-C89 ``T x; ... x = E;`` split) with byte-exact occurrence
    replacement -- multiple reads on one PACKED line are handled
    (1b731cfd find_enemy's ``xx < x_lo || xx >= x_hi`` guards were
    unreachable for the old line-regex implementation).

    Safety: exactly one write, side-effect-free RHS, every read
    strictly after the write, address never taken, and no identifier
    of the RHS is re-written (nor any call made, when the RHS reads
    non-local state) between the write and the last read.
    """
    fs = _fs(forge)
    if fs is None:
        return 0
    local_safe = fs.call_free_locals()
    n_added = 0
    for c in fs.body.named_children:
        if c.type == "comment":
            continue
        if c.type != "declaration":
            break
        declrs = c.children_by_field_name("declarator")
        if len(declrs) != 1 or not (_single_line(c) and fs.owns_line(c)):
            continue
        d = declrs[0]
        init_value = None
        inner = d
        if d.type == "init_declarator":
            inner = d.child_by_field_name("declarator")
            init_value = d.child_by_field_name("value")
        if inner is None or inner.type != "identifier":
            continue
        name = inner.text.decode()
        if only is not None and name != only:
            continue

        # occurrences outside the decl
        occs = [n for n in walk_named(fs.body)
                if n.type == "identifier" and n.text.decode() == name
                and not (c.start_byte <= n.start_byte < c.end_byte)
                and not (n.parent is not None
                         and n.parent.type == "field_expression"
                         and n.parent.child_by_field_name("field") == n)]
        occs.sort(key=lambda n: n.start_byte)
        writes, reads, addr = [], [], False
        for n in occs:
            p = n.parent
            if p is not None and p.type == "assignment_expression" \
                    and p.child_by_field_name("left") == n:
                writes.append(p)
            elif p is not None and p.type == "update_expression":
                writes.append(p)
                writes.append(p)        # counts as 2: never eligible
            elif p is not None and p.type == "pointer_expression" \
                    and p.child(0) is not None \
                    and p.child(0).type == "&":
                addr = True
            else:
                reads.append(n)
        if addr or not reads:
            continue

        if init_value is not None:
            if writes:
                continue
            rhs_node = init_value
            write_end = c.end_byte
            del_edits = [TextEdit(*fs.full_line_span(c), replacement="",
                                  note="delete decl")]
            tag = f"de_invent({name})"
        else:
            if len(writes) != 1:
                continue
            w = writes[0]
            if w.type != "assignment_expression":
                continue
            wop = w.child_by_field_name("operator")
            rhs_node = w.child_by_field_name("right")
            if wop is None or wop.text != b"=" or rhs_node is None:
                continue
            wst = _stmt_of(w)
            if wst is None or _expr_of_stmt(wst) != w:
                continue
            write_end = w.end_byte
            del_edits = [
                TextEdit(*fs.full_line_span(c), replacement="",
                         note="delete decl"),
                _del_stmt_edit(fs, wst, "delete assign"),
            ]
            tag = f"de_invent_split({name})"

        if not side_effect_free(rhs_node):
            continue
        if any(r.start_byte < write_end for r in reads):
            continue
        last_read = max(r.end_byte for r in reads)
        rhs_ids = identifiers(rhs_node)
        rhs_volatile = not rhs_ids <= local_safe
        # hazards between the write and each read: a call (when the
        # RHS reads non-local state) or a write to an RHS input.  A
        # call whose ARGUMENT is the read itself is NOT a hazard --
        # arguments are evaluated before the callee runs.
        hazards: list[tuple[int, int, str]] = []
        for n in walk_named(fs.body):
            if n.end_byte <= write_end or n.start_byte >= last_read:
                continue
            if n.type == "call_expression" and rhs_volatile:
                hazards.append((n.start_byte, n.end_byte, "call"))
            elif n.type in ("assignment_expression", "update_expression"):
                lhs = (n.child_by_field_name("left")
                       if n.type == "assignment_expression"
                       else n.child_by_field_name("argument"))
                base = lvalue_base(lhs) if lhs is not None else None
                if base is None or base in rhs_ids:
                    hazards.append((n.start_byte, n.end_byte, "write"))
        stable = True
        for r in reads:
            for hs, he, kind in hazards:
                if hs < write_end:
                    continue
                if kind == "call" and he <= r.start_byte:
                    stable = False      # completed call before this read
                elif kind == "write" and hs < r.start_byte:
                    stable = False      # write before (or around) read
            if not stable:
                break
        if not stable:
            continue
        rhs_text = fs.src(rhs_node)
        edits = del_edits + [
            TextEdit(start=r.start_byte, end=r.end_byte,
                     replacement=f"({rhs_text})",
                     note=f"inline@L{fs.line_no(r)}")
            for r in reads
        ]
        forge.candidate(tag, *edits)
        n_added += 1
    return n_added


def preset_de_invent_all(forge, **opts) -> int:
    """Inline every eligible single-assignment local (§13's 5x
    over-decompiled-mirror corpus signal; wins: 1b731cfd find_enemy,
    cbd82c7d city_test_for_road, 8f62a35a transform_wall_elastic,
    5cda69fb place2_sprite tile, c065aafd rot, ...)."""
    return de_invent_candidates(forge)


def preset_cache_literal(forge, type_: str = "int", **opts) -> int:
    """Repeated int literal as the full RHS of >= 2 plain assignments
    -> named local (the sprite_default pattern; reverse of de_invent).
    Skips 0/1 (too idiomatic)."""
    fs = _fs(forge)
    if fs is None:
        return 0
    anchor = fs.top_decl_anchor()
    if anchor is None:
        return 0
    taken = fs.local_names()
    uses: dict[str, list] = {}
    for st in fs.nodes("expression_statement"):
        e = _expr_of_stmt(st)
        if e is None or e.type != "assignment_expression":
            continue
        op = e.child_by_field_name("operator")
        rhs = e.child_by_field_name("right")
        if op is None or op.text != b"=" or rhs is None \
                or rhs.type != "number_literal":
            continue
        v = _int_of(rhs)
        if v is None or v in (0, 1):
            continue
        uses.setdefault(rhs.text.decode(), []).append(rhs)
    n_added = 0
    for val, nodes in uses.items():
        if len(nodes) < 2:
            continue
        cname = f"c_{val.lower()}"
        if cname in taken or not cname.replace("_", "").isalnum():
            continue
        edits = [TextEdit(start=anchor, end=anchor,
                          replacement=f"    {type_} {cname} = {val};\n",
                          note="literal cache decl")]
        edits += [TextEdit(start=n.start_byte, end=n.end_byte,
                           replacement=cname,
                           note=f"use cache@L{fs.line_no(n)}")
                  for n in nodes]
        forge.candidate(f"cache_literal({val})", *edits)
        n_added += 1
    return n_added


def _header_close(fs: FnSpan, node):
    """The ')' closing a for/while header (last ')' before the body)."""
    body = node.child_by_field_name("body")
    close = None
    for c in node.children:
        if c.type == ")" and (body is None or c.start_byte < body.start_byte):
            close = c
    return close


def preset_loop_form(forge, **opts) -> int:
    """``for (init; cond; post)``  ->  ``init; while (cond) { ... post; }``
    (the -d1 line-stream / treegen-temp-order toggle; PS mixes both)."""
    fs = _fs(forge)
    if fs is None:
        return 0
    n_added = 0
    for node in fs.nodes("for_statement"):
        cond = node.child_by_field_name("condition")
        update = node.child_by_field_name("update")
        init = node.child_by_field_name("initializer")
        body = node.child_by_field_name("body")
        if cond is None or update is None or body is None \
                or body.type != "compound_statement":
            continue
        if init is not None and init.type == "declaration":
            continue                    # C99 for-init: not corpus-legal
        if _has_scoped_continue(body):
            continue
        close = _header_close(fs, node)
        if close is None or not _single_line(node.children[0]):
            continue
        if node.start_point[0] != close.start_point[0]:
            continue                    # multi-line header: skip
        indent = fs.indent_of(node)
        brace_line_start = fs.line_start(body.end_byte - 1)
        edits = []
        if init is not None:
            edits.append(TextEdit(
                start=fs.line_start(node.start_byte),
                end=fs.line_start(node.start_byte),
                replacement=f"{indent}{fs.src(init).rstrip(';')};\n",
                note="init stmt"))
        edits.append(TextEdit(
            start=node.start_byte, end=close.end_byte,
            replacement=f"while ({fs.src(cond).rstrip(';')})",
            note="for -> while"))
        edits.append(TextEdit(
            start=brace_line_start, end=brace_line_start,
            replacement=f"{indent}    {fs.src(update)};\n",
            note="trailing post"))
        forge.candidate(f"loop_form(while@L{fs.line_no(node)})", *edits)
        n_added += 1
    return n_added


def _is_simple_post(fs: FnSpan, stmt) -> bool:
    e = _expr_of_stmt(stmt)
    if e is None:
        return False
    if any(n.type == "call_expression" for n in walk_named(e)):
        return False
    return e.type in ("assignment_expression", "update_expression")


def preset_while_rotate(forge, **opts) -> int:
    """``while (cond) {..; post}``  ->  ``for ( ; cond; post[, post2])``
    (Rule 134 ROTATED form -- the test_elastic_range loop family;
    INVERSE of loop_form)."""
    fs = _fs(forge)
    if fs is None:
        return 0
    n_added = 0
    for node in fs.nodes("while_statement"):
        cond = node.child_by_field_name("condition")
        body = node.child_by_field_name("body")
        if cond is None or body is None \
                or body.type != "compound_statement":
            continue
        if _has_scoped_continue(body):
            continue
        sts = fs.statements_of(body)
        if not sts:
            continue
        close = _header_close(fs, node)
        if close is None or node.start_point[0] != close.start_point[0]:
            continue
        posts = []
        for st in reversed(sts[-2:]):
            if _is_simple_post(fs, st) and _single_line(st) \
                    and fs.owns_line(st):
                posts.insert(0, st)
            else:
                break
        if not posts or len(posts) >= len(sts):
            continue
        cond_t = fs.src(unparen(cond))
        variants = [posts[-1:]]
        if len(posts) == 2:
            variants.append(posts)
        for spans in variants:
            post_t = ", ".join(fs.src(_expr_of_stmt(s)) for s in spans)
            edits = [TextEdit(start=node.start_byte, end=close.end_byte,
                              replacement=f"for ( ; {cond_t}; {post_t})",
                              note="while -> rotated for")]
            edits += [TextEdit(*fs.full_line_span(s), replacement="",
                               note="post moved to for clause")
                      for s in spans]
            forge.candidate(
                f"while_rotate(L{fs.line_no(node)}"
                f"{'x2' if len(spans) == 2 else ''})", *edits)
            n_added += 1
    return n_added


def preset_ternary_split(forge, **opts) -> int:
    """``lv = c ? a : b;``  ->  ``if (c) lv = a; else lv = b;`` (the
    byte-zero false-arm ``xor al,al`` family)."""
    fs = _fs(forge)
    if fs is None:
        return 0
    n_added = 0
    for st in fs.nodes("expression_statement"):
        e = _expr_of_stmt(st)
        if e is None or e.type != "assignment_expression":
            continue
        op = e.child_by_field_name("operator")
        lv = e.child_by_field_name("left")
        rhs = unparen(e.child_by_field_name("right"))
        if op is None or op.text != b"=" or lv is None or rhs is None \
                or rhs.type != "conditional_expression":
            continue
        if any(n.type == "call_expression" for n in walk_named(st)):
            continue
        if not (_starts_line(fs, st) and fs.owns_line(st)):
            continue
        cond = unparen(rhs.child_by_field_name("condition"))
        a = rhs.child_by_field_name("consequence")
        b = rhs.child_by_field_name("alternative")
        if cond is None or a is None or b is None:
            continue
        indent = fs.indent_of(st)
        lv_t = fs.src(lv)
        repl = (f"if ({fs.src(cond)})\n"
                f"{indent}    {lv_t} = {fs.src(a)};\n"
                f"{indent}else\n"
                f"{indent}    {lv_t} = {fs.src(b)};")
        forge.candidate(
            f"ternary_split(L{fs.line_no(st)})",
            TextEdit(start=st.start_byte, end=st.end_byte,
                     replacement=repl, note="?: -> if/else"),
        )
        n_added += 1
    return n_added


def preset_if_fission(forge, **opts) -> int:
    """Split the LAST statement out of each arm of a fused ``if/else``
    into a second conditional re-testing the SAME condition.

    Evidence: 980929b7 setup_roman_units BYTE-EXACT (all four unit
    stages: PS re-tests ``bat_size <= count`` for the count update --
    L740/L746/L752/L758); f64c2951 setup_enemy_units stages 4/5.

    Safety: the condition is side-effect-free, reads only never-
    address-taken locals (calls in the heads can't touch them), and no
    head statement writes any of its inputs.
    """
    fs = _fs(forge)
    if fs is None:
        return 0
    safe = fs.call_free_locals()
    n_added = 0
    for ifn in fs.nodes("if_statement"):
        cond = ifn.child_by_field_name("condition")
        cons = ifn.child_by_field_name("consequence")
        alt = _else_arm(ifn)
        if cond is None or cons is None or alt is None:
            continue
        if cons.type != "compound_statement" \
                or alt.type != "compound_statement":
            continue
        arm_a = fs.statements_of(cons)
        arm_b = fs.statements_of(alt)
        if len(arm_a) < 2 or len(arm_b) < 2:
            continue
        cexpr = unparen(cond)
        if cexpr is None or not side_effect_free(cexpr):
            continue
        cond_ids = identifiers(cexpr)
        if not cond_ids or not cond_ids <= safe:
            continue
        heads = arm_a[:-1] + arm_b[:-1]
        if any(stmt_reads_writes(h)[1] & cond_ids for h in heads):
            continue
        tail_a, tail_b = arm_a[-1], arm_b[-1]
        if any(t.type != "expression_statement" or not _single_line(t)
               or not fs.owns_line(t) for t in (tail_a, tail_b)):
            continue
        indent = fs.indent_of(ifn)
        insert_at = fs.line_end(ifn.end_byte - 1)
        new_if = (f"{indent}if ({fs.src(cexpr)})\n"
                  f"{indent}    {fs.src(tail_a)}\n"
                  f"{indent}else\n"
                  f"{indent}    {fs.src(tail_b)}\n")
        forge.candidate(
            f"if_fission(L{fs.line_no(ifn)})",
            TextEdit(*fs.full_line_span(tail_a), replacement="",
                     note="pull tail A"),
            TextEdit(*fs.full_line_span(tail_b), replacement="",
                     note="pull tail B"),
            TextEdit(start=insert_at, end=insert_at, replacement=new_if,
                     note="re-test conditional"),
        )
        n_added += 1
    return n_added


_REL_NEG = {"<": ">=", "<=": ">", ">": "<=", ">=": "<",
            "==": "!=", "!=": "=="}


def preset_if_invert(forge, **opts) -> int:
    """``if (a < b) X else Y``  ->  ``if (a >= b) Y else X``
    (semantics-preserving condition negation with arm swap -- flips
    which arm is the fall-through and the cmp/jcc polarity).

    Evidence: 980929b7 setup_roman_units BYTE-EXACT (PS tests
    ``bat_size <= count`` where RC tested ``count < bat_size`` with
    swapped arms, all four stages); 71669746 test_zone_for_closest_fire
    (``min_cov >= 100`` polarity).
    """
    fs = _fs(forge)
    if fs is None:
        return 0
    n_added = 0
    for ifn in fs.nodes("if_statement"):
        cond = ifn.child_by_field_name("condition")
        cons = ifn.child_by_field_name("consequence")
        alt = _else_arm(ifn)
        if cond is None or cons is None or alt is None:
            continue
        if alt.type == "if_statement":
            continue                    # else-if chain: polarity is load-bearing
        c = unparen(cond)
        if c is None or c.type != "binary_expression" \
                or not side_effect_free(c):
            continue
        op = c.child_by_field_name("operator")
        l = c.child_by_field_name("left")
        r = c.child_by_field_name("right")
        if op is None or l is None or r is None:
            continue
        neg = _REL_NEG.get(op.text.decode())
        if neg is None:
            continue
        # both arms swap textually; require shape parity so the
        # indentation stays sane
        if (cons.type == "compound_statement") != \
                (alt.type == "compound_statement"):
            continue
        forge.candidate(
            f"if_invert(L{fs.line_no(ifn)})",
            TextEdit(start=l.start_byte, end=r.end_byte,
                     replacement=f"{fs.src(l)} {neg} {fs.src(r)}",
                     note="negate cond"),
            TextEdit(start=cons.start_byte, end=cons.end_byte,
                     replacement=fs.src(alt), note="arm X<-Y"),
            TextEdit(start=alt.start_byte, end=alt.end_byte,
                     replacement=fs.src(cons), note="arm Y<-X"),
        )
        n_added += 1
    return n_added


def preset_guard_const(forge, **opts) -> int:
    """Inside an arm guarded by ``v == K`` (or the else-arm of
    ``v != K``, or a ternary), replace each pre-write READ of ``v``
    with the literal ``K``.  With K == 1 and an enclosing ``x += v`` /
    ``x -= v``, additionally offer ``x++;`` / ``x--;``.

    Evidence: 82c4be1b / 00715fa8 road_ramifications BYTE-EXACT
    (``(x == 79) ? x : x + 1`` -> ``? 79 :`` clamp arms); fd93151a 3x
    build_*_from_elastic BYTE-EXACT (``x += best_elastic_dirc`` ->
    ``x++`` under ``else if (best_elastic_dirc == 1)``).
    """
    fs = _fs(forge)
    if fs is None:
        return 0
    n_added = 0
    sites: list[tuple] = []

    def _eq_guard(cond):
        c = unparen(cond)
        if c is None or c.type != "binary_expression":
            return None
        op = c.child_by_field_name("operator")
        l = unparen(c.child_by_field_name("left"))
        r = unparen(c.child_by_field_name("right"))
        if op is None or l is None or r is None:
            return None
        op_t = op.text.decode()
        if op_t not in ("==", "!="):
            return None
        for ident, lit in ((l, r), (r, l)):
            if ident.type == "identifier" and _int_of(lit) is not None:
                return ident.text.decode(), lit.text.decode(), op_t
        return None

    for ifn in fs.nodes("if_statement"):
        g = _eq_guard(ifn.child_by_field_name("condition"))
        if g is None:
            continue
        var, k_text, op_t = g
        arm = (ifn.child_by_field_name("consequence") if op_t == "=="
               else _else_arm(ifn))
        if arm is not None:
            sites.append((var, k_text, arm))
    for tern in fs.nodes("conditional_expression"):
        g = _eq_guard(tern.child_by_field_name("condition"))
        if g is None:
            continue
        var, k_text, op_t = g
        arm = tern.child_by_field_name(
            "consequence" if op_t == "==" else "alternative")
        if arm is not None:
            sites.append((var, k_text, arm))

    for var, k_text, arm in sites:
        occs = sorted(
            (n for n in walk_named(arm)
             if n.type == "identifier" and n.text.decode() == var),
            key=lambda n: n.start_byte)
        first_write = None
        reads = []
        for n in occs:
            p = n.parent
            if p is not None and (
                    (p.type == "assignment_expression"
                     and p.child_by_field_name("left") == n)
                    or p.type == "update_expression"
                    or (p.type == "pointer_expression"
                        and p.child(0) is not None
                        and p.child(0).type == "&")):
                first_write = n.start_byte
                break
            reads.append(n)
        for n in reads:
            if first_write is not None and n.start_byte >= first_write:
                continue
            line = fs.line_no(n)
            forge.candidate(
                f"guard_const({var}={k_text}@L{line})",
                TextEdit(start=n.start_byte, end=n.end_byte,
                         replacement=k_text),
            )
            n_added += 1
            if k_text.strip() in ("1", "0x1"):
                p = n.parent
                if p is not None and p.type == "assignment_expression" \
                        and unparen(p.child_by_field_name("right")) == n:
                    op = p.child_by_field_name("operator")
                    lv = p.child_by_field_name("left")
                    if op is not None and lv is not None \
                            and op.text.decode() in ("+=", "-=") \
                            and side_effect_free(lv):
                        sign = "++" if op.text == b"+=" else "--"
                        forge.candidate(
                            f"guard_incdec({fs.src(lv)}{sign}@L{line})",
                            TextEdit(start=p.start_byte, end=p.end_byte,
                                     replacement=f"{fs.src(lv)}{sign}"),
                        )
                        n_added += 1
    return n_added


_CHAR_CASTS = ("unsigned char", "signed char", "char")


def preset_rmw_split(forge, **opts) -> int:
    """``lv = (lv OP1 A) OP2 B;``  ->  ``lv OP1= A; lv OP2= B;``
    (two in-place memory RMWs -- Rule 143).

    Evidence: b3fc4071 dock_the_ship_in_good_port BYTE-EXACT
    (``occupant |= 0x1c; occupant &= 0x9f;``); 82c4be1b / 00715fa8
    road_ramifications BYTE-EXACT (``terrain &= 0xf9; terrain |= 2;``).
    A char-family cast wrapper on a byte-field store is absorbed (the
    witnessed PS form).
    """
    fs = _fs(forge)
    if fs is None:
        return 0
    n_added = 0
    for st in fs.nodes("expression_statement"):
        e = _expr_of_stmt(st)
        if e is None or e.type != "assignment_expression":
            continue
        op = e.child_by_field_name("operator")
        if op is None or op.text != b"=":
            continue
        lv = e.child_by_field_name("left")
        if lv is None or not side_effect_free(lv):
            continue
        rhs = unparen(e.child_by_field_name("right"))
        if rhs is not None and rhs.type == "cast_expression":
            tnode = rhs.child_by_field_name("type")
            has_field = any(n.type == "field_expression"
                            for n in walk_named(lv)) \
                or lv.type == "field_expression"
            if tnode is None or _norm(fs.src(tnode)) not in _CHAR_CASTS \
                    or not has_field:
                continue
            rhs = unparen(rhs.child_by_field_name("value"))
        if rhs is None or rhs.type != "binary_expression":
            continue
        op2 = rhs.child_by_field_name("operator")
        inner = unparen(rhs.child_by_field_name("left"))
        b_node = rhs.child_by_field_name("right")
        if op2 is None or inner is None or b_node is None \
                or op2.text.decode() not in _RMW_OPS \
                or inner.type != "binary_expression":
            continue
        op1 = inner.child_by_field_name("operator")
        base = unparen(inner.child_by_field_name("left"))
        a_node = inner.child_by_field_name("right")
        if op1 is None or base is None or a_node is None \
                or op1.text.decode() not in _RMW_OPS:
            continue
        if _norm(fs.src(base)) != _norm(fs.src(lv)):
            continue
        if not (side_effect_free(a_node) and side_effect_free(b_node)):
            continue
        if identifiers(lv) & (identifiers(a_node) | identifiers(b_node)):
            continue
        if not _starts_line(fs, st):
            continue
        indent = fs.indent_of(st)
        lv_t = fs.src(lv)
        repl = (f"{lv_t} {op1.text.decode()}= {fs.src(a_node)};\n"
                f"{indent}{lv_t} {op2.text.decode()}= {fs.src(b_node)};")
        forge.candidate(
            f"rmw_split(L{fs.line_no(st)})",
            TextEdit(start=st.start_byte, end=st.end_byte,
                     replacement=repl),
        )
        n_added += 1
    return n_added


def preset_cache_field(forge, max_sites: int = 10, **opts) -> int:
    """Repeated identical field/array READ (>= 2 occurrences, write-
    and call-free window) -> named local (the inverse of de_invent;
    PS sometimes NAMED the repeated read).

    Evidence: b3fc4071 dock_the_ship_in_good_port BYTE-EXACT (``occ``
    cached once, tested twice -- the frame root); f3fb8fc5
    build_city_item per-region gfx locals; 6a330ced take_census.
    Emitted per site with both ``int`` and ``unsigned char`` types.
    """
    fs = _fs(forge)
    if fs is None:
        return 0
    anchor = fs.top_decl_anchor()
    if anchor is None:
        return 0
    taken = fs.local_names()

    groups: dict[str, list] = {}
    for n in fs.nodes("field_expression", "subscript_expression"):
        p = n.parent
        if p is not None and p.type in (
                "field_expression", "subscript_expression",
                "pointer_expression"):
            continue                    # not maximal
        if p is not None and p.type == "assignment_expression" \
                and p.child_by_field_name("left") == n:
            continue
        if p is not None and p.type == "update_expression":
            continue
        if p is not None and p.type == "pointer_expression" \
                and p.child(0) is not None and p.child(0).type == "&":
            continue
        if not side_effect_free(n) or lvalue_base(n) is None:
            continue
        groups.setdefault(_norm(fs.src(n)), []).append(n)

    cands = [(k, v) for k, v in groups.items() if len(v) >= 2]
    cands.sort(key=lambda kv: -len(kv[1]))
    n_added = 0
    for expr_text, occs in cands[:max_sites]:
        occs.sort(key=lambda n: n.start_byte)
        first, last = occs[0], occs[-1]
        w_start, w_end = first.start_byte, last.end_byte
        expr_ids = identifiers(first)
        safe = True
        for n in walk_named(fs.body):
            if n.end_byte <= w_start or n.start_byte >= w_end:
                continue
            if n.type == "call_expression":
                safe = False
                break
            if n.type in ("assignment_expression", "update_expression"):
                lhs = (n.child_by_field_name("left")
                       if n.type == "assignment_expression"
                       else n.child_by_field_name("argument"))
                base = lvalue_base(lhs) if lhs is not None else None
                if base is None or base in expr_ids:
                    safe = False
                    break
        if not safe:
            continue
        stmt1 = _stmt_of(first)
        if stmt1 is None or not _starts_line(fs, stmt1):
            continue
        field = first.child_by_field_name("field") \
            if first.type == "field_expression" else None
        base_name = (field.text.decode() if field is not None
                     else lvalue_base(first) or "val")
        name = f"c_{base_name}"
        if name in taken:
            continue
        ls = fs.line_start(stmt1.start_byte)
        indent = fs.text[ls:stmt1.start_byte]
        line = fs.line_no(stmt1)
        for type_ in ("int", "unsigned char"):
            edits = [
                TextEdit(start=anchor, end=anchor,
                         replacement=f"    {type_} {name};\n",
                         note="cache decl"),
                TextEdit(start=ls, end=ls,
                         replacement=f"{indent}{name} = {expr_text};\n",
                         note="cache load"),
            ]
            edits += [TextEdit(start=n.start_byte, end=n.end_byte,
                               replacement=name,
                               note=f"use@L{fs.line_no(n)}")
                      for n in occs]
            forge.candidate(
                f"cache_field({name}:{type_}@L{line})", *edits)
            n_added += 1
    return n_added


def preset_bool_return(forge, **opts) -> int:
    """``return E ? 1 : 0;`` -> ``return E;`` when E is a comparison
    (provably identical).  Evidence: b3fc4071 (``return was_sea_flag
    != 0;``)."""
    fs = _fs(forge)
    if fs is None:
        return 0
    n_added = 0
    for r in fs.nodes("return_statement"):
        kids = [c for c in r.named_children if c.type != "comment"]
        if len(kids) != 1:
            continue
        t = unparen(kids[0])
        if t is None or t.type != "conditional_expression":
            continue
        cons = unparen(t.child_by_field_name("consequence"))
        alt = unparen(t.child_by_field_name("alternative"))
        if _int_of(cons) != 1 or _int_of(alt) != 0:
            continue
        cond = unparen(t.child_by_field_name("condition"))
        if cond is None or cond.type != "binary_expression":
            continue
        op = cond.child_by_field_name("operator")
        if op is None or op.text.decode() not in (
                "==", "!=", "<", ">", "<=", ">="):
            continue
        forge.candidate(
            f"bool_return(L{fs.line_no(r)})",
            TextEdit(start=kids[0].start_byte, end=kids[0].end_byte,
                     replacement=fs.src(cond)),
        )
        n_added += 1
    return n_added


_CAST_LIMITS = {
    "char": 0x7f, "signed char": 0x7f, "unsigned char": 0xff,
    "short": 0x7fff, "signed short": 0x7fff, "unsigned short": 0xffff,
}


def preset_cast_drop(forge, **opts) -> int:
    """Drop PROVABLY-no-op narrowing casts: ``(T)(E & M)`` where the
    mask M fits T's non-negative range (the stored value cannot
    change, whatever the lvalue type).  Evidence: f76bc477
    region_go_to_target BYTE-EXACT (``(char)((wd + 1) & 7)``)."""
    fs = _fs(forge)
    if fs is None:
        return 0
    n_added = 0
    for c in fs.nodes("cast_expression"):
        tnode = c.child_by_field_name("type")
        val = c.child_by_field_name("value")
        if tnode is None or val is None:
            continue
        limit = _CAST_LIMITS.get(_norm(fs.src(tnode)))
        if limit is None:
            continue
        v = unparen(val)
        if v is None or v.type != "binary_expression":
            continue
        op = v.child_by_field_name("operator")
        mask = _int_of(unparen(v.child_by_field_name("right")))
        if op is None or op.text != b"&" or mask is None \
                or not (0 <= mask <= limit):
            continue
        forge.candidate(
            f"cast_drop(L{fs.line_no(c)})",
            TextEdit(start=c.start_byte, end=c.end_byte,
                     replacement=fs.src(val)),
        )
        n_added += 1
    return n_added


_CAST_CMP_OPS = {"<", "<=", ">", ">=", "==", "!="}
_CAST_ARITH_OPS = {"+", "-", "*", "/", "%", "<<", ">>", "&", "|", "^"}
#: rvalue operand forms worth wrapping (never literals -- a cast on a
#: constant is folded by the front end).
_CAST_OPERAND_TYPES = (
    "identifier", "field_expression", "subscript_expression",
    "call_expression", "parenthesized_expression",
)


def preset_cast_sweep(forge, types=None, max_sites: int = 24,
                      **opts) -> int:
    """Explicit-cast sweep: wrap variables, computation results and
    comparison operands/results in every native integer cast
    (``types=[...]`` narrows; ``max_sites`` caps the site count).

    Sites, in priority order (rvalue-only, deduped by span):
      1. operands of comparisons  -- ``(T)x < y`` (comparison sign/width
         is decided by the promoted operand types),
      2. arithmetic/bitwise binop results -- ``(T)(a + b)``,
      3. comparison results -- ``(T)(a < b)``,
      4. identifier operands of arithmetic binops -- ``(T)x + y``,
      5. RHS of simple assignments / return expressions.

    Rationale: a wrong global / struct-field / return type is
    INVISIBLE to the local-decl type sweep -- an explicit cast at the
    USE site realises the promotion PS's (differently-typed) source
    got for free, so a hit here is a recovered type fact about a
    symbol declared elsewhere.  And like the type sweep, a
    byte-neutral cast is a conflict-list perturbation (register-class
    change on a compiler temp) -- a seat-steering lever.  Sites whose
    operand is already a cast are skipped (``cast_drop``'s turf)."""
    fs = _fs(forge)
    if fs is None:
        return 0
    cast_types = tuple(types) if types else NATIVE_INT_TYPES
    sites: list[tuple[int, int, object]] = []
    seen_span: set[tuple[int, int]] = set()

    def _add(prio: int, node) -> None:
        span = (node.start_byte, node.end_byte)
        if span in seen_span:
            return
        if node.type in ("number_literal", "char_literal"):
            return
        p = node.parent
        if p is not None and p.type == "cast_expression":
            return                      # already cast: cast_drop's turf
        if node.type == "cast_expression":
            return
        seen_span.add(span)
        sites.append((prio, len(sites), node))

    for n, op_t, l, r in _binops(fs):
        if op_t in _CAST_CMP_OPS:
            for side in (l, r):
                if side.type in _CAST_OPERAND_TYPES:
                    _add(0, side)
            _add(2, n)
        elif op_t in _CAST_ARITH_OPS:
            _add(1, n)
            for side in (l, r):
                if side.type == "identifier":
                    _add(3, side)
    for n in walk_named(fs.body):
        if n.type == "assignment_expression":
            op = n.child_by_field_name("operator")
            rhs = n.child_by_field_name("right")
            if op is not None and op.text == b"=" and rhs is not None \
                    and rhs.type in _CAST_OPERAND_TYPES:
                _add(4, rhs)
        elif n.type == "return_statement":
            kids = [c for c in n.named_children if c.type != "comment"]
            if len(kids) == 1 and kids[0].type in _CAST_OPERAND_TYPES:
                _add(4, kids[0])

    sites.sort(key=lambda t: (t[0], t[1]))
    n_added = 0
    seen_names: set[str] = set()
    for _prio, _ord, node in sites[:max_sites]:
        txt = _norm(fs.src(node))
        short = txt if len(txt) <= 18 else txt[:15] + "..."
        for t in cast_types:
            name = f"cast(L{fs.line_no(node)}:{short}={t})"
            if name in seen_names:
                name = (f"cast(L{fs.line_no(node)}"
                        f"@{node.start_byte}:{short}={t})")
            seen_names.add(name)
            forge.candidate(
                name,
                TextEdit(start=node.start_byte, end=node.end_byte,
                         replacement=f"({t}){_paren(fs, node)}"),
            )
            n_added += 1
    return n_added


def preset_line_split(forge, **opts) -> int:
    """Un-pack lines carrying >= 2 sibling statements (one candidate
    per packed line).  Bytes are invariant; the -d1 LINNUM stream --
    and with it the run-ledger ir layer + Hard Rule #8's line-compare
    -- moves.  Evidence: adf145d3 road_ramifications (split else-if
    chain assignments onto own lines)."""
    fs = _fs(forge)
    if fs is None:
        return 0
    n_added = 0
    for comp in fs.compounds():
        sts = fs.statements_of(comp)
        i = 0
        while i < len(sts):
            row = sts[i].start_point[0]
            group = [sts[i]]
            j = i + 1
            while j < len(sts) and sts[j].start_point[0] == row \
                    and sts[j].end_point[0] == row:
                group.append(sts[j])
                j += 1
            if len(group) >= 2 and sts[i].end_point[0] == row:
                ls = fs.line_start(group[0].start_byte)
                indent = fs.text[ls:group[0].start_byte]
                if not indent.strip():
                    edits = [
                        TextEdit(start=prev.end_byte, end=nxt.start_byte,
                                 replacement=f"\n{indent}")
                        for prev, nxt in zip(group, group[1:])
                    ]
                    forge.candidate(f"line_split(L{row + 1})", *edits)
                    n_added += 1
            i = j
    return n_added


def preset_line_join(forge, max_sites: int = 150, **opts) -> int:
    """Pack adjacent single-line simple statements onto one line (one
    candidate per adjacent pair; compose pairs for longer runs).  PS's
    statement-per-line packing is heavier than ours in many TUs
    (4a5e22ed place2_sprite line packing, ir 34->16; 1b731cfd
    find_enemy packs both guards on one line)."""
    fs = _fs(forge)
    if fs is None:
        return 0
    n_added = 0
    for comp in fs.compounds():
        sts = fs.statements_of(comp)
        for a, b in zip(sts, sts[1:]):
            if n_added >= max_sites:
                return n_added
            if a.type != "expression_statement" \
                    or b.type != "expression_statement":
                continue
            if not (_single_line(a) and _single_line(b)):
                continue
            if b.start_point[0] != a.end_point[0] + 1:
                continue
            if not (fs.owns_line(a) and fs.owns_line(b)):
                continue
            if fs.text[a.end_byte:b.start_byte].strip():
                continue                # comment between: keep apart
            forge.candidate(
                f"line_join(L{fs.line_no(a)}+L{fs.line_no(b)})",
                TextEdit(start=a.end_byte, end=b.start_byte,
                         replacement=" "),
            )
            n_added += 1
    return n_added


def _reindent_block(fs: FnSpan, stmt, new_indent: str) -> str:
    """The statement's full-line text, re-indented to ``new_indent``
    (relative inner indentation of multi-line statements preserved)."""
    s0, s1 = fs.full_line_span(stmt)
    block = fs.text[s0:s1]
    if not block.endswith("\n"):
        block += "\n"
    lines = block.splitlines(keepends=True)
    head = lines[0]
    old_indent = head[:len(head) - len(head.lstrip())]
    out = []
    for ln in lines:
        if ln.startswith(old_indent):
            out.append(new_indent + ln[len(old_indent):])
        elif ln.strip():
            out.append(new_indent + ln.lstrip())
        else:
            out.append(ln)
    return "".join(out)


def _contains_call(nodes) -> bool:
    return any(n.type == "call_expression"
               for stmt in nodes for n in walk_named(stmt))


def preset_tail_dup(forge, max_stmts: int = 3, **opts) -> int:
    """Rule 121 (2026-07-10 refinement): move the shared tail AFTER an
    ``if/else`` INTO the end of each arm.  ComTail re-merges the bytes;
    LdStAlloc walks the duplicated rover ops = +advance per copy.

    A statement-only dup is re-merged BEFORE the walk (screens
    INERT@BURN); a dup whose moved prefix INCLUDES a call survives to
    the walk -- the tag says which (``call`` vs ``stmt-only``).
    Byte-safety follows PS's witnessed layout (merged-dup jmp carries
    its own -d1 mark vs unmarked cross-arm goto/shared-tail jmp):
    byte-compile after screening.  Evidence: mid3_line_no_sides_base
    15cd1284 (win, killed the mov ebp,0xf CompressIns non-fusion);
    show_battlemap_base b5d891d9 (layout-unsafe counter-example).

    Safety: moving the first k trailing statements to the END of both
    arms is control-flow-neutral -- an early exit (continue/goto/
    return) inside an arm skipped the tail before and still does; a
    fall-through path ran it once and still does.  Tail statements
    must be expression statements owning their lines (no declarations,
    no labels -- so no jump target can move).
    """
    fs = _fs(forge)
    if fs is None:
        return 0
    n_added = 0
    for ifn in fs.nodes("if_statement"):
        cons = ifn.child_by_field_name("consequence")
        alt = _else_arm(ifn)
        if cons is None or alt is None:
            continue
        if cons.type != "compound_statement" \
                or alt.type != "compound_statement":
            continue
        holder = _stmt_of(ifn)               # ascends label wrappers
        if holder is None or holder.parent is None:
            continue
        sibs = fs.statements_of(holder.parent)
        try:
            i = sibs.index(holder)
        except ValueError:
            continue
        tail = []
        for s in sibs[i + 1:]:
            if s.type != "expression_statement" or not fs.owns_line(s):
                break
            tail.append(s)
            if len(tail) >= max_stmts:
                break
        if not tail:
            continue
        # insertion anchors: line-start of each arm's closing brace
        # (which must own its line so full-line inserts stay clean)
        anchors = []
        for arm in (cons, alt):
            brace = arm.children[-1] if arm.children else None
            if brace is None or brace.type != "}":
                anchors = None
                break
            ls = fs.line_start(brace.start_byte)
            if fs.text[ls:brace.start_byte].strip():
                anchors = None
                break
            stmts = fs.statements_of(arm)
            indent = (fs.indent_of(stmts[-1]) if stmts
                      else fs.indent_of(arm) + "    ")
            anchors.append((ls, indent))
        if anchors is None:
            continue
        for k in range(1, len(tail) + 1):
            moved = tail[:k]
            kind = "call" if _contains_call(moved) else "stmt-only"
            edits = [
                TextEdit(start=anchor, end=anchor,
                         replacement="".join(
                             _reindent_block(fs, m, indent) for m in moved),
                         note="dup tail into arm")
                for anchor, indent in anchors
            ]
            edits += [TextEdit(*fs.full_line_span(m), replacement="",
                               note="remove shared tail stmt")
                      for m in moved]
            forge.candidate(
                f"tail_dup(L{fs.line_no(ifn)},k{k},{kind})", *edits)
            n_added += 1
    return n_added


def preset_tail_hoist(forge, max_stmts: int = 3, **opts) -> int:
    """Reverse of :func:`preset_tail_dup`: both arms of an ``if/else``
    END with the same statement sequence -> remove it from each arm and
    write it ONCE after the if/else (the shared-tail form; -advance).
    Same bytes via ComTail either way on the merged side; the rover
    walk loses the duplicated ops.  Arms ending in continue/goto/return
    yield an empty common suffix (only expression statements scan), so
    the transform stays control-flow-neutral by construction.
    """
    fs = _fs(forge)
    if fs is None:
        return 0
    n_added = 0
    for ifn in fs.nodes("if_statement"):
        cons = ifn.child_by_field_name("consequence")
        alt = _else_arm(ifn)
        if cons is None or alt is None:
            continue
        if cons.type != "compound_statement" \
                or alt.type != "compound_statement":
            continue
        a_stmts = fs.statements_of(cons)
        b_stmts = fs.statements_of(alt)
        suffix = 0
        while (suffix < min(len(a_stmts), len(b_stmts), max_stmts)):
            a = a_stmts[-1 - suffix]
            b = b_stmts[-1 - suffix]
            if a.type != "expression_statement" \
                    or b.type != "expression_statement" \
                    or not fs.owns_line(a) or not fs.owns_line(b) \
                    or _norm(fs.src(a)) != _norm(fs.src(b)):
                break
            suffix += 1
        if not suffix:
            continue
        holder = _stmt_of(ifn)
        if holder is None:
            continue
        insert_at = fs.line_end(holder.end_byte - 1)
        indent = fs.indent_of(holder)
        for k in range(1, suffix + 1):
            moved_a = a_stmts[len(a_stmts) - k:]
            moved_b = b_stmts[len(b_stmts) - k:]
            kind = "call" if _contains_call(moved_a) else "stmt-only"
            edits = [TextEdit(*fs.full_line_span(m), replacement="",
                              note="remove arm-tail copy")
                     for m in (*moved_a, *moved_b)]
            edits.append(TextEdit(
                start=insert_at, end=insert_at,
                replacement="".join(
                    _reindent_block(fs, m, indent) for m in moved_a),
                note="shared tail after if/else"))
            forge.candidate(
                f"tail_hoist(L{fs.line_no(ifn)},k{k},{kind})", *edits)
            n_added += 1
    return n_added


_ALL_BATTERY = (
    "stmt_reorder_deep", "decl_swap_all", "decl_perm",
    "commute_all", "relorder_all",
    "shift1", "bytemask",
    "compound_assign_expand", "compound_assign_contract", "incdec_toggle",
    "decl_init_split", "decl_hoist", "de_invent_all", "cache_literal",
    "cache_field", "loop_form", "while_rotate", "ternary_split",
    "if_fission", "if_invert", "guard_const", "rmw_split",
    "bool_return", "cast_drop", "cast_sweep",
    "line_split", "line_join",
    "type_sweep", "param_type_sweep",
    "tail_dup", "tail_hoist",
)


def preset_all(forge, **opts) -> int:
    """THE DEFAULT BATTERY: every site-preset, poured together.
    Forgetting a lever costs a session (2026-06-30 postmortem); the
    dedup + island-ordering + caps absorb the pool size."""
    n = 0
    for name in _ALL_BATTERY:
        n += PRESETS[name](forge, **opts)
    return n


#: The seat-layer lever family (fix_next=seat).  Every lever here is a
#: proven register-SEAT mover; the shape levers (if/loop/ternary/rmw/
#: line_split ...) are OMITTED because on an ir=0/islands=0 function they
#: only waste compiles.  Split into the pure BIRTH-REORDER family (Rule
#: 28a/115 -- the offline seat oracle predicts these exactly) and the
#: range-changing BRIDGE family (register-class flips + live-set changes,
#: which the offline model can't predict and must compile).
_SEAT_REORDER = (
    "decl_swap_all", "decl_perm", "stmt_reorder_deep",
    "commute_all", "relorder_all",
)
_SEAT_BRIDGE = (
    "type_sweep", "param_type_sweep", "cast_sweep",
    "de_invent_all", "cache_field",
)


def preset_seat(forge, restrict=None, prune_reorder: bool = False,
                **opts) -> int:
    """The fix_next=seat profile, oracle-tunable.

    ``restrict=[vars...]`` (from ``c2.forge.seat_oracle``) focuses the
    decl/type levers on the competing values the oracle named.
    ``prune_reorder=True`` DROPS the birth-reorder family entirely --
    used when the oracle certifies (trusted + exhausted) that no pure
    reorder reaches PS, so the residue is a bridge (register-class flip)
    or sub-source; grinding decl/stmt order then only wastes compiles.

    The `restrict` filter is applied to every lever that supports it
    (decl_swap_all, decl_perm, type_sweep, param_type_sweep); the
    remaining levers emit all their sites (they are O(n), not O(n^2)).
    """
    n = 0
    if not prune_reorder:
        # FOCUSED reorder profile: the birth-reorder levers, EVERY one
        # restricted to the oracle's named vars, so the singles pool is
        # tens (not hundreds) and the pairs/triples escalation stays far
        # under the cap.  No broad cast/param sweeps here -- those are the
        # bridge strategy.
        # decl_swap_all is UNRESTRICTED: the survey (convert_lbm_file
        # closed via swap_decls(i,b), and `i` is not a diverging value)
        # proves the decl-order MOVER need not be the competing value.
        # It is only O(n^2) so the full pair set stays small; the more
        # expensive levers (decl_perm, stmt/commute, type) stay focused.
        n += preset_decl_swap_all(forge)
        n += preset_decl_perm(forge, restrict=restrict)
        n += preset_stmt_reorder_deep(forge, restrict=restrict)
        n += preset_commute_all(forge, restrict=restrict)
        n += preset_type_sweep(forge, restrict=restrict)
        # The seat layer is lever-AMBIGUOUS (survey: find_enemy/start_move/
        # city_test_for_road are shape-identical fix_next=seat islands=0 yet
        # closed by de-invent / commute / width respectively).  So the
        # profile must offer EVERY observed seat lever and let byte-verify
        # pick -- de_invent_all (remove an invented local) was the missing
        # one; there is no reliable PS-native "invented" signal to target it,
        # so we always offer it (bounded by the eligible-local count).
        n += preset_de_invent_all(forge)
        return n
    # BRIDGE profile (floor/savings): no pure reorder reaches PS, so try
    # register-class flips on the named competing values only.  Restricted
    # to the oracle's vars -> a handful of candidates, not a 400-wide sweep.
    n += preset_type_sweep(forge, restrict=restrict)
    n += preset_param_type_sweep(forge, restrict=restrict)
    n += preset_de_invent_all(forge)
    n += preset_cache_field(forge)
    return n


def preset_localset(forge, mode: str = "de_invent", restrict=None,
                    **opts) -> int:
    """The local-SET repair profile (driven by the win-census verdict).

    The seat residue's ROOT is often a wrong named-local set (the
    allocator's conflict-queue input), not a reorder/retype of the
    current set.  ``mode`` comes from ``c2.forge.seat_oracle.census_verdict``:

      de_invent (\u0394<0) -- our source invented local(s); inline every
                        eligible single-assign local + the beam/verify
                        picks the removal that closes.
      add_local (\u0394>0) -- the original had more local(s); introduce a
                        named local for a repeated field/array read or
                        literal (cache_field / cache_literal).  NOTE:
                        only the repeated-read/literal forms are
                        auto-synthesizable; an arbitrary new intermediate
                        still needs a hand edit named from the slot's
                        first-use asm.
      width     (\u0394=0) -- count matches; a local has the wrong type.
    """
    n = 0
    if mode == "de_invent":
        n += preset_de_invent_all(forge)
        n += preset_cache_field(forge)             # remove one / cache another
        n += preset_type_sweep(forge, restrict=restrict)
    elif mode == "add_local":
        n += preset_cache_field(forge)
        n += preset_cache_literal(forge)
        n += preset_de_invent_all(forge)           # port drift: also invented?
    else:                                          # width
        n += preset_type_sweep(forge, restrict=restrict)
        n += preset_param_type_sweep(forge, restrict=restrict)
        n += preset_cast_sweep(forge)
    return n


PRESETS = {
    "tie_group":                preset_tie_group,
    "decl_swap_all":            preset_decl_swap_all,
    "decl_perm":                preset_decl_perm,
    "decl_init_split":          preset_decl_init_split,
    "decl_hoist":               preset_decl_hoist,
    "stmt_reorder_deep":        preset_stmt_reorder_deep,
    "stmt_swap_adjacent":       preset_stmt_swap_adjacent,   # alias (call-free)
    "firstassign":              preset_stmt_reorder_deep,    # alias (compat)
    "commute_all":              preset_commute_all,
    "relorder_all":             preset_relorder_all,
    "type_sweep":               preset_type_sweep,
    "param_type_sweep":         preset_param_type_sweep,
    "shift1":                   preset_shift1,
    "bytemask":                 preset_bytemask,
    "compound_assign_expand":   preset_compound_assign_expand,
    "compound_assign_contract": preset_compound_assign_contract,
    "incdec_toggle":            preset_incdec_toggle,
    "de_invent_all":            preset_de_invent_all,
    "cache_literal":            preset_cache_literal,
    "cache_field":              preset_cache_field,
    "loop_form":                preset_loop_form,
    "while_rotate":             preset_while_rotate,
    "ternary_split":            preset_ternary_split,
    "if_fission":               preset_if_fission,
    "if_invert":                preset_if_invert,
    "guard_const":              preset_guard_const,
    "rmw_split":                preset_rmw_split,
    "bool_return":              preset_bool_return,
    "cast_drop":                preset_cast_drop,
    "cast_sweep":               preset_cast_sweep,
    "line_split":               preset_line_split,
    "line_join":                preset_line_join,
    "tail_dup":                 preset_tail_dup,
    "tail_hoist":               preset_tail_hoist,
    "seat":                     preset_seat,
    "localset":                 preset_localset,
    "all":                      preset_all,
}

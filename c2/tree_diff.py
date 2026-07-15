"""Compare a REVERSED IR tree (from PS asm via :mod:`c2.binir`) against the
FORWARD IR tree (from our build`s instrumented compile trace, via
:mod:`c2.ir`).  Structural differences reveal what intermediate constructs
PS`s source had that ours doesn`t.

End-to-end pipeline (the long-term vision):

    PS.EXE asm  --binir.recover-->  RecoveredOp[]  --to_tree-->  TreeShape  ┐
                                                                              ├-> diff
    decomp.c    --wcc386 trace-->  IRForest        --to_tree-->  TreeShape  ┘

Where :class:`TreeShape` is the SHARED canonical tree representation that
both sides produce.  The diff highlights:

  * Nodes present in ONE side only -- e.g. an `ASSIGN(temp, ...)` chain on
    the FORWARD side (with the temp `s`) that has no counterpart on the
    REVERSED side (PS used direct-memory RMW with no temp).  This is the
    "intermediate" the user wants the diff to surface.
  * Mismatched op shapes -- e.g. forward emits a `BINARY(O_AND)` then
    `ASSIGN`, reversed emits a `PRE_GETS(O_AND)`.  Tells you the OPTAB
    chose a different row.
  * Same shape, different attributes (e.g. operand register class) -- a
    deeper level of detail when surface shapes match.

This module currently provides:

  * :class:`TreeShape` -- the unified node type.
  * :func:`shape_from_ir_forest` -- forward path adapter for c2.ir.Node.
  * :func:`shape_from_binir_ops` -- reverse path adapter for
    c2.binir.RecoveredOp (PARTIAL -- only the patterns binir recognises
    today get tree nodes; the rest become "raw_asm" leaves).
  * :func:`tree_diff` -- structural comparison + difference report.

The reverse-side coverage will grow with binir`s pattern catalog.  Adding
a new RecoveredOp kind:
    1. Add the asm matcher in :mod:`c2.binir`.
    2. Add a converter case in :func:`shape_from_binir_ops` mapping the
       new kind to a TreeShape node (or sub-tree).
    3. Add a forward-side counterpart in :func:`shape_from_ir_forest` IF
       the same shape comes out of the trace too.
    4. Write a test asserting forward.tree == reverse.tree for a function
       where both should be identical.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Optional

from c2.ir import (
    CG_OP_NAMES, IRForest, Name, Node,
    TN_LEAF, TN_UNARY, TN_BINARY, TN_COMPARE, TN_ASSIGN, TN_LV_ASSIGN,
    TN_PARM, TN_CALL, TN_COMMA, TN_BIT_LVALUE, TN_CONS, TN_SIDE_EFFECT,
    NAME_CLASS_NAME, TN_CLASS_NAME,
)


# ── Canonical tree representation ───────────────────────────────────────

@dataclass
class TreeShape:
    """A node in the unified IR tree (either forward or reverse derived).

    Fields are kept small + comparable so two TreeShape trees can be
    structurally diffed.  ``op`` and ``children`` are the load-bearing
    fields; ``detail`` carries side-band metadata (offsets, names) that the
    diff inspects but doesn`t require to match.
    """
    op: str                                # e.g. "ASSIGN", "BINARY:O_AND", "LEAF:N_MEMORY"
    children: list["TreeShape"] = field(default_factory=list)
    detail: dict = field(default_factory=dict)

    # Provenance: which side produced this node.
    origin: str = "?"                      # "forward" | "reverse"

    def __repr__(self) -> str:
        if not self.children:
            return f"<{self.op}>"
        return f"<{self.op}({len(self.children)})>"

    def pretty(self, *, indent: int = 0) -> str:
        """Multi-line indented dump, useful for debugging."""
        pad = "  " * indent
        head = f"{pad}{self.op}"
        if self.detail:
            head += "  " + " ".join(f"{k}={v}" for k, v in self.detail.items()
                                    if k not in ("offset",))
        lines = [head]
        for c in self.children:
            lines.append(c.pretty(indent=indent + 1))
        return "\n".join(lines)


# ── Forward path: from c2.ir.Node ────────────────────────────────────────

# cg_op enum lives in c2.ir.CG_OP_NAMES (empirically recovered from a 10.0a
# trace; see c2/ir.py module docstring).  Mirror it here as ``_CG_OP_NAMES``
# for backward-compat with existing imports.
_CG_OP_NAMES: dict[int, str] = dict(CG_OP_NAMES)


def _cg_op(op: int) -> str:
    return _CG_OP_NAMES.get(op, f"O_op{op}")


def _ir_op_name(node: Node) -> str:
    """Canonical ``op`` field for a c2.ir.Node."""
    cls_name = TN_CLASS_NAME.get(node.cls, f"cls{node.cls:#x}")
    if node.kind == "tl":
        # Leaf: tag with the underlying name class when available.
        if node.name is not None:
            return f"LEAF:{NAME_CLASS_NAME.get(node.name.cls, 'NAME')}"
        return f"LEAF:{cls_name}"
    if node.kind == "tb":
        return "BIT_LVALUE"
    # tn
    if node.cls in (TN_BINARY, TN_COMPARE):
        return f"{cls_name}:{_cg_op(node.op)}"
    if node.cls == TN_UNARY:
        return f"UNARY:{_cg_op(node.op)}"
    return cls_name


def shape_from_node(node: Optional[Node], *, _seen=None) -> Optional[TreeShape]:
    """Convert a c2.ir.Node into a TreeShape.  Returns None for None.
    Guards against cycles (shouldn`t happen with bottom-up IR but be safe).
    """
    if node is None:
        return None
    if _seen is None:
        _seen = set()
    if id(node) in _seen:
        return TreeShape(op="<cycle>", origin="forward")
    _seen.add(id(node))
    children: list[TreeShape] = []
    left_shape = shape_from_node(node.left, _seen=_seen) if hasattr(node, "left") else None
    right_shape = shape_from_node(node.right, _seen=_seen) if hasattr(node, "right") else None
    if left_shape is not None:
        children.append(left_shape)
    if right_shape is not None:
        children.append(right_shape)
    detail: dict = {}
    if node.line is not None:
        detail["line"] = node.line
    if node.kind == "tl" and node.name is not None:
        detail["name_seq"] = node.name.seq
        detail["name_cls"] = NAME_CLASS_NAME.get(node.name.cls, f"cls{node.name.cls}")
    return TreeShape(op=_ir_op_name(node), children=children,
                     detail=detail, origin="forward")


def shape_from_ir_forest(forest: IRForest) -> list[TreeShape]:
    """Convert every statement root in the forest to a TreeShape.  The
    result is a list of per-statement trees in source-line order."""
    out: list[TreeShape] = []
    for root in forest.roots:
        s = shape_from_node(root)
        if s is not None:
            out.append(s)
    return out


# ── Reverse path: from c2.binir.RecoveredOp ──────────────────────────────

def shape_from_binir_ops(ops: list, *, line_lookup: Optional[dict] = None
                         ) -> list[TreeShape]:
    """Convert a list of :class:`c2.binir.RecoveredOp` into TreeShapes.

    Coverage is PARTIAL -- only the patterns binir currently recognises
    map to tree nodes.  Unrecognised offsets become ``raw_asm`` leaves so
    consumers see the gap rather than silently lose data.

    ``line_lookup`` maps asm offset -> source line (from debug info or
    a decomp-verify cache); when given, every emitted TreeShape gets a
    ``line`` detail.  Optional.
    """
    out: list[TreeShape] = []
    for op in ops:
        if op.kind in ("const_store_run_reg", "const_store_run_imm"):
            # expand to n ASSIGN(MEM, CONST) shapes so the run compares
            # 1:1 with individual mov_mem_imm / forward-tree assigns; the
            # FORM (reg vs imm) is a summarize()-level signal (Rule 128),
            # never an IR-tree difference.
            val = op.detail.get("value")
            for _ in range(op.detail.get("n", 1)):
                sh = TreeShape(
                    op="ASSIGN",
                    children=[
                        TreeShape(op="LEAF:MEMORY", origin="reverse"),
                        TreeShape(op="LEAF:CONSTANT",
                                  detail={"value": val}, origin="reverse"),
                    ],
                    detail={"kind": op.kind, "offset": op.offset},
                    origin="reverse",
                )
                if line_lookup and op.offset in line_lookup:
                    sh.detail["line"] = line_lookup[op.offset]
                out.append(sh)
            continue
        if op.kind == "mem_sum_chain":
            # one ASSIGN(MEM, left-assoc O_PLUS chain over n MEMORY leaves)
            # -- matches the forward tree of `g = a + b + ... + z;` exactly,
            # regardless of which terms CompressIns left split (Rule 130).
            n = op.detail.get("n", 2)
            expr = TreeShape(op="LEAF:MEMORY", origin="reverse")
            for _ in range(n - 1):
                expr = TreeShape(
                    op="BINARY:O_PLUS",
                    children=[expr,
                              TreeShape(op="LEAF:MEMORY", origin="reverse")],
                    origin="reverse",
                )
            sh = TreeShape(
                op="ASSIGN",
                children=[TreeShape(op="LEAF:MEMORY", origin="reverse"), expr],
                detail={"kind": op.kind, "offset": op.offset},
                origin="reverse",
            )
            if line_lookup and op.offset in line_lookup:
                sh.detail["line"] = line_lookup[op.offset]
            out.append(sh)
            continue
        if op.kind == "ptr_base_materialize":
            # pure address-mode artifact (the &arr[i] LA): no forest
            # counterpart -- the lever lives in the kind census/notes.
            continue
        shape = _binir_op_to_shape(op)
        if shape is None:
            continue
        if line_lookup and op.offset in line_lookup:
            shape.detail["line"] = line_lookup[op.offset]
        out.append(shape)
    return out


def _binir_op_to_shape(op) -> Optional[TreeShape]:
    """Map ONE RecoveredOp to a TreeShape (or None if the kind doesn`t
    correspond to a tree node)."""
    kind = op.kind
    detail = {"offset": op.offset, **op.detail}
    if kind == "r5c_idiv_pair":
        # Two divides sharing a divisor temp.  Represent as a synthetic
        # OP_DIV + OP_MOD pair with the divisor as a TEMP leaf.
        div_reg = op.detail.get("div_reg", "?")
        divisor = op.detail.get("divisor_imm")
        divisor_leaf = TreeShape(
            op="LEAF:CONSTANT" if divisor is not None else f"LEAF:REGISTER",
            detail={"value": divisor, "reg": div_reg},
            origin="reverse",
        )
        return TreeShape(
            op="SIDE_EFFECT",   # the pair is a side-effect group
            children=[
                TreeShape(op="BINARY:O_MOD",
                          children=[TreeShape(op="LEAF:?", origin="reverse"),
                                    divisor_leaf],
                          origin="reverse"),
                TreeShape(op="BINARY:O_DIV",
                          children=[TreeShape(op="LEAF:?", origin="reverse"),
                                    divisor_leaf],
                          origin="reverse"),
            ],
            detail=detail, origin="reverse",
        )
    if kind == "g_pow2div":
        shift = op.detail.get("shift", 0)
        return TreeShape(
            op="BINARY:O_DIV",
            children=[
                TreeShape(op="LEAF:?", origin="reverse"),
                TreeShape(op="LEAF:CONSTANT",
                          detail={"value": 1 << shift}, origin="reverse"),
            ],
            detail=detail, origin="reverse",
        )
    if kind == "g_div2":
        return TreeShape(
            op="BINARY:O_DIV",
            children=[
                TreeShape(op="LEAF:?", origin="reverse"),
                TreeShape(op="LEAF:CONSTANT",
                          detail={"value": 2}, origin="reverse"),
            ],
            detail=detail, origin="reverse",
        )
    if kind == "zext_byte_load":
        return TreeShape(
            op="UNARY:O_CONVERT",
            children=[
                TreeShape(op="LEAF:MEMORY", origin="reverse"),
            ],
            detail=detail, origin="reverse",
        )
    if kind in {"zext_clr_reg", "zext_and_inplace", "zext_copy_and"}:
        # Both rCLRHI_R lowerings of the SAME OP_CONVERT (xor+mov-low from
        # a register vs and-imm in place).  One shape => an AL-squat
        # seating divergence never shows up as an IR-tree difference; the
        # summarize() kind split is the seating signal instead.
        return TreeShape(
            op="UNARY:O_CONVERT",
            children=[TreeShape(op="LEAF:?", origin="reverse")],
            detail=detail, origin="reverse",
        )
    if kind in {"mul_pow2", "mul_const_minus_one",
                "mul_const_plus_one", "mul_lea_scaled_self",
                "mul_lea_scaled"}:
        factor = op.detail.get("factor")
        return TreeShape(
            op="BINARY:O_TIMES",
            children=[
                TreeShape(op="LEAF:?", origin="reverse"),
                TreeShape(op="LEAF:CONSTANT",
                          detail={"value": factor}, origin="reverse"),
            ],
            detail=detail, origin="reverse",
        )
    if kind in {"cmp_jcc", "zero_test_jcc"}:
        # Comparison + branch -- represent as a COMPARE TN.  Use a CLEAN
        # canonical op name (NOT the operand-laden string from binir.op).
        # The condition comes from the jcc mnemonic via _condcode_to_op,
        # already mapped to "O_CMP_*" so it round-trips against the
        # forward-side ``_cg_op(node.op)`` naming.
        from c2.binir import _condcode_to_op as _cc2op  # local: avoid cycle
        jcc = op.detail.get("jcc", "?")
        cond = _cc2op(jcc)
        rhs_val = op.detail.get("imm", 0) if kind == "cmp_jcc" else 0
        return TreeShape(
            op=f"COMPARE:{cond}",
            children=[
                TreeShape(op="LEAF:?", origin="reverse"),
                TreeShape(op="LEAF:CONSTANT",
                          detail={"value": rhs_val}, origin="reverse"),
            ],
            detail=detail, origin="reverse",
        )
    if kind in {"zext_load_byte", "zext_load_word",
                "signext_load_byte", "signext_load_word"}:
        return TreeShape(
            op="UNARY:O_CONVERT",
            children=[TreeShape(op="LEAF:MEMORY", origin="reverse")],
            detail=detail, origin="reverse",
        )
    if kind == "pre_gets_mem_const":
        # The smoking gun for Rule 17b: direct-memory-RMW with constant.
        # Shape: PRE_GETS:O_<binop>(LEAF:MEMORY, LEAF:CONSTANT)
        cg = op.detail.get("cg_op", "O_?")
        imm = op.detail.get("imm")
        return TreeShape(
            op=f"PRE_GETS:{cg}",
            children=[
                TreeShape(op="LEAF:MEMORY", origin="reverse"),
                TreeShape(op="LEAF:CONSTANT",
                          detail={"value": imm}, origin="reverse"),
            ],
            detail=detail, origin="reverse",
        )
    if kind == "mov_mem_imm":
        # ASSIGN(LEAF:MEMORY, LEAF:CONSTANT) -- the bulk "X = K" store.
        imm = op.detail.get("imm")
        return TreeShape(
            op="ASSIGN",
            children=[
                TreeShape(op="LEAF:MEMORY", origin="reverse"),
                TreeShape(op="LEAF:CONSTANT",
                          detail={"value": imm}, origin="reverse"),
            ],
            detail=detail, origin="reverse",
        )
    if kind == "call_with_args":
        # CALL(target) with one PARM child per pushed argument.  The args
        # themselves are kept as opaque LEAF:? leaves -- we know they
        # exist but not their tree shape from binir alone.
        argc = op.detail.get("argc", 0)
        return TreeShape(
            op="CALL",
            children=[
                TreeShape(op="PARM",
                          children=[TreeShape(op="LEAF:?", origin="reverse")],
                          origin="reverse")
                for _ in range(argc)
            ],
            detail=detail, origin="reverse",
        )
    if kind == "branch_jmp":
        # Unconditional GOTO -- no children in the tree-shape sense
        # (the target is metadata, not a sub-expression).
        return TreeShape(op="GOTO", detail=detail, origin="reverse")
    if kind == "branch_flag_jcc":
        # Conditional branch where the flag-set is implicit (no preceding
        # cmp).  Map to a synthetic COND_BRANCH; the forward side will
        # show whichever COMPARE the front-end built.
        return TreeShape(op="COND_BRANCH", detail=detail, origin="reverse")
    return None


# ── Tree diff ────────────────────────────────────────────────────────────

@dataclass
class Difference:
    """One structural difference between two trees."""
    kind: str        # "op_mismatch" | "children_mismatch" | "only_in_a" | "only_in_b"
    path: str        # dotted/indexed path to the differing node
    a: Optional[str] = None
    b: Optional[str] = None
    note: str = ""


def tree_diff(a: Optional[TreeShape], b: Optional[TreeShape],
              path: str = "") -> list[Difference]:
    """Structural diff of two TreeShape trees.

    Comparisons are by ``op`` and recursive children.  ``detail`` is
    INFORMATIONAL only -- it doesn`t cause a mismatch by itself (we treat
    detail as side-band metadata).  Returns a list of differences; an empty
    list means the two trees are structurally identical.
    """
    if a is None and b is None:
        return []
    if a is None:
        return [Difference(kind="only_in_b", path=path, b=b.op,
                           note=f"forward has no counterpart")]
    if b is None:
        return [Difference(kind="only_in_a", path=path, a=a.op,
                           note=f"reverse has no counterpart")]
    diffs: list[Difference] = []
    if a.op != b.op:
        diffs.append(Difference(
            kind="op_mismatch", path=path, a=a.op, b=b.op,
            note="root op differs",
        ))
    # Compare children sequentially.  When lengths differ, that`s itself a
    # diff and we still descend into the shorter prefix.
    n = max(len(a.children), len(b.children))
    if len(a.children) != len(b.children):
        diffs.append(Difference(
            kind="children_mismatch", path=path,
            a=str(len(a.children)), b=str(len(b.children)),
            note=f"child count differs ({len(a.children)} vs {len(b.children)})",
        ))
    for i in range(n):
        ca = a.children[i] if i < len(a.children) else None
        cb = b.children[i] if i < len(b.children) else None
        diffs.extend(tree_diff(ca, cb, path=f"{path}[{i}]" if path else f"[{i}]"))
    return diffs


def trees_match(a: TreeShape, b: TreeShape) -> bool:
    """True iff ``tree_diff(a, b)`` returns no differences."""
    return not tree_diff(a, b)


# ── Rule 119 byte-pump workhorse signature on the forward TreeShape ─────


@dataclass
class BytePumpChain:
    """A workhorse-accumulator chain detected in the forward IR.

    Attributes
    ----------
    name_seq:
        The ``name.seq`` of the workhorse LEAF (a synthetic id from the
        IR trace -- matches ``LEAF`` nodes' ``detail['name_seq']``).
    self_ref_count:
        Number of ASSIGN statements where the target leaf also appears
        in the rvalue subtree (i.e., ``r = r <op> X`` form, compound
        assignment).
    has_lshift:
        Whether any self-referencing ASSIGN includes a BINARY:O_LSHIFT
        on the target leaf.  LSHIFT in OW v1 is NOT in
        ``CountRegMoves``' commutative table -- it consumes a
        walk-slot for no CRM bonus, so its presence increases the
        wasted-savings signal.
    has_byte_zext_input:
        Whether at least one ASSIGN's rvalue contains a
        ``UNARY:O_CONVERT`` (the IR shape for ``(unsigned char)expr``
        byte-zext / sign-extend coming out of the front-end).  When
        true, the chain is a classic byte-pump composite.
    stmt_indices:
        Indexes into ``shapes`` (the forward TreeShape list) where the
        chain occurs.  Useful for rendering / pointing at source lines.
    """

    name_seq: int
    self_ref_count: int
    has_lshift: bool
    has_byte_zext_input: bool
    stmt_indices: list[int] = field(default_factory=list)


def _collect_leaf_seqs(shape: TreeShape) -> set[int]:
    """Walk a TreeShape subtree and collect every ``name_seq`` of LEAF
    nodes.  Used to detect "does the rvalue reference the target leaf?"
    """
    seqs: set[int] = set()
    if shape.op.startswith("LEAF:") and "name_seq" in shape.detail:
        seqs.add(shape.detail["name_seq"])
    for c in shape.children:
        seqs.update(_collect_leaf_seqs(c))
    return seqs


def _has_op(shape: TreeShape, op_prefix: str) -> bool:
    """True if any node in the subtree has ``shape.op`` starting with
    ``op_prefix``."""
    if shape.op.startswith(op_prefix):
        return True
    return any(_has_op(c, op_prefix) for c in shape.children)


def detect_byte_pump_chains(shapes: list[TreeShape],
                             *, min_self_ref: int = 2) -> list[BytePumpChain]:
    """Find workhorse-accumulator chains in a FORWARD TreeShape list
    (one TreeShape per statement-root, in source order; the output of
    :func:`shape_from_ir_forest`).

    A "byte-pump workhorse" is a LEAF that appears as the ASSIGN target
    in ``min_self_ref+`` consecutive (or near-consecutive) statements
    WHERE THE RVALUE SUBTREE ALSO REFERENCES THAT SAME LEAF.  This is
    the IR signature of compound assignments ``r = r <op> X`` (which
    the front-end may rewrite from source ``r <op>= X``).

    The returned list is ordered by decreasing ``self_ref_count``
    (strongest signal first).  Pure self-assigns / no-op patterns are
    excluded because they have ``self_ref_count == 0``.

    See Rule 119 (``docs/watcom-codegen-patterns.md``) for the lever.
    The IR-level detector backstops the AST detector in
    ``c2.commands.byte_pump_hints`` for cases where source-shape doesn't
    match the byte-pump idiom but the IR does (front-end rewrites, etc.).
    """
    per_seq: dict[int, BytePumpChain] = {}
    for i, shape in enumerate(shapes):
        if shape.op != "ASSIGN" or len(shape.children) < 2:
            continue
        target = shape.children[0]
        rvalue = shape.children[1]
        if not target.op.startswith("LEAF:"):
            continue
        tseq = target.detail.get("name_seq")
        if tseq is None:
            continue
        rvalue_seqs = _collect_leaf_seqs(rvalue)
        if tseq not in rvalue_seqs:
            # Pure assign ``r = expr`` (no compound) -- not a chain link.
            continue
        chain = per_seq.get(tseq)
        if chain is None:
            chain = BytePumpChain(name_seq=tseq, self_ref_count=0,
                                  has_lshift=False, has_byte_zext_input=False,
                                  stmt_indices=[])
            per_seq[tseq] = chain
        chain.self_ref_count += 1
        chain.stmt_indices.append(i)
        if _has_op(rvalue, "BINARY:O_LSHIFT"):
            chain.has_lshift = True
        if _has_op(rvalue, "UNARY:O_CONVERT"):
            chain.has_byte_zext_input = True
    result = [c for c in per_seq.values() if c.self_ref_count >= min_self_ref]
    result.sort(key=lambda c: -c.self_ref_count)
    return result


# ── Convenience: diff a function`s forward vs reverse trees ──────────────

def diff_function(forest: IRForest, recovered_ops: list,
                  *, line_lookup: Optional[dict] = None) -> dict:
    """Diff the forward IR forest`s statement roots against the trees
    recoverable from binir`s patterns.

    Returns ``{"forward": [...], "reverse": [...], "diffs": [...]}`` for
    a side-by-side rendering.

    NOTE: reverse-side coverage is currently PARTIAL -- many functions
    will show large `only_in_a` diffs simply because binir doesn`t (yet)
    recognise the asm pattern.  As the binir catalog grows the gaps shrink.
    """
    forward = shape_from_ir_forest(forest)
    reverse = shape_from_binir_ops(recovered_ops, line_lookup=line_lookup)
    # The simplest "alignment" pairs forward[i] with reverse[i] in order.
    # A smarter alignment (e.g. by line number) is a future iteration.
    diffs: list[Difference] = []
    for i in range(max(len(forward), len(reverse))):
        a = forward[i] if i < len(forward) else None
        b = reverse[i] if i < len(reverse) else None
        diffs.extend(tree_diff(a, b, path=f"stmt[{i}]"))
    return {"forward": forward, "reverse": reverse, "diffs": diffs}

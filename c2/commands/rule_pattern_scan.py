"""Extensible scanner framework for source patterns + IR-forest verification.

Two complementary jobs per rule:

  1. **Source-level AST detection** -- walk every function`s C AST and report
     where the rule`s SOURCE pattern appears.  For a "remove this construct"
     rule (like Rule 17b), the test asserts 0 candidates corpus-wide.

  2. **IR-forest verification** -- given an instrumented compile trace, walk
     the per-routine IR forest (c2.ir) and assert the rule`s PREDICTED tree
     shape (or its absence) holds.  Connects the AST candidate to the
     compiler`s actual tree decisions -- so when a new "tree-reversal"
     construct is reverse-engineered, the test can confirm the compiler
     really does build the tree we think it does.

Adding a new rule pattern
-------------------------

Subclass :class:`SourcePatternDetector`, decorate with :func:`register`,
implement at least :meth:`find_in_funcdef`:

    @register
    class MyRuleDetector(SourcePatternDetector):
        rule_id = "42"
        title  = "Some new tree-shape lever"

        def find_in_funcdef(self, funcdef, fn_name):
            # walk node.block_items / use generic_visit, yield Candidate(...)
            ...

        # Optional: predict + verify the IR-forest shape that this rule
        # cares about.
        def predict_ir(self, candidate):
            return [TreePattern(cls=TN_BINARY, op=O_AND, ...)]

        def verify_against_ir(self, candidate, ir_forest):
            # default impl iterates predict_ir() and checks `ir_forest`;
            # override only if you need custom logic.
            ...

The base class fills in :meth:`verify_against_ir` from :meth:`predict_ir`,
so most detectors only need to declare their predicted trees.

Run the whole framework:

    from c2.commands.rule_pattern_scan import scan_corpus
    findings = scan_corpus()                       # all registered rules
    findings = scan_corpus(rule_ids=["17b"])       # one rule

Run IR-forest verification against a trace dict:

    from c2.regalloc.trace import parse
    from c2.commands.rule_pattern_scan import verify_corpus_predictions
    trace = parse(open("trace.txt").read())
    results = verify_corpus_predictions(trace)
"""
from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import ClassVar, Iterable, Optional

from pycparser import c_ast

from c2.ir import (
    IRForest,
    TN_ASSIGN, TN_LV_ASSIGN, TN_BINARY, TN_LEAF, TN_CONS,
    N_CONSTANT, N_MEMORY, N_TEMP, N_REGISTER,
)


# ── Candidate (source-pattern match) ──────────────────────────────────────

@dataclass
class Candidate:
    """One source-pattern match.  ``detail`` is rule-specific."""
    rule_id: str
    func: str
    file: str
    line: int
    description: str
    detail: dict = field(default_factory=dict)


# ── Tree-pattern matcher (for IR-forest verification) ─────────────────────

@dataclass
class TreePattern:
    """Declarative shape of a tn / tl / tb node.

    Any field left ``None`` matches anything in that position.  ``name_cls``
    constrains the underlying ``Name`` object for a leaf (e.g. require
    ``N_MEMORY`` for the LHS of an in-place AND).
    """
    kind: Optional[str] = None        # "tn" | "tl" | "tb"
    cls: Optional[int] = None         # TN_* enum value
    op: Optional[int] = None          # cg_op (BINARY/UNARY)
    left: Optional["TreePattern"] = None
    right: Optional["TreePattern"] = None
    name_cls: Optional[int] = None    # leaf-only: the wrapped name`s class
    payload_is_const: Optional[bool] = None   # leaf wraps an N_CONSTANT?

    def matches(self, node) -> bool:
        """Recursively match against a c2.ir.Node."""
        if node is None:
            return self.kind is None and self.cls is None
        if self.kind is not None and node.kind != self.kind:
            return False
        if self.cls is not None and node.cls != self.cls:
            return False
        if self.op is not None and node.op != self.op:
            return False
        if self.name_cls is not None:
            nm = getattr(node, "name", None)
            if nm is None or nm.cls != self.name_cls:
                return False
        if self.payload_is_const is not None:
            nm = getattr(node, "name", None)
            is_const = nm is not None and nm.cls == N_CONSTANT
            if is_const != self.payload_is_const:
                return False
        if self.left is not None and not self.left.matches(getattr(node, "left", None)):
            return False
        if self.right is not None and not self.right.matches(getattr(node, "right", None)):
            return False
        return True


def count_matches(forest: IRForest, pattern: TreePattern) -> int:
    """Count nodes in the forest that match ``pattern``."""
    return sum(1 for n in forest.all_nodes if pattern.matches(n))


# ── Detector base ─────────────────────────────────────────────────────────

class SourcePatternDetector(abc.ABC):
    """Base class for one rule`s source-pattern detector.

    Subclasses set ``rule_id`` and ``title`` (class-level), and implement
    :meth:`find_in_funcdef`.  Optionally override :meth:`predict_ir` to
    declare tree shapes that the IR-forest verifier will look for.
    """
    rule_id: ClassVar[str] = ""
    title: ClassVar[str] = ""

    @abc.abstractmethod
    def find_in_funcdef(self, funcdef: c_ast.FuncDef, fn_name: str
                        ) -> Iterable[Candidate]:
        """Yield :class:`Candidate` records for every source-pattern match
        in this function.  Override per rule."""
        ...

    # ---- Optional IR-forest verification ----------------------------------

    def predict_ir(self, candidate: Candidate) -> list[TreePattern]:
        """Tree shapes the compiler IR should contain when this source
        pattern is present.  Return ``[]`` to opt out of IR verification.
        Subclasses override to declare per-rule predictions."""
        return []

    def verify_against_ir(self, candidate: Candidate, forest: IRForest
                          ) -> dict:
        """Cross-check the candidate against an actual trace IR forest.

        Default impl runs :meth:`predict_ir` and counts how many of each
        pattern the forest contains.  Returns
        ``{"predicted": [...], "found": [...], "consistent": bool}``.
        """
        predictions = self.predict_ir(candidate)
        found = [count_matches(forest, p) for p in predictions]
        # The rule is "consistent" when every prediction has at least one
        # IR-forest match (rules express NECESSARY tree shapes; absence
        # would falsify the mechanism).
        consistent = all(c >= 1 for c in found) if predictions else True
        return {
            "rule_id": self.rule_id,
            "func": candidate.func,
            "predictions": [(repr(p), c) for p, c in zip(predictions, found)],
            "consistent": consistent,
        }


# ── Registry ───────────────────────────────────────────────────────────────

DETECTORS: dict[str, SourcePatternDetector] = {}


def register(cls):
    """Decorator: instantiate the detector and add to :data:`DETECTORS`."""
    if not cls.rule_id:
        raise ValueError(f"{cls.__name__} must set rule_id")
    DETECTORS[cls.rule_id] = cls()
    return cls


def registered_rules() -> list[str]:
    """Stable-sorted list of registered rule ids."""
    return sorted(DETECTORS)


# ── Shared AST helpers ─────────────────────────────────────────────────────

def _is_integral_decl(decl: c_ast.Decl) -> bool:
    """Plain integral decl like ``unsigned char foo = ...;``."""
    if not isinstance(decl.type, c_ast.TypeDecl):
        return False
    if not isinstance(decl.type.type, c_ast.IdentifierType):
        return False
    return any(n in {"char", "short", "int", "long"}
               for n in decl.type.type.names)


def expr_key(node) -> str:
    """Normalised key for an expression -- two nodes return the same string
    iff they reference the same logical lvalue.

    Public helper -- detectors compare lvalues this way."""
    if node is None:
        return ""
    if isinstance(node, c_ast.ID):
        return node.name
    if isinstance(node, c_ast.Constant):
        return f"<{node.type}:{node.value}>"
    if isinstance(node, c_ast.BinaryOp):
        return f"({expr_key(node.left)} {node.op} {expr_key(node.right)})"
    if isinstance(node, c_ast.UnaryOp):
        return f"({node.op}{expr_key(node.expr)})"
    if isinstance(node, c_ast.ArrayRef):
        return f"{expr_key(node.name)}[{expr_key(node.subscript)}]"
    if isinstance(node, c_ast.StructRef):
        return f"{expr_key(node.name)}{node.type}{expr_key(node.field)}"
    if isinstance(node, c_ast.Cast):
        return f"((cast){expr_key(node.expr)})"
    if isinstance(node, c_ast.FuncCall):
        args = (node.args.exprs if node.args else [])
        return f"{expr_key(node.name)}({','.join(expr_key(a) for a in args)})"
    return f"<{type(node).__name__}>"


# ── Rule 17b detector ──────────────────────────────────────────────────────

@register
class Rule17bDetector(SourcePatternDetector):
    """Intermediate temp blocks AND/OR direct-memory-RMW.

    Pattern: ``TYPE temp = LHS & MASK ; LHS = temp ; LHS = temp | BIT ;``
    where LHS is the same lvalue in all three references.

    Predicted IR (when the pattern is present):
      * A ``TN_ASSIGN`` whose right is ``TN_BINARY(O_AND, *, TN_CONS)`` --
        the ``temp = LHS & MASK`` statement.
      * Subsequent ``TN_ASSIGN``\\(s) whose right is ``TN_BINARY(O_OR,
        TN_LEAF(temp), TN_CONS)`` -- the ``LHS = temp | BIT`` statements.

    When the SAME function is recompiled with the temp removed, the IR
    forest should NOT contain a ``TN_BINARY(O_AND, *, TN_CONS)`` node whose
    parent ``TN_ASSIGN`` targets a TEMP -- the direct-memory-RMW form goes
    through ``TN_PRE_GETS`` (op = O_AND_PRE_GETS) instead.
    """
    rule_id = "17b"
    title = "Intermediate temp blocks AND/OR direct-memory-RMW"

    def find_in_funcdef(self, funcdef: c_ast.FuncDef, fn_name: str):
        coll = _17bWalker(fn_name)
        try:
            coll.visit(funcdef)
        except Exception:
            return []
        return coll.matches

    def predict_ir(self, candidate: Candidate) -> list[TreePattern]:
        # TN_ASSIGN with RHS = TN_BINARY(O_AND, *, TN_CONS)
        # cg_op O_AND = 9 (from c2.commands.divisor_hints / cgdefs.h)
        O_AND = 9
        O_OR = 10
        return [
            # The `s = X & MASK` statement -- TN_ASSIGN whose right is the AND.
            TreePattern(
                cls=TN_ASSIGN,
                right=TreePattern(cls=TN_BINARY, op=O_AND,
                                  right=TreePattern(cls=TN_CONS)),
            ),
            # The `X = s | BIT` statement -- TN_ASSIGN whose right is the OR
            # of (some leaf, const).
            TreePattern(
                cls=TN_ASSIGN,
                right=TreePattern(cls=TN_BINARY, op=O_OR,
                                  right=TreePattern(cls=TN_CONS)),
            ),
        ]


class _17bWalker(c_ast.NodeVisitor):
    def __init__(self, fn_name: str):
        self.fn_name = fn_name
        self.matches: list[Candidate] = []

    def visit_Compound(self, node: c_ast.Compound) -> None:
        block_items = node.block_items or []
        for i, item in enumerate(block_items):
            if not isinstance(item, c_ast.Decl):
                continue
            if not _is_integral_decl(item):
                continue
            init = item.init
            if not (isinstance(init, c_ast.BinaryOp) and init.op == "&"):
                continue
            if not isinstance(init.right, c_ast.Constant):
                continue
            temp_name = item.name
            lhs_key = expr_key(init.left)
            plain = 0
            or_uses = 0
            for later in block_items[i + 1:]:
                p, o = _count_17b_uses(later, temp_name, lhs_key)
                plain += p
                or_uses += o
            if plain >= 1 and or_uses >= 1:
                coord = item.coord
                self.matches.append(Candidate(
                    rule_id="17b",
                    func=self.fn_name,
                    file=coord.file if coord and coord.file else "?",
                    line=coord.line if coord and coord.line else 0,
                    description=(f"intermediate temp `{temp_name}` blocks "
                                 f"direct memory RMW of `{lhs_key}`"),
                    detail={"temp_name": temp_name, "lhs_key": lhs_key,
                            "or_uses": or_uses},
                ))
        # Descend into nested compounds.
        self.generic_visit(node)


def _count_17b_uses(node, temp_name: str, lhs_key: str) -> tuple[int, int]:
    plain, or_count = 0, 0
    if isinstance(node, c_ast.Assignment) and node.op == "=":
        if expr_key(node.lvalue) == lhs_key:
            rhs = node.rvalue
            if isinstance(rhs, c_ast.ID) and rhs.name == temp_name:
                plain += 1
            elif (isinstance(rhs, c_ast.BinaryOp)
                  and rhs.op == "|"
                  and isinstance(rhs.left, c_ast.ID)
                  and rhs.left.name == temp_name):
                or_count += 1
    for _, child in node.children():
        p, o = _count_17b_uses(child, temp_name, lhs_key)
        plain += p
        or_count += o
    return plain, or_count


# ── Public scan API ────────────────────────────────────────────────────────

def find_candidates(funcdefs_by_name: dict[str, c_ast.FuncDef],
                    rule_ids: Optional[list[str]] = None
                    ) -> dict[str, list[Candidate]]:
    """Run all (or a subset of) registered detectors over a mapping
    ``{func_name: FuncDef}``.

    Returns ``{rule_id: [Candidate, ...]}``.
    """
    targets = rule_ids if rule_ids is not None else registered_rules()
    out: dict[str, list[Candidate]] = {r: [] for r in targets}
    for fn_name, funcdef in funcdefs_by_name.items():
        for rid in targets:
            detector = DETECTORS.get(rid)
            if detector is None:
                continue
            out[rid].extend(detector.find_in_funcdef(funcdef, fn_name))
    return out


def scan_corpus(rule_ids: Optional[list[str]] = None
                ) -> dict[str, list[Candidate]]:
    """Scan the full caesar2 source corpus for all registered rule patterns.
    Returns ``{rule_id: [Candidate, ...]}``."""
    from c2.commands.style_check import _source_index
    index = _source_index()
    funcdefs = {name: funcdef for name, (_p, funcdef, _s) in index.items()}
    return find_candidates(funcdefs, rule_ids=rule_ids)


def verify_corpus_predictions(trace_dict: dict,
                              rule_ids: Optional[list[str]] = None
                              ) -> list[dict]:
    """For every candidate found via :func:`scan_corpus`, verify the
    detector`s predicted IR shape against the corresponding trace IR forest.

    ``trace_dict`` is the output of :func:`c2.regalloc.trace.parse`.
    Returns a list of result dicts (one per candidate that had a matching
    routine in the trace).
    """
    by_func: dict[str, IRForest] = {}
    for ro in trace_dict.get("routines", []):
        # Routines map to source functions via the trace`s ``by_func`` index
        # (populated by trace_compile / corpus_trace).  We accept either
        # form: a flat by_func mapping in the trace, or per-routine.
        if "by_func" in trace_dict:
            for name, idx_or_ro in trace_dict["by_func"].items():
                idx = (idx_or_ro.get("index")
                       if isinstance(idx_or_ro, dict) else idx_or_ro)
                if ro.get("index") == idx and "ir" in ro:
                    by_func[name] = ro["ir"]
                    break
        elif "ir" in ro:
            # Fallback: keyless association.
            by_func.setdefault(f"routine_{ro.get('index', '?')}", ro["ir"])

    candidates_by_rule = scan_corpus(rule_ids=rule_ids)
    results: list[dict] = []
    for rid, cands in candidates_by_rule.items():
        detector = DETECTORS[rid]
        for cand in cands:
            forest = by_func.get(cand.func)
            if forest is None:
                continue
            results.append(detector.verify_against_ir(cand, forest))
    return results


# ── Back-compat shim (old API used by existing tests) ──────────────────────

# Pre-refactor names kept as aliases.
Rule17bCandidate = Candidate


def find_rule_17b_candidates(funcdefs_by_name: dict
                              ) -> list[Candidate]:
    """Back-compat: return only Rule 17b candidates from a pre-parsed
    mapping."""
    return find_candidates(funcdefs_by_name, rule_ids=["17b"])["17b"]

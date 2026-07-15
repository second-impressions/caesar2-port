"""Rule 154 detector — goto-tail-with-body vs if/else source-form distinguisher.

Source-form ambiguity arises when:

    if (X) {                       if (!X) {
        body_a;                        body_b;
        goto LABEL;        vs      } else {
    }                                  body_a;
    body_b;                        }
    LABEL: ...                     LABEL: ...

Both compile to similar PS asm.  Byte signature distinguishes them only
when ``body_a >= 1`` statement (validated synthetically in
``docs/codegen-experiments/goto-vs-ifelse.py``).  For ``body_a == 0``
the byte output is identical -- equivalence class, no rewrite.

The asm signal: **the size (bytes / insn count) of the fall-through
block after the gating jcc**.  In goto form, the fall-through is
body_a (short).  In if/else form, the fall-through is body_b (long).

This module exposes:

  * :func:`detect_candidates(func)` -- AST walker returning candidate
    sites in a function.
  * :func:`classify_via_asm(name, candidate)` -- maps a candidate to a
    PS-asm verdict (``goto`` / ``ifelse`` / ``equivalence``).
  * :func:`render_rule154_hint(name)` -- the ``decomp-verify -v``
    one-line hint when a candidate is a rewrite target.

See Rule 154 in ``docs/watcom-codegen-patterns.md`` for the full story.
"""

from __future__ import annotations

import collections
from dataclasses import dataclass, field
from typing import Optional

from pycparser import c_ast

from c2.commands.disasm import disasm_function
from c2.commands.insn_ast import _decode_raw

_JCC = frozenset({
    'je', 'jne', 'jl', 'jle', 'jg', 'jge',
    'jb', 'jbe', 'ja', 'jae',
    'jz', 'jnz', 'js', 'jns', 'jo', 'jno',
})


@dataclass
class GotoIfElseCandidate:
    """One AST site: `if (X) { body_a; goto LABEL; } body_b; LABEL: ...`."""
    label: str
    if_line: int
    label_line: int
    body_a_size: int   # # statements in iftrue before the goto
    body_b_size: int   # # statements between if and label
    after_label_size: int  # # statements after the label
    has_else: bool

    @property
    def is_equivalence_class(self) -> bool:
        """True iff body_a == 0 -- both source forms produce identical bytes."""
        return self.body_a_size == 0

    @property
    def is_rewrite_candidate(self) -> bool:
        """True iff body_a >= 1 (distinguishable) AND body_b >= body_a (worth swapping)."""
        return self.body_a_size >= 1 and self.body_b_size >= self.body_a_size


class _GotoCollector(c_ast.NodeVisitor):
    def __init__(self) -> None:
        self.labels: dict[str, tuple[c_ast.Label, list]] = {}
        self.gotos: list[tuple[c_ast.Goto, list]] = []
        self._stack: list[c_ast.Node] = []

    def generic_visit(self, node: c_ast.Node) -> None:
        self._stack.append(node)
        for _, c in node.children():
            self.visit(c)
        self._stack.pop()

    def visit_Label(self, node: c_ast.Label) -> None:
        self.labels[node.name] = (node, list(self._stack))
        self.generic_visit(node)

    def visit_Goto(self, node: c_ast.Goto) -> None:
        self.gotos.append((node, list(self._stack)))
        self.generic_visit(node)


def _count_stmts(stmt: Optional[c_ast.Node]) -> int:
    if stmt is None:
        return 0
    if isinstance(stmt, c_ast.Compound):
        return len(stmt.block_items or [])
    return 1


def _nearest_terminating_if(
    parent_chain: list[c_ast.Node],
    goto_node: c_ast.Goto,
) -> tuple[Optional[c_ast.If], Optional[str]]:
    """Find the innermost ``If`` node whose iftrue (or iffalse) body's LAST
    statement is this goto.  Returns ``(if_node, branch)`` or ``(None, None)``.
    """
    for i in range(len(parent_chain) - 1, -1, -1):
        p = parent_chain[i]
        if isinstance(p, c_ast.If):
            for branch_name in ('iftrue', 'iffalse'):
                branch = getattr(p, branch_name)
                if isinstance(branch, c_ast.Compound) and branch.block_items:
                    if branch.block_items[-1] is goto_node:
                        return p, branch_name
                elif branch is goto_node:
                    return p, branch_name
            return None, None  # found an If but not the terminating stmt
    return None, None


def detect_candidates(func: c_ast.FuncDef) -> list[GotoIfElseCandidate]:
    """Walk a function and return all `if (X) { body_a; goto LABEL; } body_b; LABEL: ...` sites."""
    gc = _GotoCollector()
    gc.visit(func.body)
    goto_target_count = collections.Counter(g.name for g, _ in gc.gotos)
    body_items = (func.body.block_items or [])
    out: list[GotoIfElseCandidate] = []

    for goto_node, parent_chain in gc.gotos:
        if_node, branch = _nearest_terminating_if(parent_chain, goto_node)
        if if_node is None or branch != 'iftrue':
            continue
        if goto_target_count[goto_node.name] != 1:
            continue  # multiple gotos -- Rule 92 funnel, NOT a candidate
        label_info = gc.labels.get(goto_node.name)
        if not label_info:
            continue
        label_node, label_parents = label_info
        # Both label and if must be at function-body top level
        if not (label_parents and label_parents[0] is func.body):
            continue
        if not (parent_chain and parent_chain[0] is func.body):
            continue
        try:
            p_if = body_items.index(if_node)
            p_label = body_items.index(label_node)
        except ValueError:
            continue
        if p_label <= p_if:
            continue
        body_b_size = p_label - p_if - 1
        if body_b_size < 1:
            continue
        body_a_size = _count_stmts(if_node.iftrue) - 1
        out.append(GotoIfElseCandidate(
            label=goto_node.name,
            if_line=if_node.coord.line if if_node.coord else 0,
            label_line=label_node.coord.line if label_node.coord else 0,
            body_a_size=body_a_size,
            body_b_size=body_b_size,
            after_label_size=len(body_items) - p_label - 1,
            has_else=if_node.iffalse is not None,
        ))
    return out


@dataclass
class JccFallThrough:
    """One jcc + the fall-through block size measured to the next ``jmp``/``ret``."""
    jcc_addr: int
    jcc_line: int   # propagated PS -d1 line
    jcc_mnem: str
    target_addr: int
    fall_size_bytes: int
    fall_insn_count: int
    fall_terminator_addr: int


def analyze_jcc_fall_through(name: str) -> list[JccFallThrough]:
    """For every forward jcc in a function, measure the fall-through block size."""
    try:
        _, _, lines = disasm_function(name)
    except Exception:
        return []
    addr_to_idx = {ln.address: i for i, ln in enumerate(lines)}
    propagated: list[int] = []
    cur = 0
    for ln in lines:
        if ln.line:
            cur = ln.line
        propagated.append(cur)
    out: list[JccFallThrough] = []
    for i, ln in enumerate(lines):
        ins = _decode_raw(bytes(ln.bytes_), ln.address) if ln.bytes_ else None
        if not ins or ins.mnemonic not in _JCC:
            continue
        if not ins.ops or not ins.ops[0].is_imm:
            continue
        tgt = ins.ops[0].imm
        if tgt <= ln.address:
            continue
        k = i + 1
        fall_size = 0
        terminator: Optional[int] = None
        while k < len(lines) and lines[k].address < tgt:
            kln = lines[k]
            kins = _decode_raw(bytes(kln.bytes_), kln.address) if kln.bytes_ else None
            fall_size += len(kln.bytes_)
            if kins and kins.mnemonic in ('jmp', 'ret') or (kins and kins.mnemonic.startswith('ret')):
                terminator = kln.address
                break
            k += 1
        if terminator is None:
            continue
        out.append(JccFallThrough(
            jcc_addr=ln.address,
            jcc_line=propagated[i],
            jcc_mnem=ins.mnemonic,
            target_addr=tgt,
            fall_size_bytes=fall_size,
            fall_insn_count=k - i,
            fall_terminator_addr=terminator,
        ))
    return out


def classify_via_asm(
    name: str,
    candidate: GotoIfElseCandidate,
    *,
    stmt_bytes: int = 8,
) -> Optional[str]:
    """Classify a candidate by matching its body_a / body_b sizes against the
    PS asm jcc fall-through sizes.

    Returns:
      * ``'equivalence'``  if ``body_a == 0`` (forms are byte-identical)
      * ``'goto'``         if the asm signal matches goto form (fall-through ~ body_a)
      * ``'ifelse'``       if the asm signal matches if/else form (fall-through ~ body_b)
      * ``None``           if no clean jcc gate can be identified

    ``stmt_bytes`` is the average instruction-bytes-per-statement estimate
    used to compare body_a/b sizes against fall-through bytes (default 8).
    """
    if candidate.is_equivalence_class:
        return 'equivalence'
    jccs = analyze_jcc_fall_through(name)
    if not jccs:
        return None
    # Look for a jcc whose fall-through block size closely matches body_a*stmt_bytes
    # (the goto-form fingerprint) or body_b*stmt_bytes (the if/else fingerprint).
    body_a_est = candidate.body_a_size * stmt_bytes + 5  # + jmp size
    body_b_est = candidate.body_b_size * stmt_bytes + 5
    # Pick the jcc whose fall-through is closest to EITHER estimate
    best_dist = float('inf')
    best_verdict: Optional[str] = None
    for j in jccs:
        d_goto = abs(j.fall_size_bytes - body_a_est)
        d_ifelse = abs(j.fall_size_bytes - body_b_est)
        d = min(d_goto, d_ifelse)
        if d < best_dist:
            best_dist = d
            best_verdict = 'goto' if d_goto < d_ifelse else 'ifelse'
    return best_verdict

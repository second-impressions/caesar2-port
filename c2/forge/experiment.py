"""``Forge`` -- the targeted, low-boilerplate cgex successor.

Design intent (per the brief that drove the rewrite):

  * **Replace cgex's investigative experiments**, NOT the corpus sweeper.
    The unit of work is "I am stuck on function X; here are 8 things I
    want to try; tell me which combination wins."
  * **Targeted DSL**: ``swap_decls("a", "b")``, ``commute_at(line=42)``,
    ``try_type("count", ["short","int","unsigned int"])``,
    ``insert_local("c_g", "int", "g_int", before_line=40)`` -- one line
    per hypothesis, no AST scaffolding visible to the user.
  * **Massive composition is the goal, not a side-effect**.  The lever
    presets feed THOUSANDS of variants from the CARTESIAN PRODUCT of a
    small candidate pool, because the real wins come from MULTIPLE
    CHANGES APPLIED TOGETHER, not from a single edit.
  * **Text-preserving edits**.  No CGenerator regen.  Source bytes
    outside the edited range survive exactly -- comments, indent, brace
    style, the observed-source-style.md conventions are inviolable.

Usage::

    with Forge("show_menus", file="controls.c") as f:
        # Targeted hypotheses (each adds ONE candidate to the pool):
        f.swap_decls("sx", "sy")
        f.swap_statements(line_a=143, line_b=145)
        f.commute_at(line=147, op="+")
        f.try_type("count", ["short", "unsigned short", "unsigned int"])
        f.insert_local("c_g", "int", "g_int", before_line=140)

        # Preset packs (each adds DOZENS of candidates discovered via AST):
        f.preset("tie_group")           # firstassign + decl_order + stmt_swap
        f.preset("commute_all")         # one candidate per commutative binop
        f.preset("type_sweep", restrict=["sx","sy","count"])

        # Search modes:
        f.run("each")                   # try each candidate alone
        f.run("pairs")                  # every 2-combination
        f.run("triples")                # every 3-combination
        f.run(depth=4, max_variants=5000)  # depth-4 product, capped

        # OR the all-in-one:
        f.run_all()                     # depth = candidate-count, no cap

"""

from __future__ import annotations

import contextlib
import io
import itertools
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterator

from c2.forge import cspan, ps_ref
from c2.forge.edits import Candidate, EditPlan, TextEdit, baseline_plan, plan_ok
from c2.forge.judge import Score


@dataclass
class PlanResult:
    """Score for one EditPlan (one tried variant)."""

    plan: EditPlan
    score: Score
    shape_delta: int = 0
    bytes_delta: int = 0

    def __repr__(self) -> str:                # interactive-friendly
        tag = "✓" if self.score.bytes == 0 else " "
        return (f"<PlanResult {tag} shape={self.score.shape_total}"
                f"(Δ{self.shape_delta:+d}) "
                f"bytes={self.score.bytes}(Δ{self.bytes_delta:+d}) "
                f"plan='{self.plan.name}'>")


@dataclass
class Summary:
    """``Forge.run`` output: baseline + every tried plan."""

    function: str
    file: str
    baseline: Score
    plans: list[PlanResult] = field(default_factory=list)
    elapsed_s: float = 0.0
    skipped_overlap: int = 0          # plans dropped: candidates overlap
    duplicates: int = 0               # plans dropped: same fingerprint
    build_failures: int = 0
    candidates_total: int = 0

    def winners(self, matrix=None) -> list[PlanResult]:
        """Plans that IMPROVE on baseline, judged by the DecisionMatrix
        (default: strict lex fix-order -- the honest per-function judge
        per AGENTS.md; an ir drop is a win even when bytes rise, and
        byte-exact always wins).

        The matrix carries the TYPE-edit width guard (2026-07-03
        metric-gaming defence) and, for ``policy="lex+weighted"``, the
        composite fallback with the ir/islands hard guards.  See
        :mod:`c2.forge.matrix`.
        """
        from c2.forge.matrix import DecisionMatrix
        m = matrix or DecisionMatrix(policy="lex")
        out = []
        for p in self.plans:
            if not p.score.ok:
                continue
            has_type = any(c.name.startswith(("type(", "paramtype("))
                           for c in p.plan.candidates)
            if m.accepts(p.score, self.baseline, has_type_edit=has_type):
                out.append(p)
        return out

    def pareto(self) -> list[PlanResult]:
        """The Pareto front over ``(ir, isl, width, spill, seat,
        bytes)`` among plans that don't regress the shape-truth layers
        -- "the different wins": mutually incomparable trade-offs,
        each a candidate branch to explore."""
        from c2.forge.matrix import dominates, pareto_front
        b = self.baseline
        bvec = b.layers + (b.bytes,)
        pool = [p for p in self.plans
                if p.score.ok
                and p.score.layers[0] <= b.layers[0]
                and p.score.layers[1] <= b.layers[1]]
        front = pareto_front(pool)
        return [p for p in front
                if (v := p.score.layers + (p.score.bytes,)) != bvec
                and not dominates(bvec, v)]

    def best(self, matrix=None) -> PlanResult | None:
        from c2.forge.matrix import DecisionMatrix
        m = matrix or DecisionMatrix(policy="lex")
        winners = self.winners(m)
        if not winners:
            return None
        winners.sort(key=lambda p: m.rank_key(p.score, self.baseline)
                     + (-len(p.plan.candidates),))
        return winners[0]

    def __repr__(self) -> str:
        wins = len(self.winners())
        return (f"<Summary {self.function} "
                f"baseline=shape{self.baseline.shape_total}/bytes"
                f"{self.baseline.bytes}, {len(self.plans)} plans tried, "
                f"{wins} winning, {self.elapsed_s:.1f}s>")

    def show(self, top: int = 15, file=None) -> None:
        import sys
        f = file or sys.stdout
        b = self.baseline
        print(f"\nbaseline ({self.function}, {self.file}):  "
              f"shape={b.shape_total}  bytes={b.bytes}  "
              f"fix_next={b.fix_next}", file=f)
        print(f"candidates: {self.candidates_total}, "
              f"plans: {len(self.plans)} tried, "
              f"{self.skipped_overlap} skipped (overlap), "
              f"{self.duplicates} dedup, "
              f"{self.build_failures} build-fail, "
              f"{self.elapsed_s:.1f}s", file=f)
        winners = self.winners()
        if not winners:
            front = self.pareto()
            print("\nNO IMPROVING PLAN.\n"
                  "  (every variant tied or regressed vs baseline"
                  + (f"; {len(front)} lateral trade-off(s) on the "
                     f"pareto front -- summary.pareto())" if front
                     else ")"), file=f)
            return
        front = self.pareto()
        print(f"\n{len(winners)} winning plan(s), "
              f"{len(front)} on the pareto front.  "
              f"Top {min(top, len(winners))}:",
              file=f)
        winners.sort(key=lambda p: (p.score.layers, p.score.bytes))
        bl = b.layers
        for i, p in enumerate(winners[:top], 1):
            pl = p.score.layers
            lay = f"ir{pl[0]} i{pl[1]} w{pl[2]} sp{pl[3]} st{pl[4]}"
            base = f"ir{bl[0]} i{bl[1]} w{bl[2]} sp{bl[3]} st{bl[4]}"
            print(f"  {i:>3d}  [{lay} <- {base}]  "
                  f"bytes={p.score.bytes:<4d} \u0394b={p.bytes_delta:+4d}  "
                  f"({len(p.plan.candidates)}x)  {p.plan.name}", file=f)


class Forge:
    """One investigative experiment for ONE function.

    Construct, add candidates via the targeted DSL, ``run()``, read the
    Summary.  All state is in-process; nothing persists unless you call
    ``apply()`` to splice the winning plan into the live source file.
    """

    def __init__(self, function: str, *, file: str,
                 cflags: str | None = None, image: str | None = None,
                 source_root: Path | str | None = None):
        self.function = function
        self.file = file
        self.cflags = cflags
        self.image = image
        self.source_root = (Path(source_root) if source_root
                            else Path("decomp"))
        src_path = self.source_root / "src" / file
        if not src_path.exists():
            raise FileNotFoundError(src_path)
        self._file_path = src_path
        # Raw source text + a lazily-built tree-sitter span index (see
        # the ``fs`` property).  All DSL queries and presets run on
        # byte-exact spans of THIS text; nothing re-parses per
        # candidate.
        self.text: str = src_path.read_text()
        self._fs = None
        self.__line_starts: list[int] | None = None
        _ = self.fs                        # fail fast if fn not found
        self._candidates: list[Candidate] = []
        # Persistent warm pool (set by session() / persistent_pool());
        # None means each run() opens + tears down its own pool.  Reuse
        # across runs is the big interactive win -- worker warm-up is
        # ~250 ms each, and an iterative REPL session typically runs
        # 5-20 times.
        self._pool = None

    def __repr__(self) -> str:
        pool_tag = " pool=warm" if self._pool is not None else ""
        return (f"<Forge {self.function} ({self.file}) "
                f"{len(self._candidates)} candidate(s){pool_tag}>")


    def candidate(self, name: str, *edits: TextEdit,
                  note: str = "") -> "Forge":
        """Append a manually-constructed candidate (escape hatch).

        Most users should reach for the named DSL methods (``swap_decls``,
        ``commute_at`` etc.) instead -- this one is for cases the named
        DSL doesn't cover.
        """
        self._candidates.append(Candidate(
            name=name, edits=tuple(edits), note=note,
        ))
        return self

    # DSL infrastructure (tree-sitter spans; see c2.forge.cspan)

    @property
    def fs(self) -> "cspan.FnSpan":
        """The tree-sitter span index for this function (built once)."""
        if self._fs is None:
            self._fs = cspan.fnspan(self.text, self.function)
            if self._fs is None:
                raise KeyError(
                    f"function {self.function!r} not found in "
                    f"{self._file_path} (or tree-sitter unavailable)")
        return self._fs

    def _line_span(self, line: int) -> tuple[int, int]:
        """(start, end) char offsets of a 1-based source line
        (end just past the newline)."""
        starts = self._line_starts
        if not 1 <= line <= len(starts):
            raise IndexError(f"line {line} out of range")
        start = starts[line - 1]
        end = starts[line] if line < len(starts) else len(self.text)
        return start, end

    @property
    def _line_starts(self) -> list[int]:
        if self.__line_starts is None:
            starts = [0]
            for i, ch in enumerate(self.text):
                if ch == "\n":
                    starts.append(i + 1)
            self.__line_starts = starts
        return self.__line_starts

    def _stmt_at_line(self, line: int):
        """The statement node starting on the given source line (any
        block depth; first match in document order)."""
        fs = self.fs
        best = None
        for comp in fs.compounds():
            for st in fs.statements_of(comp):
                if fs.line_no(st) == line \
                        and (best is None
                             or st.start_byte < best.start_byte):
                    best = st
        return best

    def _decl_node(self, name: str):
        """The declaration node introducing ``name`` (any depth)."""
        from c2.forge.cspan import _declared_names, walk_named
        fs = self.fs
        for n in walk_named(fs.body):
            if n.type != "declaration":
                continue
            for d in n.children_by_field_name("declarator"):
                if name in _declared_names(d):
                    return n
        return None


    def swap_decls(self, name_a: str, name_b: str) -> "Forge":
        """Swap the WHOLE LINES of two declarations identified by name."""
        fs = self.fs
        a = self._decl_node(name_a)
        b = self._decl_node(name_b)
        if a is None or b is None:
            raise KeyError(
                f"swap_decls: declaration "
                f"{name_a if a is None else name_b!r} not in body")
        sa, ea = fs.full_line_span(a)
        sb, eb = fs.full_line_span(b)
        return self.candidate(
            f"swap_decls({name_a},{name_b})",
            TextEdit(start=sa, end=ea, replacement=self.text[sb:eb],
                     note="A<-B"),
            TextEdit(start=sb, end=eb, replacement=self.text[sa:ea],
                     note="B<-A"),
        )

    def try_type(self, decl_name: str, types: list[str]) -> "Forge":
        """For each type in ``types``, add a candidate that rewrites the
        named decl's type words.  N types == N candidates."""
        d = self._decl_node(decl_name)
        if d is None:
            raise KeyError(f"try_type: decl {decl_name!r} not in body")
        tnode = d.child_by_field_name("type")
        if tnode is None:
            raise KeyError(f"try_type: decl {decl_name!r} has no type node")
        for t in types:
            self.candidate(
                f"type({decl_name}={t})",
                TextEdit(start=tnode.start_byte, end=tnode.end_byte,
                         replacement=t),
            )
        return self

    def set_type(self, decl_name: str, new_type: str) -> "Forge":
        """Single-candidate form of ``try_type``."""
        return self.try_type(decl_name, [new_type])


    def swap_statements(self, *, line_a: int, line_b: int) -> "Forge":
        """Swap two statements identified by their (1-based) starting
        source lines (ANY block depth; spans are exact, so multi-line
        statements and packed lines are handled)."""
        a = self._stmt_at_line(line_a)
        b = self._stmt_at_line(line_b)
        if a is None or b is None:
            raise KeyError(
                f"swap_statements: no stmt starting at line "
                f"{line_a if a is None else line_b}")
        fs = self.fs
        return self.candidate(
            f"swap_stmts(L{line_a},L{line_b})",
            TextEdit(start=a.start_byte, end=a.end_byte,
                     replacement=fs.src(b)),
            TextEdit(start=b.start_byte, end=b.end_byte,
                     replacement=fs.src(a)),
        )

    def replace_line(self, line: int, new_text: str) -> "Forge":
        """Replace the WHOLE LINE at ``line`` (1-based) with ``new_text``."""
        start, end = self._line_span(line)
        if not new_text.endswith("\n"):
            new_text = new_text + "\n"
        return self.candidate(
            f"replace_line(L{line})",
            TextEdit(start=start, end=end, replacement=new_text),
        )

    def insert_before_line(self, line: int, text: str,
                           note: str = "") -> "Forge":
        """Insert ``text`` (newline added if absent) just before the
        source line ``line``."""
        if not text.endswith("\n"):
            text = text + "\n"
        start, _ = self._line_span(line)
        return self.candidate(
            note or f"insert_before(L{line})",
            TextEdit(start=start, end=start, replacement=text),
        )

    def insert_after_line(self, line: int, text: str,
                          note: str = "") -> "Forge":
        if not text.endswith("\n"):
            text = text + "\n"
        _, end = self._line_span(line)
        return self.candidate(
            note or f"insert_after(L{line})",
            TextEdit(start=end, end=end, replacement=text),
        )

    def insert_local(self, name: str, type_: str, init: str,
                     *, before_line: int | None = None,
                     after_line: int | None = None,
                     indent: str = "    ") -> "Forge":
        """Inject ``<type> <name> = <init>;`` as a fresh local."""
        decl_line = f"{indent}{type_} {name} = {init};"
        if before_line is not None:
            return self.insert_before_line(
                before_line, decl_line,
                note=f"local({name}={init})@before-L{before_line}")
        if after_line is not None:
            return self.insert_after_line(
                after_line, decl_line,
                note=f"local({name}={init})@after-L{after_line}")
        # Default: end of the leading decl run (C89-safe).
        anchor = self.fs.top_decl_anchor()
        if anchor is None:
            raise ValueError("insert_local: no executable statement found")
        return self.candidate(
            f"local({name}={init})@auto",
            TextEdit(start=anchor, end=anchor,
                     replacement=decl_line + "\n"),
        )


    def _binops_at(self, line: int, op: str | None = None) -> list:
        from c2.forge.presets import _binops
        out = []
        for n, op_t, l, r in _binops(self.fs):
            if self.fs.line_no(n) != line:
                continue
            if op is not None and op_t != op:
                continue
            out.append((n, op_t, l, r))
        out.sort(key=lambda t: t[0].start_byte)
        return out

    def commute_at(self, *, line: int, op: str | None = None,
                   nth: int = 0) -> "Forge":
        """Commute the ``nth`` binop on ``line`` (optionally filtered
        by ``op``).  Operands are parenthesised (source parens inside
        the span survive; precedence cannot shift)."""
        from c2.forge.presets import _paren
        cands = self._binops_at(line, op)
        if nth >= len(cands):
            raise IndexError(
                f"commute_at: line {line} has {len(cands)} matching "
                f"binop(s); asked for #{nth}")
        n, op_t, l, r = cands[nth]
        fs = self.fs
        if fs.src(l) == fs.src(r):
            return self                           # no-op
        return self.candidate(
            f"commute({op_t}@L{line}#{nth})",
            TextEdit(start=l.start_byte, end=r.end_byte,
                     replacement=f"{_paren(fs, r)} {op_t} {_paren(fs, l)}"),
        )

    def commute_all_in(self, line_range: tuple[int, int],
                       op: str | None = None) -> "Forge":
        """One candidate per commutable binop in the inclusive line
        range."""
        from c2.forge.presets import _COMMUTATIVE_OPS, _binops, _paren
        a, b = line_range
        fs = self.fs
        for n, op_t, l, r in _binops(fs):
            if not (a <= fs.line_no(n) <= b):
                continue
            if op_t not in _COMMUTATIVE_OPS:
                continue
            if op is not None and op_t != op:
                continue
            if fs.src(l) == fs.src(r):
                continue
            self.candidate(
                f"commute({op_t}@L{fs.line_no(n)})",
                TextEdit(start=l.start_byte, end=r.end_byte,
                         replacement=f"{_paren(fs, r)} {op_t} "
                                     f"{_paren(fs, l)}"),
            )
        return self

    def move_statement(self, *, from_line: int, to_line: int) -> "Forge":
        """Move the statement starting at ``from_line`` to appear
        BEFORE the statement at ``to_line`` (any block depth)."""
        src = self._stmt_at_line(from_line)
        dst = self._stmt_at_line(to_line)
        if src is None or dst is None:
            raise KeyError(
                f"move_statement: no stmt starting at line "
                f"{from_line if src is None else to_line}")
        if src.start_byte == dst.start_byte:
            return self                            # no-op
        fs = self.fs
        from c2.forge.presets import _del_stmt_edit
        moved = fs.src(src)
        indent = fs.indent_of(dst)
        ins_at = fs.line_start(dst.start_byte)
        return self.candidate(
            f"move_stmt(L{from_line}->before-L{to_line})",
            _del_stmt_edit(fs, src, "delete"),
            TextEdit(start=ins_at, end=ins_at,
                     replacement=f"{indent}{moved}\n", note="insert"),
        )

    def de_invent(self, var_name: str) -> "Forge":
        """Delete a single-assignment local (``T x = E;`` init-decl or
        the strict-C89 ``T x; ... x = E;`` split form) and inline
        ``(E)`` at every READ of ``x`` (Rule 67 / §10; exact occurrence
        spans -- packed multi-read lines are handled).  Raises
        ``ValueError`` when the local is not eligible."""
        from c2.forge.presets import de_invent_candidates
        added = de_invent_candidates(self, only=var_name)
        if added == 0:
            raise ValueError(
                f"de_invent({var_name!r}): local not eligible "
                f"(not found / multiple writes / address taken / "
                f"unstable RHS)")
        return self

    def cache_global(self, global_name: str, type_: str = "int",
                     *, before_line: int | None = None,
                     cache_name: str | None = None) -> "Forge":
        """Inject ``<type> <cache_name> = <global_name>;`` at the top
        of the body and rewrite every downstream READ of the global to
        the cache (lvalues, field names, and callees are left alone --
        the Rule 116 cache-introduction lever)."""
        from c2.forge.cspan import walk_named
        fs = self.fs
        cache_name = cache_name or f"c_{global_name}"
        anchor = (self._line_span(before_line)[0]
                  if before_line is not None
                  else fs.top_decl_anchor())
        if anchor is None:
            raise ValueError(
                "cache_global: no executable statement found in body")
        edits = [TextEdit(
            start=anchor, end=anchor,
            replacement=f"    {type_} {cache_name} = {global_name};\n",
            note="insert cache decl")]
        n_reads = 0
        for n in walk_named(fs.body):
            if n.type != "identifier" or fs.src(n) != global_name:
                continue
            if n.start_byte < anchor:
                continue
            p = n.parent
            if p is not None and (
                    (p.type == "assignment_expression"
                     and p.child_by_field_name("left") == n)
                    or p.type == "update_expression"
                    or (p.type == "field_expression"
                        and p.child_by_field_name("field") == n)
                    or (p.type == "call_expression"
                        and p.child_by_field_name("function") == n)):
                continue
            edits.append(TextEdit(
                start=n.start_byte, end=n.end_byte,
                replacement=cache_name,
                note=f"rewrite@L{fs.line_no(n)}"))
            n_reads += 1
        if n_reads == 0:
            raise ValueError(
                f"cache_global({global_name!r}): no readable use found")
        return self.candidate(
            f"cache_global({global_name}=>{cache_name}:{type_})", *edits)

    def add_else_if(self, *, else_line: int, condition: str) -> "Forge":
        """Convert ``else {{ ... }}`` on ``else_line`` into
        ``else if (<condition>) {{ ... }}`` (Rule 152)."""
        from c2.forge.cspan import walk_named
        fs = self.fs
        for n in walk_named(fs.body):
            if n.type != "if_statement":
                continue
            alt = n.child_by_field_name("alternative")
            if alt is None or alt.type != "else_clause":
                continue
            if alt.start_point[0] + 1 != else_line:
                continue
            kids = [c for c in alt.named_children if c.type != "comment"]
            if kids and kids[0].type == "if_statement":
                raise ValueError(
                    f"add_else_if: line {else_line} is already an "
                    f"`else if`; target the chain's terminal else")
            kw = alt.children[0]           # the `else` keyword token
            return self.candidate(
                f"else_if(L{else_line}:{condition!r})",
                TextEdit(start=kw.start_byte, end=kw.end_byte,
                         replacement=f"else if ({condition})"),
            )
        raise KeyError(
            f"add_else_if: no `else` clause starting on line {else_line}")

    def split_expr(self, *, at_line: int, expr_text: str,
                   into_var: str, type_: str = "int") -> "Forge":
        """Extract a sub-expression on ``at_line`` into a fresh local
        declared just before that line."""
        line_start, line_end = self._line_span(at_line)
        line_text = self.text[line_start:line_end]
        pos = line_text.find(expr_text)
        if pos < 0:
            raise LookupError(
                f"split_expr: {expr_text!r} not found on line {at_line}")
        decl_line = f"    {type_} {into_var} = {expr_text};\n"
        return self.candidate(
            f"split_expr(L{at_line}:{expr_text!r}->{into_var})",
            TextEdit(start=line_start, end=line_start,
                     replacement=decl_line, note="insert extract"),
            TextEdit(start=line_start + pos,
                     end=line_start + pos + len(expr_text),
                     replacement=into_var, note="rewrite use"),
        )

    def replace_expr(self, old_text: str, new_text: str,
                     *, at_line: int | None = None,
                     nth: int = 0) -> "Forge":
        """Replace the ``nth`` literal occurrence of ``old_text``
        inside the function body (optionally restricted to one line)."""
        fs = self.fs
        search_start, search_end = fs.body.start_byte, fs.body.end_byte
        if at_line is not None:
            ls, le = self._line_span(at_line)
            search_start, search_end = max(search_start, ls), min(
                search_end, le)
        cursor = search_start
        for _ in range(nth + 1):
            pos = self.text.find(old_text, cursor, search_end)
            if pos < 0:
                raise LookupError(
                    f"replace_expr: {old_text!r} not found "
                    f"({nth + 1}-th occurrence)")
            cursor = pos + len(old_text)
        start = cursor - len(old_text)
        return self.candidate(
            f"replace({old_text!r}->{new_text!r}@{at_line or '?'})",
            TextEdit(start=start, end=start + len(old_text),
                     replacement=new_text),
        )


    def preset(self, name: str, **opts) -> "Forge":
        """Bulk-import candidates from a named lever preset.

        Presets are the bulk hypothesis generators.  They walk the AST,
        identify every legal site for a transformation, and emit one
        candidate per site.  A typical preset adds 10-200 candidates --
        feed several presets into ``run("pairs")`` or
        ``run(depth=3)`` to get the thousands-of-variants cartesian
        explosion the workflow is built for.

        Built-in presets:

            tie_group       -- firstassign + decl_order + stmt_swap
                               (the verified regalloc-tie safe group)
            commute_all     -- one candidate per commutative binop site
            relorder_all    -- one candidate per <,<=,>,>= site (swap+flip)
            type_sweep      -- every native-integer local x every OTHER
                               native integer type (char/short/int/long,
                               signed+unsigned; width/sign-agnostic)
                               (restrict=[name,...] to narrow the local set)
            cast_sweep      -- explicit ``(T)`` casts on variables,
                               computation results and comparison
                               operands/results, every native integer
                               type (types=[...] / max_sites=N to narrow)
            decl_swap_all   -- every pair of locals declared in the same
                               run (n*(n-1)/2 candidates per run)
            stmt_swap_adjacent -- every adjacent independent statement
                                  pair
            shift1          -- ``x<<1`` ↔ ``x+x`` toggles
            bytemask        -- ``E & 0xff`` ↔ ``(unsigned char)E`` toggles

        Options vary per preset; the most common is ``restrict=[name,
        ...]`` to limit to a subset of locals / operations.
        """
        from c2.forge.presets import PRESETS
        if name not in PRESETS:
            raise KeyError(
                f"unknown preset {name!r}; available: {sorted(PRESETS)}")
        added = PRESETS[name](self, **opts)
        return self


    def candidates(self) -> list[Candidate]:
        """The current candidate pool (read-only view)."""
        return list(self._candidates)

    def clear_candidates(self) -> "Forge":
        """Drop every registered candidate -- useful in a REPL when
        iterating on the hypothesis set without rebuilding the whole
        Forge object."""
        self._candidates = []
        return self


    def preview(self, target, *, context: int = 2) -> str:
        """Render a textual unified-diff preview of what ``target`` would
        do to the source -- WITHOUT compiling.  Useful for sanity-
        checking a candidate before adding it to a big run.

        ``target`` is either a single Candidate or an EditPlan.  The
        diff is line-oriented with ``context`` lines around each hunk.
        """
        import difflib
        if isinstance(target, Candidate):
            plan = EditPlan(candidates=(target,))
        elif isinstance(target, EditPlan):
            plan = target
        else:
            raise TypeError(
                f"preview() needs a Candidate or EditPlan, got "
                f"{type(target).__name__}")
        base = self.text
        new = plan.apply(base)
        diff = difflib.unified_diff(
            base.splitlines(keepends=True),
            new.splitlines(keepends=True),
            fromfile=f"{self.file}  (baseline)",
            tofile=f"{self.file}  (after: {plan.name})",
            n=context,
        )
        return "".join(diff)

    def dry_run(self, mode: str | int = "each",
                max_variants: int = 100_000) -> dict:
        """Enumerate plans WITHOUT compiling, return counts + a sample.

        Use to sanity-check a search-space size before kicking off a
        long run.  The cartesian product of even modest candidate
        sets blows up fast; ``dry_run`` shows you the count and the
        first few plan names so you can adjust mode or cap before
        spending CPU.
        """
        depth = self._resolve_depth(mode)
        plans = list(self._enumerate_plans(depth, max_variants))
        n = len(plans)
        n_overlap = (sum(1 for _ in itertools.combinations(
            self._candidates, depth)) - n if depth <= 6 else None)
        # cap=hit?
        hit_cap = n == max_variants
        sample = [p.name for p in plans[:8]]
        if n > 8:
            sample.append(f"...{n - 8} more")
        return {
            "candidates": len(self._candidates),
            "depth": depth,
            "plans_enumerable": n,
            "overlapping_combos_dropped": n_overlap,
            "hit_cap": hit_cap,
            "sample": sample,
        }


    def session(self, *, jobs: int = 4):
        """Open a warm worker pool that survives across multiple
        ``run()`` calls.  Use as a context manager::

            with forge.session(jobs=6) as s:
                s.run("each")            # ~5 s
                s.add_candidate(...)
                s.run("pairs")           # ~15 s without re-warming
                summary.show()

        Outside the ``with`` block (or after ``close()``), each
        ``run()`` re-spins workers itself.  Pool is shared across the
        whole forge instance until closed.
        """
        return _ForgeSession(self, jobs=jobs)

    def close(self) -> None:
        """Tear down any persistent warm pool.  Safe to call multiple
        times; pairs with ``session()``.  Called automatically when
        the Forge object is garbage collected."""
        if self._pool is not None:
            self._pool.shutdown()
            self._pool = None

    def __del__(self):
        try:
            self.close()
        except Exception:                       # noqa: BLE001
            pass


    def repl_help(self) -> None:
        """Point at the `forge` skill -- the canonical, always-up-to-date
        cheatsheet + user guide.  The Forge class never embeds API
        documentation inline (it would drift); the skill is the source
        of truth.
        """
        print(
            f"forge cheatsheet + guide:  read .pi/skills/forge/SKILL.md\n"
            f"  (or: from c2.forge import skill_path; "
            f"print(open(skill_path()).read())  )\n"
            f"\n"
            f"current state: Forge({self.function!r}, file={self.file!r}), "
            f"{len(self._candidates)} candidate(s) queued"
        )

    def _order_candidates_by_islands(self, baseline) -> None:
        """Stable-sort ``self._candidates`` so island-relevant ones come
        first (see ``_run_pipeline``).  No-op when the baseline carries
        no ledger (islands unavailable) or no islands."""
        led = getattr(baseline, "ledger", None) or {}
        islands = led.get("islands") or []
        if not islands:
            return
        text = self.text
        line_starts = [0]
        for i, ch in enumerate(text):
            if ch == "\n":
                line_starts.append(i + 1)

        import bisect as _b
        import re as _re

        def _line_of(off: int) -> int:
            return _b.bisect_right(line_starts, off)

        island_lines: set[int] = set()
        for isl in islands:
            island_lines.update(isl.get("rc_lines") or [])
        ident_re = _re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
        island_idents: set[str] = set()
        src_lines = text.splitlines()
        for lno in island_lines:
            if 1 <= lno <= len(src_lines):
                island_idents.update(ident_re.findall(src_lines[lno - 1]))
        # drop keywords/noise that would match everything
        island_idents -= {
            "if", "else", "while", "for", "return", "int", "char",
            "unsigned", "signed", "short", "long", "void", "struct",
            "break", "continue", "goto", "do", "switch", "case",
        }

        def _prio(cand) -> int:
            for e in cand.edits:
                lo = _line_of(e.start)
                hi = _line_of(max(e.start, e.end - 1))
                if any(ln in island_lines for ln in range(lo, hi + 1)):
                    return 0
            if island_idents:
                for e in cand.edits:
                    snippet = text[e.start:e.end] + " " + e.replacement
                    if island_idents & set(ident_re.findall(snippet)):
                        return 0
            return 1

        self._candidates.sort(key=_prio)   # stable: preserves preset order

    def _unique_candidates(self) -> list:
        """``self._candidates`` deduplicated by APPLIED TEXT -- two
        candidates that splice to byte-identical source (e.g.
        ``swap_decls(a,b)`` and a 2-element ``decl_perm`` of the same
        run) are the SAME variant, but carry different edit spans so the
        span-fingerprint dedup misses them.  ~9% of the corpus's singles
        are such duplicates; dropping them (provably safe -- identical
        text) also removes the duplicate PAIRS they would seed.  First
        occurrence wins, so the island-first ordering is preserved.
        """
        base = self.text
        seen: set = set()
        out = []
        for c in self._candidates:
            try:
                key = EditPlan(candidates=(c,)).apply(base)
            except Exception:                       # noqa: BLE001
                key = ("\0raw", c.name)
            if key in seen:
                continue
            seen.add(key)
            out.append(c)
        return out

    def _enumerate_plans(self, depth: int,
                         max_variants: int | None) -> Iterator[EditPlan]:
        """Yield every EditPlan of size 1..depth whose candidates don't
        overlap, deduplicated by fingerprint.  Lazy generator so a
        million-variant product never balloons RAM.
        """
        seen: set[str] = set()
        emitted = 0
        candidates = self._unique_candidates()
        n = len(candidates)
        for k in range(1, depth + 1):
            for combo in itertools.combinations(candidates, k):
                if not plan_ok(combo):
                    continue
                plan = EditPlan(candidates=tuple(combo))
                if plan.fingerprint in seen:
                    continue
                seen.add(plan.fingerprint)
                yield plan
                emitted += 1
                if max_variants is not None and emitted >= max_variants:
                    return

    def ranked_pair_plans(self, rank_by_name: dict,
                          cap: int) -> Iterator[EditPlan]:
        """Best-first PAIR enumeration seeded by singles results.

        ``rank_by_name`` maps candidate name -> its singles rank key
        (lower = better, e.g. ``DecisionMatrix.rank_key`` vs the
        baseline).  Candidates absent from the map (failed compiles,
        never scored) are EXCLUDED -- a broken single stays broken in
        a pair.  Pairs are yielded in ``(rank_i + rank_j, rank_i)``
        order, so under a cap the prefix is the most promising slice
        of the pair space instead of ``itertools.combinations``'s
        lexicographic prefix (which starves every late candidate).
        The candidate list is pre-sliced to the top M with
        C(M,2) >= 2.5*cap so the sort stays trivial.
        """
        import math
        ranked = [c for c in self._unique_candidates()
                  if c.name in rank_by_name]
        ranked.sort(key=lambda c: rank_by_name[c.name])
        # Dense diagonal only within the top-M (C(M,2) ~ 2.5*cap keeps
        # the sort trivial); the coverage sweep below still reaches
        # EVERY ranked candidate.
        m = len(ranked)
        if cap and cap > 0:
            want = 2.5 * cap                # margin for plan_ok rejects
            m = min(m, max(2, int((1 + math.sqrt(1 + 8 * want)) / 2) + 1))
        order = sorted(((i, j) for i in range(m) for j in range(i + 1, m)),
                       key=lambda ij: (ij[0] + ij[1], ij[0]))
        seen: set[str] = set()
        seen_names: set[str] = set()
        emitted = 0

        def _emit(a, b):
            nonlocal emitted
            combo = (a, b)
            if not plan_ok(combo):
                return None
            plan = EditPlan(candidates=combo)
            if plan.fingerprint in seen:
                return None
            seen.add(plan.fingerprint)
            seen_names.update((a.name, b.name))
            emitted += 1
            return plan

        # phase 1: best-first diagonal, up to ~85% of the cap
        diag_budget = int(cap * 0.85) if cap and cap > 0 else None
        k = 0
        for k, (i, j) in enumerate(order):
            if diag_budget is not None and emitted >= diag_budget:
                break
            p = _emit(ranked[i], ranked[j])
            if p is not None:
                yield p
        # phase 2: coverage sweep -- every ok single not yet paired
        # gets a few pairings with the top-ranked compatibles, so no
        # lever is silently starved by the cap
        top = ranked[:16]
        for c in ranked:
            if c.name in seen_names:
                continue
            paired = 0
            for t in top:
                if t is c:
                    continue
                p = _emit(c, t)
                if p is not None:
                    yield p
                    paired += 1
                    if paired >= 3:
                        break
        # phase 3: resume the diagonal with whatever budget remains
        for i, j in order[k:]:
            p = _emit(ranked[i], ranked[j])
            if p is not None:
                yield p

    def ranked_triple_plans(self, rank_by_name: dict,
                            seed_pairs: list[tuple[str, str]],
                            cap: int) -> Iterator[EditPlan]:
        """Best-first TRIPLE enumeration seeded by the pair results.

        Blind C(n,3) is hopeless (574 candidates -> 31M triples); the
        escalation only makes sense SEEDED: ``seed_pairs`` are the ok
        pairs of the previous pass ordered best-first (candidate name
        tuples), each extended with ranked ok singles
        (``rank_by_name``, as in :meth:`ranked_pair_plans`).  Pairs
        and singles are walked anti-diagonally (pair_rank +
        single_rank ascending), so a capped pass explores 'best pair
        + best third lever' combinations first.  Emission stops just
        past ``cap`` -- the caller's queue is the hard cap.
        """
        uniq = self._unique_candidates()
        by_name = {c.name: c for c in uniq}
        singles = [c for c in uniq if c.name in rank_by_name]
        singles.sort(key=lambda c: rank_by_name[c.name])
        pairs: list[tuple[Candidate, Candidate]] = []
        for a, b in seed_pairs:
            ca, cb = by_name.get(a), by_name.get(b)
            if ca is not None and cb is not None:
                pairs.append((ca, cb))
            if cap and len(pairs) >= max(64, cap):
                break
        np_, ns = len(pairs), len(singles)
        if not np_ or not ns:
            return
        budget = int(cap * 1.05) if cap and cap > 0 else None
        seen: set[str] = set()
        emitted = 0
        for tot in range(np_ + ns - 1):
            if budget is not None and emitted >= budget:
                return
            for i in range(min(tot, np_ - 1), -1, -1):
                j = tot - i
                if j >= ns:
                    continue
                a, b = pairs[i]
                c = singles[j]
                if c.name == a.name or c.name == b.name:
                    continue
                combo = (a, b, c)
                if not plan_ok(combo):
                    continue
                plan = EditPlan(candidates=combo)
                if plan.fingerprint in seen:
                    continue
                seen.add(plan.fingerprint)
                emitted += 1
                yield plan
                if budget is not None and emitted >= budget:
                    return

    def add_candidate(self, candidate: Candidate) -> "Forge":
        """Append a pre-built Candidate (escape hatch beyond the DSL)."""
        self._candidates.append(candidate)
        return self

    def run(self, mode: str | int = "each", *,
            jobs: int = 4, max_variants: int = 5000,
            stop_at_exact: bool = True,
            progress: bool = True, store=None,
            plans: Iterator[EditPlan] | None = None) -> Summary:
        """Compile + score every plan up to the chosen depth.

        Args:
            mode: ``"each"`` (depth 1, singletons), ``"pairs"`` (depth 2),
                ``"triples"`` (depth 3), ``"all"`` (depth = number of
                candidates), or an explicit integer depth.  The cartesian
                product can blow up; ``max_variants`` is the hard cap.
            jobs: parallel workers.
            max_variants: hard cap on plans tried.  For ``"each"`` the
                cap is floored at the candidate count -- SINGLES ARE
                NEVER TRUNCATED (full lever coverage is the point).
            stop_at_exact: stop the moment any plan scores ``bytes == 0``
                (the DONE oracle).
            progress: print a one-line tick per second to stderr.
            plans: explicit plan iterator overriding the depth
                enumeration (e.g. :meth:`ranked_pair_plans`); ``mode``
                is ignored for enumeration when given.
        """
        depth = self._resolve_depth(mode)
        if not self._candidates:
            # Pure baseline scoring -- still useful as a sanity check.
            return self._baseline_only()
        if depth == 1 and plans is None:
            max_variants = max(max_variants, len(self._candidates))
        return self._run_pipeline(
            depth=depth, jobs=jobs, max_variants=max_variants,
            stop_at_exact=stop_at_exact, progress=progress, store=store,
            plan_iter=plans,
        )

    def _resolve_depth(self, mode: str | int) -> int:
        if isinstance(mode, int):
            return max(1, mode)
        mode = mode.lower()
        if mode in ("each", "singletons", "1"):
            return 1
        if mode in ("pairs", "2"):
            return 2
        if mode in ("triples", "3"):
            return 3
        if mode in ("quads", "4"):
            return 4
        if mode in ("all", "max"):
            return max(1, len(self._candidates))
        raise ValueError(f"unknown run mode {mode!r}")


    def _baseline_only(self) -> Summary:
        from c2.forge.pool import ForgePool
        from c2.forge.variant import make_variant
        ps = ps_ref.load(self.function)
        with ForgePool(workers=1, file=self.file, function=self.function,
                       cflags=self.cflags, image=self.image,
                       source_root=self.source_root) as pool:
            v = make_variant(vid="baseline", lever_path=("baseline",),
                             body_text="", file_text=self.text)
            sc = pool.compile_and_score(v, ps)
        return Summary(function=self.function, file=self.file,
                       baseline=sc, plans=[], elapsed_s=0.0,
                       candidates_total=0)

    def _run_pipeline(self, *, depth: int, jobs: int, max_variants: int,
                      stop_at_exact: bool, progress: bool,
                      store=None, plan_iter=None) -> Summary:
        import sys
        from c2.forge.pool import ForgePool
        from c2.forge.variant import make_variant

        ps = ps_ref.load(self.function)
        base_text = self.text
        t0 = time.perf_counter()

        # Use the persistent pool (session()) if open; otherwise spin a
        # fresh pool that lives only for this run.  The contextmanager
        # form below handles teardown either way.
        own_pool = self._pool is None
        pool_ctx = (
            ForgePool(workers=jobs, file=self.file, function=self.function,
                      cflags=self.cflags, image=self.image,
                      source_root=self.source_root)
            if own_pool
            else _NullCtx(self._pool)
        )

        with pool_ctx as pool:
            base_v = make_variant(vid="baseline", lever_path=("baseline",),
                                  body_text="", file_text=base_text)
            baseline = pool.compile_and_score(base_v, ps, want_ledger=True)
            if store is not None and "baseline" not in store.meta:
                store.set_baseline(baseline)
            # Island-first plan ORDERING (never filtering): sort the
            # candidate pool so edits touching the baseline's divergence
            # islands -- by line intersection or by identifier overlap
            # with the islands' source lines -- enumerate first.  With a
            # max_variants cap this makes the capped prefix maximally
            # island-relevant; without a cap it only accelerates
            # stop-at-exact.  Accuracy-neutral by construction: every
            # plan the old order could try is still tried.
            self._order_candidates_by_islands(baseline)
            if stop_at_exact and baseline.ok and baseline.bytes == 0:
                if progress:
                    print("baseline already byte-exact; skip.", file=sys.stderr)
                return Summary(function=self.function, file=self.file,
                               baseline=baseline, plans=[],
                               candidates_total=len(self._candidates))

            # Stream plans -> variants -> pool.
            def _variant_stream():
                source = (plan_iter if plan_iter is not None
                          else self._enumerate_plans(depth, max_variants))
                for plan in source:
                    full = plan.apply(base_text)
                    yield make_variant(
                        vid=f"p{plan.fingerprint}",
                        lever_path=tuple(c.name for c in plan.candidates),
                        body_text=full,
                        file_text=full,
                    ), plan

            # The pool's run_stream takes a Variant iterator; we keep
            # the plan alongside via a side dict.
            plan_by_id: dict[str, EditPlan] = {}
            def _just_variants():
                for v, plan in _variant_stream():
                    plan_by_id[v.id] = plan
                    yield v

            from c2.forge.variant import VariantQueue
            queue = VariantQueue(_just_variants(), max_variants=max_variants)

            results: list[PlanResult] = []
            failures = 0
            tick = time.perf_counter()
            exact_found = False
            # track the best improving variant seen so far so the
            # progress line reports GAINS, not just a plan count.
            best_pr: PlanResult | None = None
            for vr in pool.run_stream(queue, ps):
                if not vr.score.ok:
                    failures += 1
                    continue
                plan = plan_by_id.get(vr.variant.id)
                if plan is None:
                    continue
                pr = PlanResult(
                    plan=plan, score=vr.score,
                    shape_delta=vr.score.shape_total - baseline.shape_total,
                    bytes_delta=vr.score.bytes - baseline.bytes,
                )
                results.append(pr)
                if store is not None:
                    store.log_result(plan, vr.score)
                # "better" = fix-order layer vector first (the honest
                # judge -- an ir drop beats any byte movement), bytes
                # as the within-layer tie-break.
                improved = (best_pr is None
                            or (pr.score.layers, pr.score.bytes)
                            < (best_pr.score.layers, best_pr.score.bytes))
                if improved:
                    best_pr = pr
                    # NEEDLE-MOVEMENT reporting: print ONLY when the new
                    # best also beats the BASELINE (a genuine gain), never
                    # on a timer -- per-second plan-count spam buries the
                    # signal in long runs (2026-06-30).
                    if (progress
                            and (pr.score.layers, pr.score.bytes)
                            < (baseline.layers, baseline.bytes)):
                        pl = pr.score.layers
                        print(f"  ▲ {queue.emitted} plans in: "
                              f"ir{pl[0]} i{pl[1]} w{pl[2]} sp{pl[3]} "
                              f"st{pl[4]} bytes={pr.score.bytes} "
                              f"(Δb={pr.bytes_delta:+d})  "
                              f"[{pr.plan.name}]  "
                              f"{time.perf_counter() - t0:.0f}s",
                              file=sys.stderr)
                now = time.perf_counter()
                if stop_at_exact and vr.score.bytes == 0:
                    if progress:
                        print(f"  \u2713 byte-exact: {plan.name}",
                              file=sys.stderr)
                    exact_found = True
                    pool.request_stop()
                    break
                if progress and (now - tick) > 120.0:
                    # sparse heartbeat (2 min) so a stalled container is
                    # distinguishable from a long quiet search; all real
                    # reporting happens on needle movement above.
                    print(f"  …{queue.emitted} plans, {failures} fail, "
                          f"{now - t0:.0f}s elapsed", file=sys.stderr)
                    tick = now
            if exact_found:
                pool.drain_inflight()

        elapsed = time.perf_counter() - t0
        return Summary(
            function=self.function, file=self.file,
            baseline=baseline, plans=results, elapsed_s=elapsed,
            duplicates=queue.duplicates,
            build_failures=failures,
            candidates_total=len(self._candidates),
        )


    def apply(self, plan: EditPlan) -> Path:
        """Write the plan's edits into the live source file (text-preserving).

        Returns the path written.  Idempotent within a session; safe to
        re-apply (the edits are TEXT-based on the current file).
        """
        base = self._file_path.read_text()
        new_text = plan.apply(base)
        self._file_path.write_text(new_text)
        # Bump mtime so the verifier's fast path doesn't return a stale
        # result on the next verify call.
        os.utime(self._file_path, None)
        return self._file_path


    def __enter__(self) -> "Forge":
        return self

    def __exit__(self, *_exc) -> None:
        # Tear down any persistent pool the user opened via session().
        self.close()


class _NullCtx:
    """Tiny context manager that yields an already-open pool and never
    tears it down.  Used internally when ``Forge._pool`` is already set
    (a session() is active) so the per-run with-block doesn't kill the
    pool we want to reuse."""

    def __init__(self, pool):
        self._pool = pool

    def __enter__(self):
        return self._pool

    def __exit__(self, *_exc):
        return False


class _ForgeSession:
    """Context manager that opens a warm worker pool on a Forge and
    leaves it open across multiple ``run()`` calls."""

    def __init__(self, forge: "Forge", *, jobs: int):
        self._forge = forge
        self._jobs = jobs
        self._opened = False

    def __enter__(self) -> "Forge":
        if self._forge._pool is not None:
            # Nested sessions are a programmer error; refuse cleanly.
            raise RuntimeError(
                "Forge already has an open session; close() it first.")
        from c2.forge.pool import ForgePool
        pool = ForgePool(
            workers=self._jobs,
            file=self._forge.file,
            function=self._forge.function,
            cflags=self._forge.cflags,
            image=self._forge.image,
            source_root=self._forge.source_root,
        )
        pool.__enter__()                         # starts workers
        self._forge._pool = pool
        self._opened = True
        return self._forge

    def __exit__(self, *exc):
        if self._opened and self._forge._pool is not None:
            try:
                self._forge._pool.__exit__(*exc)
            finally:
                self._forge._pool = None
        return False


#
# The smart alternative to a multi-hour cartesian barrage AND to the old
# single-track greedy walk: from ROUND 1 the search keeps up to ``beam``
# DISTINCT improving states (preferring branches from different lever
# families), expands each with the full battery, and records the whole
# tree -- so the alternative branches that the greedy walk used to throw
# away stay explored AND reconstructable (RunStore).  When the lex ladder
# WALL-LOCKS (no ir/islands-safe step reduces the deep residue), the beam
# may take a bounded BRIDGE step -- pay a shallow ir/islands/bytes
# regression to buy a deeper (seat/spill/width) gain -- to hop into a
# seat=0 basin from which byte-exact is a short descent.  The keep bar is
# unchanged: only a net lex win (or byte-exact) survives, so a bridge that
# leads nowhere is explored and discarded.


def climb(function: str, *, file: str, jobs: int = 8,
          max_rounds: int = 48, beam: int = 2,
          pairs_when_stuck: bool = True, pairs_cap: int = 25_000,
          keep: bool = True, presets: tuple[str, ...] = ("all",),
          preset_opts: dict | None = None,
          source_root=None, quiet: bool = False,
          policy: str = "lex+weighted", store: bool = True,
          log_children: int = 10, max_variants: int = 25_000,
          budget: float | None = None,
          bridge: bool = True, bridge_ir_budget: int | None = None,
          bridge_isl_budget: int | None = None,
          max_bridges: int = 8) -> dict:
    """Beam-search one function with the full lever battery.

    Each round: every beam state is expanded with full-battery singles
    (never truncated -- full lever coverage per state); the
    DecisionMatrix picks the accepted children; the top ``beam``
    DISTINCT states (family-diverse) survive.  When no state yields a
    lex improvement the search walks the escalation ladder on the best
    state: RANKED pairs (seeded by that state's own singles results,
    best-first, failed singles excluded), then RANKED triples (top ok
    pairs x ranked singles, anti-diagonal -- catches three
    simultaneously-needed edits invisible to singles and pairs alike),
    then a weighted plateau step (``policy="lex+weighted"``:
    bytes/lower layers may trade, the ir/islands layers may NEVER
    regress).

    **Bridges (basin-hop, ``bridge=True``).**  When the lex ladder
    stalls -- and only then -- the search may take a ``bridge`` step:
    a BOUNDED ir/islands/bytes regression that BUYS a strict
    improvement in a DEEPER residue layer (width/spill/seat).  This
    lets the beam climb OUT of a wall-locked local minimum toward a
    seat=0 launch basin from which byte-exact may be reachable (the
    ``city_test_for_road`` 6-byte seat tie: the only seat=0 states are
    register-class type flips costing ir+islands+hundreds of bytes).
    Two guarantees make the basin actually explorable:

      * **admission**: on a stalled round the best-ranked bridge is
        ALWAYS admitted (extending the beam by one when the normal
        proposals filled it) -- weighted byte-chasing steps can never
        starve the hop, and the hop never displaces them;
      * **the full ladder**: pairs/triples escalation rotates over the
        beam states not yet escalated (fingerprint-tracked) instead of
        hammering the lex-best state forever -- a basin state is
        lex-WORSE than the main lane by construction, so without the
        rotation it would only ever see singles.

    Three more rules keep the hops PRODUCTIVE (2026-07-06 postmortem:
    the first cut burned all 8 bridges on 4 repetitions of the same
    2 plans, cycling bridge->descend->walk-back while the best basin
    state never got its pairs turn):

      * **dedup**: a bridge signature ``(plan, layers, bytes)`` is
        admitted ONCE per run -- neutral-variant base states re-offer
        the same hop forever otherwise;
      * **hold-the-gain**: children of a basin lineage may not regress
        the deep layers the bridge bought (seat back to 1 = walking
        back over the bridge; the descent must repair ir/islands while
        HOLDING the bought seat) -- byte-exact bypasses the hold;
      * **ladder queue**: an un-escalated state displaced from the
        beam parks in a pending queue and stays escalation-eligible.

    ``bridge_ir_budget`` / ``bridge_isl_budget`` cap the shallow
    regression per hop.  Default (None) is ADAPTIVE to function size:
    ``max(12, ir_total//6)`` / ``max(16, ir_total//4)`` -- a
    register-class flip in a 2 kB function legitimately moves far more
    islands than in a 60-byte one.  Deep-gain candidates beyond the
    budget are WARNED about and listed in the report, never silently
    dropped; ``max_bridges`` caps the total hops so the search still
    terminates.  Bridges NEVER change the keep bar -- see below.

    Stops at byte-exact, at ``max_rounds``, when nothing (including
    bridges) is accepted, or when the wall-clock ``budget`` (seconds)
    is exhausted.  The variant caps are runaway BRAKES, not budgets --
    the search almost always ends on stall or byte-exact first;
    ``budget`` is the knob that maps to real cost.

    The judge is the same fix-order layer vector ``decomp-verify``
    prints; the FINAL state is kept only when it beats the start
    LEXICOGRAPHICALLY (or is byte-exact) -- weighted AND bridge steps
    are bridges, never the destination (a bridge that leads nowhere is
    explored, then restored).

    The whole search tree (accepted states with full source, plus the
    top ``log_children`` evaluated-but-not-taken children per state)
    lands in ``.c2-cache/forge-runs/<fn>/<ts>-climb/`` -- every branch
    diff is reconstructable offline via ``c2 forge diff``.

    Returns a report dict (keys: steps, start, final, improved,
    byte_exact, restored, run_dir, rounds).
    """
    import hashlib
    import sys

    from c2.forge import runstore as rs
    from c2.forge.matrix import DecisionMatrix
    from c2.forge.pool import ForgePool

    preset_opts = preset_opts or {}
    root = Path(source_root) if source_root else Path("decomp")
    src_path = root / "src" / file
    original_text = src_path.read_text()
    matrix = DecisionMatrix(policy=policy)
    lexm = DecisionMatrix(policy="lex")

    def _say(msg: str) -> None:
        if not quiet:
            print(msg, file=sys.stderr)

    def _fp(text: str) -> str:
        return hashlib.sha1(text.encode()).hexdigest()[:12]

    def _lay(score) -> str:
        pl = score.layers
        return (f"ir{pl[0]} i{pl[1]} w{pl[2]} sp{pl[3]} st{pl[4]} "
                f"bytes={score.bytes}")

    run_store = rs.RunStore.create(
        function, file, "climb", original_text,
        config={"jobs": jobs, "beam": beam, "max_rounds": max_rounds,
                "policy": policy, "presets": list(presets),
                "preset_opts": dict(preset_opts),
                "pairs_cap": pairs_cap, "max_variants": max_variants,
                "bridge": bridge, "bridge_ir_budget": bridge_ir_budget,
                "bridge_isl_budget": bridge_isl_budget,
                "max_bridges": max_bridges},
    ) if store else None

    @dataclass
    class _Node:
        id: str
        text: str
        score: Any = None          # Score once evaluated
        parent: str | None = None
        basin: bool = False        # descendant of a bridge (basin-hop)
        # deep-layer (width, spill, seat) maxima a basin lineage must
        # HOLD -- set to the bridge child's deep layers at admission,
        # inherited by descendants.  A child regressing past these has
        # walked back over the bridge and is rejected (byte-exact
        # bypasses).
        hold: tuple | None = None

    node_seq = itertools.count(1)

    n_evaluated = 0
    t_climb0 = time.perf_counter()

    def _eval(text: str, mode: str = "each",
              cap: int = max_variants) -> Summary:
        """Materialise a state on disk, derive the battery, run it on
        the SHARED warm pool."""
        nonlocal n_evaluated
        src_path.write_text(text)
        os.utime(src_path, None)
        f = (Forge(function, file=file, source_root=source_root)
             if source_root else Forge(function, file=file))
        for p in presets:
            f.preset(p, **preset_opts)
        f._pool = pool
        try:
            s = f.run(mode, jobs=jobs, progress=False,
                      max_variants=cap, stop_at_exact=True)
            n_evaluated += len(s.plans) + 1     # +1 = baseline compile
            return s
        finally:
            f._pool = None          # never tear down the shared pool

    def _over_budget() -> bool:
        return (budget is not None and budget > 0
                and time.perf_counter() - t_climb0 > budget)

    def _eval_ranked_pairs(text: str, prior: Summary,
                           cap: int) -> tuple[Summary, int]:
        """Pairs escalation seeded by the state's OWN singles results:
        pairs of ok-singles in best-first (rank_i+rank_j) order.  No
        single is re-run; failed singles are excluded.  Returns
        (summary, n_seed_singles)."""
        nonlocal n_evaluated
        src_path.write_text(text)
        os.utime(src_path, None)
        f = (Forge(function, file=file, source_root=source_root)
             if source_root else Forge(function, file=file))
        for p in presets:
            f.preset(p, **preset_opts)
        rank = {}
        for pr in prior.plans:
            if len(pr.plan.candidates) == 1 and pr.score.ok:
                rank[pr.plan.candidates[0].name] = \
                    lexm.rank_key(pr.score, prior.baseline)
        f._pool = pool
        try:
            s = f.run("pairs", jobs=jobs, progress=False,
                      max_variants=cap, stop_at_exact=True,
                      plans=f.ranked_pair_plans(rank, cap))
            n_evaluated += len(s.plans) + 1
            return s, len(rank)
        finally:
            f._pool = None

    def _eval_ranked_triples(text: str, prior: Summary,
                             pairs_summary: Summary,
                             cap: int) -> tuple[Summary, int]:
        """Triples escalation: top ok pairs of the pairs pass, each
        extended with ranked ok singles, anti-diagonal best-first."""
        nonlocal n_evaluated
        src_path.write_text(text)
        os.utime(src_path, None)
        f = (Forge(function, file=file, source_root=source_root)
             if source_root else Forge(function, file=file))
        for p in presets:
            f.preset(p, **preset_opts)
        rank = {}
        for pr in prior.plans:
            if len(pr.plan.candidates) == 1 and pr.score.ok:
                rank[pr.plan.candidates[0].name] = \
                    lexm.rank_key(pr.score, prior.baseline)
        ok_pairs = sorted(
            (pr for pr in pairs_summary.plans
             if pr.score.ok and len(pr.plan.candidates) == 2),
            key=lambda pr: lexm.rank_key(pr.score,
                                         pairs_summary.baseline))
        seed = [(pr.plan.candidates[0].name, pr.plan.candidates[1].name)
                for pr in ok_pairs]
        f._pool = pool
        try:
            s = f.run("triples", jobs=jobs, progress=False,
                      max_variants=cap, stop_at_exact=True,
                      plans=f.ranked_triple_plans(rank, seed, cap))
            n_evaluated += len(s.plans) + 1
            return s, len(seed)
        finally:
            f._pool = None

    bridges_used = 0
    # Deep-gain (seat/spill/width) paths a too-tight ir/isl budget HID,
    # deduped by signature -- surfaced live AND in the report so no real
    # path is ever silently invisible (big functions can blow far past
    # the default isle budget on a single register-class flip).
    overbudget_paths: dict = {}
    warned_ob: set = set()

    def _gather_bridges(summ: Summary, state: "_Node",
                        overbudget: list) -> None:
        """Scan an already-scored Summary for BRIDGE candidates vs its
        own baseline (the state being expanded).  In-budget bridges (a
        bounded shallow regression that buys a strict deep-layer gain,
        matrix.bridge_accepts) go into the persistent RESERVOIR (one
        entry per untaken signature -- available even after the parent
        leaves the beam); genuine deep-gain bridges rejected ONLY by
        the ir/isl budget go to ``overbudget`` so the climb can warn
        about them.  Cheap: no compile, just re-judging plans forge
        already scored.  (``max_bridges`` is enforced at ADMISSION
        time, not here, so the pool stays visible for the exhaustion
        warning.)"""
        if not bridge:
            return
        base = summ.baseline
        for pr in summ.plans:
            if not pr.score.ok or pr.score.bytes == 0:
                continue
            bv = matrix.bridge_accepts(
                pr.score, base, ir_budget=bridge_ir_budget,
                isl_budget=bridge_isl_budget)
            if bv:
                sig = (pr.plan.name, pr.score.layers, pr.score.bytes)
                if sig not in bridge_taken_sigs \
                        and sig not in bridge_reservoir:
                    bridge_reservoir[sig] = (bv, pr, state, "bridge")
            elif bv.reason == "bridge over-budget":
                overbudget.append((pr, state, base))

    steps: list[dict] = []
    start_score = None
    byte_exact = False
    final_node: _Node | None = None
    kept = False
    improved = False
    rounds_done = 0

    pool = ForgePool(workers=jobs, file=file, function=function,
                     cflags=None, image=None, source_root=root)
    pool.__enter__()
    try:
        root_node = _Node(id="n0", text=original_text)
        beam_states: list[_Node] = [root_node]
        visited: set[str] = {_fp(original_text)}
        all_nodes: list[_Node] = [root_node]
        state_summaries: dict[str, Summary] = {}
        # states (by text fingerprint) whose pairs/triples ladder has
        # been climbed -- the escalation ROTATES over un-escalated beam
        # states so basin branches get the full ladder too.
        escalated: set[str] = set()
        bridge_maxed_said = False
        # one admission per (plan, layers, bytes) signature per run:
        # byte-neutral variant base states re-offer the SAME hop with a
        # fresh text fingerprint forever -- the 2026-07-06 cycle.
        bridge_taken_sigs: set[tuple] = set()
        # persistent basin-hop RESERVOIR (sig -> candidate): bridges
        # found in ANY explored state stay available, so when an
        # admitted basin dead-ends the search can fall back to the
        # next-ranked hop even though its parent left the beam.
        bridge_reservoir: dict[tuple, tuple] = {}
        # un-escalated states displaced from the beam: still
        # escalation-eligible (never silently lose the ladder turn).
        ladder_pending: dict[str, Any] = {}
        # singles summaries by TEXT fingerprint: a state RETAINED in
        # the beam (ladder pending) is re-expanded for free.
        summary_cache: dict[str, Summary] = {}

        def _novel(props: list[tuple]) -> list[tuple]:
            """Proposals whose resulting text is NOT an already-visited
            state.  Stale (all-revisit) lex proposals must not mask a
            stall -- they blocked the escalation/bridge tiers while the
            pick stage discarded every one of them."""
            return [p for p in props
                    if _fp(p[1].plan.apply(p[2].text)) not in visited]

        for rnd in range(1, max_rounds + 1):
            rounds_done = rnd
            if _over_budget():
                _say(f"  round {rnd}: wall-clock budget "
                     f"({budget:.0f}s) exhausted -- stop")
                break
            # (verdict, PlanResult, parent node, mode) accepted proposals
            proposals: list[tuple] = []
            # deep-gain bridges over the ir/isl budget (near-misses).
            bridge_overbudget: list = []
            exact_hit: tuple | None = None

            for st in beam_states:
                fp_st = _fp(st.text)
                summary = summary_cache.get(fp_st)
                if summary is None:
                    summary = _eval(st.text)
                    summary_cache[fp_st] = summary
                state_summaries[st.id] = summary
                if st.score is None:
                    st.score = summary.baseline
                    if run_store and st.id == "n0":
                        run_store.set_baseline(summary.baseline)
                        run_store.log_node(
                            "n0", parent=None, round_=0,
                            score=summary.baseline, accepted=True,
                            reason="baseline")
                if start_score is None:
                    start_score = summary.baseline
                    # adaptive bridge budgets: scale the tolerated
                    # shallow damage with the function's own size (a
                    # register-class flip in a big function moves far
                    # more islands than in a 60-byte one).
                    ir_tot = int(start_score.shape.get("ir_total", 0)
                                 or 0)
                    if bridge_ir_budget is None:
                        bridge_ir_budget = max(12, ir_tot // 6)
                    if bridge_isl_budget is None:
                        bridge_isl_budget = max(16, ir_tot // 4)
                    _say(f"climb {function}: start "
                         f"{_lay(summary.baseline)}  [beam={beam}, "
                         f"policy={policy}, bridge-ir<={bridge_ir_budget}"
                         f", bridge-isl<={bridge_isl_budget}]")
                if summary.baseline.bytes == 0:
                    byte_exact, final_node = True, st
                    break
                ranked = sorted(
                    (p for p in summary.plans if p.score.ok),
                    key=lambda p: lexm.rank_key(p.score, summary.baseline))
                if run_store:
                    for pr in ranked[:log_children]:
                        run_store.log_node(
                            f"c{next(node_seq)}", parent=st.id,
                            round_=rnd, plan=pr.plan, score=pr.score,
                            accepted=False, reason="child")
                for pr in ranked:
                    has_type = any(c.name.startswith("type(")
                                   for c in pr.plan.candidates)
                    v = matrix.accepts(pr.score, summary.baseline,
                                       has_type_edit=has_type)
                    if not v:
                        continue
                    if pr.score.bytes == 0:
                        exact_hit = (v, pr, st, "singles")
                        break
                    if st.hold is not None and any(
                            pr.score.layers[2 + i] > st.hold[i]
                            for i in range(3)):
                        continue        # bridge-gain lost (walked back)
                    proposals.append((v, pr, st, "singles"))
                _gather_bridges(summary, st, bridge_overbudget)
                if exact_hit:
                    break
            if byte_exact or exact_hit:
                if exact_hit:
                    v, pr, st, mode = exact_hit
                    text = pr.plan.apply(st.text)
                    node = _Node(id=f"n{next(node_seq)}", text=text,
                                 score=pr.score, parent=st.id)
                    all_nodes.append(node)
                    if run_store:
                        run_store.log_node(
                            node.id, parent=st.id, round_=rnd,
                            plan=pr.plan, score=pr.score, accepted=True,
                            reason="byte-exact")
                    steps.append({
                        "round": rnd, "mode": mode, "node": node.id,
                        "parent": st.id, "plan": pr.plan.name,
                        "reason": "byte-exact",
                        "layers": list(pr.score.layers),
                        "bytes": pr.score.bytes})
                    final_node = node
                    _say(f"  round {rnd}: ✓ BYTE-EXACT via "
                         f"{pr.plan.name}")
                byte_exact = True
                break

            # escalation 1: capped pairs on the best UN-ESCALATED
            # state, BASIN states first.  A basin (bridge) state is
            # lex-WORSE than the main lane by construction AND the beam
            # is replaced by children every round -- so without the
            # basin-first priority it would die after one singles pass,
            # never seeing the pairs/triples tiers a basin descent
            # needs (the whole point of paying the bridge toll).  Main-
            # lane weighted children are near-clones of their already-
            # escalated parents; they can wait.
            lex_props = [p for p in _novel(proposals)
                         if p[0].reason == "lex"]
            beam_ids = {s.id for s in beam_states}
            esc_pool = list(beam_states) + [
                s for s in ladder_pending.values()
                if s.id not in beam_ids]
            todo_esc = ([s for s in esc_pool
                         if _fp(s.text) not in escalated]
                        if not lex_props and pairs_when_stuck else [])
            if todo_esc:
                best_state = min(
                    todo_esc,
                    key=lambda s: (not s.basin, s.score.layers,
                                   s.score.bytes))
                prior = state_summaries.get(best_state.id)
                escalated.add(_fp(best_state.text))
                ladder_pending.pop(_fp(best_state.text), None)
                if prior is not None:
                    summary, n_seed = _eval_ranked_pairs(
                        best_state.text, prior, cap=pairs_cap)
                    _say(f"  round {rnd}: singles stalled -- ranked "
                         f"pairs on {best_state.id} ({n_seed} ok "
                         f"singles seed the pair space, best-first, "
                         f"cap {pairs_cap})")
                else:                       # unreachable in practice
                    _say(f"  round {rnd}: singles stalled -- pairs "
                         f"escalation on {best_state.id} "
                         f"(cap {pairs_cap})")
                    summary = _eval(best_state.text, mode="pairs",
                                    cap=pairs_cap)

                def _collect(summ, mode_label):
                    hit_exact = False
                    for pr in summ.plans:
                        if not pr.score.ok:
                            continue
                        has_type = any(c.name.startswith("type(")
                                       for c in pr.plan.candidates)
                        v = matrix.accepts(pr.score, summ.baseline,
                                           has_type_edit=has_type)
                        if v:
                            if pr.score.bytes == 0:
                                proposals.clear()
                                proposals.append(
                                    (v, pr, best_state, mode_label))
                                hit_exact = True
                                break
                            if best_state.hold is not None and any(
                                    pr.score.layers[2 + i]
                                    > best_state.hold[i]
                                    for i in range(3)):
                                continue    # bridge-gain lost
                            proposals.append(
                                (v, pr, best_state, mode_label))
                    return hit_exact

                n_before_pairs = len(proposals)
                pairs_exact = _collect(summary, "pairs")
                _gather_bridges(summary, best_state, bridge_overbudget)

                # escalation 2: ranked triples -- only when the pairs
                # pass itself added nothing (three simultaneously-
                # needed edits are invisible to singles + pairs alike)
                if (len(proposals) == n_before_pairs and not pairs_exact
                        and prior is not None and not _over_budget()):
                    summary3, n_pair_seed = _eval_ranked_triples(
                        best_state.text, prior, summary, cap=pairs_cap)
                    _say(f"  round {rnd}: pairs stalled -- ranked "
                         f"triples on {best_state.id} ({n_pair_seed} "
                         f"ok pairs x ranked singles, best-first, "
                         f"cap {pairs_cap})")
                    _collect(summary3, "triples")
                    _gather_bridges(summary3, best_state,
                                    bridge_overbudget)

            # Bridges are a LAST resort: offered only while the lex
            # ladder is genuinely stalled (a lex pair/triple still
            # counts as progress).  When stalled, the best bridge is
            # GUARANTEED admission (extending the beam if the weighted
            # byte-chasers filled it) -- see the pick stage below.
            stalled_lex = not any(p[0].reason == "lex"
                                  for p in _novel(proposals))
            have_bridge = (bridge and bridges_used < max_bridges
                           and stalled_lex and bool(bridge_reservoir))
            if (bridge and stalled_lex and bridge_reservoir
                    and bridges_used >= max_bridges
                    and not bridge_maxed_said):
                _say(f"  round {rnd}: in-budget bridge candidate(s) "
                     f"remain but --max-bridges={max_bridges} is "
                     f"exhausted -- rerun with a higher cap to explore")
                bridge_maxed_said = True

            # Record + (when stalled) WARN about deep-gain paths the
            # ir/isl budget pruned, so the user can rerun with a wider
            # --bridge-ir/--bridge-isl instead of never knowing they
            # existed.
            if bridge and bridge_overbudget:
                round_recs: dict = {}
                for pr, state, base in bridge_overbudget:
                    sl = pr.score.layers
                    sig = (pr.plan.name, sl, pr.score.bytes)
                    round_recs[sig] = {
                        "plan": pr.plan.name, "from": state.id,
                        "round": rnd, "layers": list(sl),
                        "bytes": pr.score.bytes,
                        "need_ir": sl[0] - base.layers[0],
                        "need_isl": sl[1] - base.layers[1]}
                overbudget_paths.update(round_recs)
                if stalled_lex:
                    new = [r for s, r in round_recs.items()
                           if s not in warned_ob]
                    new.sort(key=lambda r: (r["layers"][4], r["layers"][3],
                                            r["layers"][2], r["layers"][1],
                                            r["layers"][0], r["bytes"]))
                    if new:
                        _say(f"  ⚠ round {rnd}: {len(new)} deep-gain "
                             f"(seat/spill/width) path(s) beyond the "
                             f"bridge budget (ir<={bridge_ir_budget}, "
                             f"isl<={bridge_isl_budget}) -- raise the "
                             f"budget to explore:")
                        for r in new[:5]:
                            pl = r["layers"]
                            _say(f"      {r['plan']}  ->  ir{pl[0]} "
                                 f"i{pl[1]} w{pl[2]} sp{pl[3]} st{pl[4]} "
                                 f"b{r['bytes']} [from {r['from']}]  "
                                 f"needs --bridge-ir>={r['need_ir']} "
                                 f"--bridge-isl>={r['need_isl']}")
                        if len(new) > 5:
                            _say(f"      (+{len(new) - 5} more -- see the "
                                 f"run report's bridge_overbudget)")
                    warned_ob.update(round_recs.keys())

            # rank: lex steps first, then weighted; within each by the
            # absolute matrix rank vs the run start.
            proposals.sort(key=lambda t: (
                t[0].reason != "lex",
                matrix.rank_key(t[1].score, start_score),
            ))
            picked: list[tuple] = []
            seen_tx: set[str] = set()
            seen_fam: set[str] = set()
            for pass_fam in (True, False):      # family-diverse first
                for v, pr, st, mode in proposals:
                    if len(picked) >= beam:
                        break
                    text = pr.plan.apply(st.text)
                    fp = _fp(text)
                    if fp in visited or fp in seen_tx:
                        continue
                    fam = pr.plan.candidates[0].name.split("(")[0]
                    if pass_fam and fam in seen_fam:
                        continue
                    picked.append((v, pr, st, mode, text, fp))
                    seen_tx.add(fp)
                    seen_fam.add(fam)
                if len(picked) >= beam:
                    break

            # bridge admission: on a stalled round the basin-hops are
            # GUARANTEED at least one seat (extending the beam by one
            # when the weighted proposals filled it) and additionally
            # fill any slots the lex ladder left empty.  Ranked by
            # bridge_rank_key (deepest residue cleared first -- ideally
            # seat=0), family-diverse, never displacing a normal
            # branch, bounded by max_bridges.
            if have_bridge:
                want = max(1, beam - len(picked))
                pool_now = sorted(
                    bridge_reservoir.items(),
                    key=lambda kv: matrix.bridge_rank_key(kv[1][1].score))
                admitted = 0
                seen_bfam: set[str] = set()
                for pass_fam in (True, False):
                    for sig, (v, pr, st, mode) in pool_now:
                        if admitted >= want \
                                or bridges_used >= max_bridges:
                            break
                        if sig in bridge_taken_sigs:
                            continue
                        text = pr.plan.apply(st.text)
                        fp = _fp(text)
                        if fp in visited or fp in seen_tx:
                            # this realization is a known state; drop
                            # the entry so a fresh parent may re-offer
                            # the signature later.
                            bridge_reservoir.pop(sig, None)
                            continue
                        fam = pr.plan.candidates[0].name.split("(")[0]
                        if pass_fam and fam in seen_bfam:
                            continue
                        picked.append((v, pr, st, mode, text, fp))
                        seen_tx.add(fp)
                        seen_bfam.add(fam)
                        bridge_taken_sigs.add(sig)
                        bridge_reservoir.pop(sig, None)
                        bridges_used += 1
                        admitted += 1
                    if admitted >= want:
                        break

            new_beam: list[_Node] = []
            for v, pr, st, mode, text, fp in picked:
                nid = f"n{next(node_seq)}"
                visited.add(fp)
                node = _Node(id=nid, text=text, score=pr.score,
                             parent=st.id,
                             basin=(mode == "bridge" or st.basin),
                             hold=(tuple(pr.score.layers[2:5])
                                   if mode == "bridge" else st.hold))
                all_nodes.append(node)
                new_beam.append(node)
                if run_store:
                    run_store.log_node(
                        nid, parent=st.id, round_=rnd, plan=pr.plan,
                        score=pr.score, accepted=True, reason=v.reason)
                steps.append({
                    "round": rnd, "mode": mode, "node": nid,
                    "parent": st.id, "plan": pr.plan.name,
                    "reason": v.reason,
                    "layers": list(pr.score.layers),
                    "bytes": pr.score.bytes})
                _say(f"  round {rnd} [{mode}/{v.reason}] {st.id}->{nid}: "
                     f"{pr.plan.name}  ->  {_lay(pr.score)}")

            # retention + ladder queue: un-escalated states (basin
            # first) survive into free beam slots; the overflow parks
            # in ladder_pending and stays escalation-eligible -- a
            # state dying with its ladder unclimbed is a search HOLE,
            # not a pruning decision.  Re-expansion is free
            # (summary_cache); the escalation consumes one pending
            # state per stalled round, so this terminates.
            new_ids = {n.id for n in new_beam}
            held = [s for s in list(beam_states)
                    + [q for q in ladder_pending.values()
                       if q.id not in beam_ids]
                    if _fp(s.text) not in escalated
                    and s.id not in new_ids]
            held.sort(key=lambda s: (not s.basin, s.score.layers,
                                     s.score.bytes))
            for s in held:
                f = _fp(s.text)
                if len(new_beam) < beam:
                    new_beam.append(s)
                    new_ids.add(s.id)
                    if ladder_pending.pop(f, None) is None:
                        _say(f"  round {rnd}: retained {s.id} "
                             f"(pairs/triples ladder pending)")
                else:
                    if f not in ladder_pending:
                        _say(f"  round {rnd}: parked {s.id} "
                             f"(ladder pending, beam full)")
                    ladder_pending[f] = s

            if not new_beam:
                _say(f"  round {rnd}: no novel step (singles+pairs+"
                     f"triples{'+bridge' if bridge else ''}, "
                     f"policy={policy}) and no ladder pending -- stop")
                break
            beam_states = new_beam
            # a pairs/triples byte-exact was collected as a proposal --
            # short-circuit instead of re-expanding the exact state.
            exact_node = next(
                (n for n in new_beam
                 if n.score is not None and n.score.bytes == 0), None)
            if exact_node is not None:
                byte_exact, final_node = True, exact_node
                _say(f"  round {rnd}: ✓ BYTE-EXACT ({exact_node.id})")
                break

        scored = [n for n in all_nodes if n.score is not None]
        if final_node is None and scored:
            final_node = min(
                scored, key=lambda n: (n.score.layers, n.score.bytes))
        improved = (
            final_node is not None and start_score is not None
            and (final_node.score.layers, final_node.score.bytes)
            < (start_score.layers, start_score.bytes))
        kept = byte_exact or (improved and keep)
        if kept and final_node is not None:
            src_path.write_text(final_node.text)
            _say(f"climb {function}: KEPT {final_node.id} "
                 f"({_lay(final_node.score)}"
                 f"{', BYTE-EXACT' if byte_exact else ''}) -- "
                 f"re-verify with decomp-verify, then commit")
        elif improved and not keep:
            src_path.write_text(original_text)
            _say(f"climb {function}: improved to {final_node.id} "
                 f"({_lay(final_node.score)}) but keep=False -- "
                 f"restored (diff: c2 forge diff {function} "
                 f"{final_node.id})")
        else:
            src_path.write_text(original_text)
            _say(f"climb {function}: no net improvement -- restored")
        os.utime(src_path, None)
    except BaseException:
        # crash safety: never leave a half-explored state on disk
        src_path.write_text(original_text)
        os.utime(src_path, None)
        raise
    finally:
        pool.__exit__(None, None, None)

    report = {
        "function": function, "file": file, "steps": steps,
        "start": ({"layers": list(start_score.layers),
                   "bytes": start_score.bytes} if start_score else None),
        "final": ({"layers": list(final_node.score.layers),
                   "bytes": final_node.score.bytes}
                  if final_node is not None and final_node.score
                  else None),
        "improved": improved,
        "byte_exact": byte_exact,
        "restored": not kept,
        "rounds": rounds_done,
        "beam": beam,
        "policy": policy,
        "bridges_used": bridges_used,
        "bridge_ir_budget": bridge_ir_budget,
        "bridge_isl_budget": bridge_isl_budget,
        "bridge_overbudget": sorted(
            overbudget_paths.values(),
            key=lambda r: (r["layers"][4], r["layers"][3],
                           r["layers"][2], r["layers"][1],
                           r["layers"][0], r["bytes"]))[:25],
        "evaluated": n_evaluated,
        "elapsed_s": round(time.perf_counter() - t_climb0, 1),
        "rate": round(n_evaluated /
                      max(0.001, time.perf_counter() - t_climb0), 1),
        "run_dir": str(run_store.dir) if run_store else None,
    }
    _say(f"climb {function}: evaluated {n_evaluated} variants in "
         f"{report['elapsed_s']:.0f}s ({report['rate']:.0f}/s, "
         f"jobs={jobs}"
         f"{f', {bridges_used} bridge(s)' if bridges_used else ''})")
    if overbudget_paths:
        best = report["bridge_overbudget"][0]
        _say(f"climb {function}: {len(overbudget_paths)} deep-gain "
             f"path(s) were beyond the bridge budget (best: {best['plan']} "
             f"needs --bridge-ir>={best['need_ir']} "
             f"--bridge-isl>={best['need_isl']}) -- rerun wider to explore")
    if run_store:
        run_store.finalize(
            status=("byte-exact" if byte_exact
                    else "improved" if report["improved"]
                    else "neutral"),
            final=report["final"], rounds=rounds_done,
            steps=len(steps), kept=kept,
            evaluated=n_evaluated, elapsed_s=report["elapsed_s"],
            rate=report["rate"], bridges_used=bridges_used,
            bridge_overbudget=report["bridge_overbudget"])
    return report

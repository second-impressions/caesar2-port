r"""sig-drift command: detect per-TU function-signature inconsistencies.

Watcom 10.0a uses **per-TU prototype visibility** for call-site
codegen.  When ``screens.c`` is compiled, only declarations visible
inside ``screens.c`` (extern decls, forward decls, definitions in
the same TU, and ``#include``d headers) affect calls in
``screens.c``.  If ``screens.c`` declares::

    extern void font_list(int, int, int, int);   /* 4 args */

but PS source had::

    extern void font_list(int, int, int, int, unsigned char *font, int);  /* 6 args */

then ``screens.c``'s calls to ``font_list`` miscompile: caller-side
codegen sets up only 4 reg parms and **no stack push** for the
trailing two args.  This is a TU-LOCAL bug — other TUs that have
the correct 6-arg declaration are unaffected.

The bug is invisible to ``c2 callgraph --check`` because that tool
operates on the function-NAME level: it picks ONE declared sig per
function (whichever ``scan_declared_sigs`` finds last) and compares
against caller-side evidence.  Cross-TU drift goes undetected.

This command bins every declaration by ``(function_name, declared_sig)``
and surfaces names where:

  * Multiple TUs declare different sigs (inter-TU drift), OR
  * At least one TU's declaration disagrees with the
    caller-evidence "truth" sig (TU-vs-truth drift).

The CallZap-relevant view canonicalizes each sig to
``(n_reg_args, returns_void)`` — these are the only things that
affect Watcom's caller-side regalloc.  Type-only drift (e.g.
``char *`` vs ``int *``) is reported separately as it affects
warnings and semantic correctness but not codegen byte-equality.

Usage::

    # All names with inter-TU or vs-truth drift
    uv run c2 sig-drift

    # Per-TU rollup: which TU is most "infected"?
    uv run c2 sig-drift --by-tu

    # Only drift that affects CallZap (highest leverage)
    uv run c2 sig-drift --callzap

    # One function: show every TU's view of it + truth
    uv run c2 sig-drift font_list

    # JSON
    uv run c2 sig-drift --json
"""

from __future__ import annotations

import json as _json
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated, Optional

import typer
from pycparser import c_ast
from rich.console import Console
from rich.table import Table

from c2.commands.c_source import (
    classify_source,
    _is_void_return,
    _return_type_str,
    _get_generator,
)
from c2.commands.inferred_sig import (
    DeclaredSig,
    _ARG_REGS,
    infer_sig,
    infer_sig_from_callers,
)


# ── Data model ────────────────────────────────────────────────────────


@dataclass(frozen=True)
class CallZapSig:
    """The codegen-relevant projection of a C signature.

    For Watcom's __watcall: CallZap is determined entirely by the
    *register* arg count (clamped to 4: EAX/EDX/EBX/ECX) and the
    return type (void vs not).  Stack args (5th onward) do NOT
    affect CallZap because the caller pushes them and the callee
    cleans them up; no caller-side register is clobbered.

    Equality therefore ignores ``n_total_args`` — only
    ``n_reg_args`` and ``returns_void`` matter for CallZap drift.
    ``n_total_args`` is kept as an informational field for the
    pretty-printed sig.
    """
    n_reg_args: int       # clamped to 4 — the only codegen-affecting count
    returns_void: bool
    n_total_args: int = field(default=0, compare=False, hash=False)

    @classmethod
    def from_counts(cls, n_total_args: int, returns_void: bool) -> "CallZapSig":
        return cls(
            n_reg_args=min(n_total_args, 4),
            returns_void=returns_void,
            n_total_args=n_total_args,
        )

    def render(self) -> str:
        ret = "void" if self.returns_void else "int"
        if self.n_total_args == 0:
            args = "void"
        elif self.n_total_args <= 4:
            args = ", ".join(["int"] * self.n_total_args)
        else:
            args = ", ".join(["int"] * 4 + ["..."] * (self.n_total_args - 4))
        return f"{ret} f({args})"


@dataclass
class TUDecl:
    """One TU's declaration of one function (extern / forward / def)."""
    name: str
    file: str
    line: int
    kind: str            # 'extern', 'forward', 'def'
    return_type: str
    arg_types: list[str]
    raw: str             # full rendered signature
    has_value_return: bool = False
    """Only for definitions: does the C body contain `return expr;`."""

    @property
    def returns_void(self) -> bool:
        return self.return_type.strip().lower() == "void"

    @property
    def n_args(self) -> int:
        return len(self.arg_types)

    def callzap_sig(self) -> CallZapSig:
        return CallZapSig.from_counts(self.n_args, self.returns_void)


@dataclass
class Drift:
    """All TU declarations of one function + the truth sig."""
    name: str
    decls: list[TUDecl]
    truth_sig: Optional[CallZapSig] = None
    truth_source: str = "unknown"

    def buckets(self) -> dict[CallZapSig, list[TUDecl]]:
        b: dict[CallZapSig, list[TUDecl]] = defaultdict(list)
        for d in self.decls:
            b[d.callzap_sig()].append(d)
        return dict(b)

    def has_inter_tu_drift(self) -> bool:
        """True when ≥2 distinct CallZap sigs appear across TUs."""
        return len(self.buckets()) > 1

    def has_truth_drift(self) -> bool:
        """True when at least one TU's sig disagrees with truth_sig."""
        if self.truth_sig is None:
            return False
        return any(s != self.truth_sig for s in self.buckets().keys())

    def has_any_drift(self) -> bool:
        return self.has_inter_tu_drift() or self.has_truth_drift()


# ── Declaration scanning ──────────────────────────────────────────────


def _extract_decl_sig(node: c_ast.Decl) -> Optional[tuple[str, str, list[str]]]:
    """Return (name, return_type, arg_types) or None on failure."""
    if not isinstance(node.type, c_ast.FuncDecl):
        return None
    name = node.name
    if not name:
        return None
    try:
        ret = _return_type_str(node.type)
        if _is_void_return(node.type):
            ret = "void"
    except Exception:
        return None
    # Reuse the arg-type extractor used for definitions.
    from c2.commands.inferred_sig import _arg_types_from_funcdecl
    arg_types = _arg_types_from_funcdecl(node.type)
    return name, ret, arg_types


def _extract_def_sig(fn_def: c_ast.FuncDef) -> Optional[tuple[str, str, list[str]]]:
    """Return (name, return_type, arg_types) for a FuncDef."""
    return _extract_decl_sig(fn_def.decl)


def scan_all_tu_declarations(
    src_dirs: list[Path] | None = None,
    *,
    include_headers: bool = False,
) -> dict[str, list[TUDecl]]:
    """Scan every ``.c`` file for function decls (extern, forward, def).

    Returns ``{function_name: [TUDecl, ...]}``.  Each function name
    may appear with multiple TUDecls — one per file that declares
    or defines it.

    Headers under ``decomp/include`` are skipped by default because:

    * Most game ``extern`` decls in PS source were per-``.c`` file,
      not header-based (verified by Rule 37 in
      ``docs/watcom-codegen-patterns.md``).
    * Including headers would over-count by adding identical decls
      from every TU that ``#include``s the header.

    Pass ``include_headers=True`` to scan ``decomp/include/*.h`` too.
    """
    if src_dirs is None:
        src_dirs = [Path("decomp/src")]
    out: dict[str, list[TUDecl]] = defaultdict(list)
    gen = _get_generator()
    import re as _re
    files: list[Path] = []
    for d in src_dirs:
        files.extend(sorted(d.glob("*.c")))
    if include_headers:
        for d in src_dirs:
            files.extend(sorted(d.parent.glob("include/*.h")))
    for src in files:
        try:
            text = src.read_text()
        except OSError:
            continue
        try:
            decls = classify_source(text, src.name)
        except Exception:
            continue
        nonstandard_abi_names = set()
        for m in _re.finditer(r"^\s*#\s*pragma\s+aux\s+(\w+)\b", text, _re.M):
            nonstandard_abi_names.add(m.group(1))
        # All three kinds: extern, forward (no extern but is decl), def
        for kind, nodes in (
            ("extern", decls.extern_fns),
            ("forward", decls.forward_fns),
        ):
            for n in nodes:
                got = _extract_decl_sig(n)
                if got is None:
                    continue
                name, ret, args = got
                if name in nonstandard_abi_names:
                    continue
                try:
                    raw = gen.visit(n).strip()
                except Exception:
                    raw = name
                if "__far" in raw or "__interrupt" in raw:
                    # Non-default ABI declarations require pragma-aware
                    # modelling; CallZapSig's plain __watcall projection
                    # is not valid for them.
                    continue
                line = n.coord.line if n.coord else 0
                out[name].append(TUDecl(
                    name=name,
                    file=str(src),
                    line=line,
                    kind=kind,
                    return_type=ret,
                    arg_types=args,
                    raw=raw,
                ))
        for fn_def in decls.func_defs:
            got = _extract_def_sig(fn_def)
            if got is None:
                continue
            name, ret, args = got
            if name in nonstandard_abi_names:
                continue
            try:
                raw = gen.visit(fn_def.decl).strip()
            except Exception:
                raw = name
            if "__far" in raw or "__interrupt" in raw:
                continue
            line = fn_def.decl.coord.line if fn_def.decl.coord else 0
            stack = [fn_def.body]
            has_value_return = False
            while stack:
                node = stack.pop()
                if isinstance(node, c_ast.Return) and node.expr is not None:
                    has_value_return = True
                    break
                for _, child in node.children():
                    stack.append(child)
            out[name].append(TUDecl(
                name=name,
                file=str(src),
                line=line,
                kind="def",
                return_type=ret,
                arg_types=args,
                raw=raw,
                has_value_return=has_value_return,
            ))
    return dict(out)


# ── Truth sig (caller-side prefix-property + body) ────────────────────


def _truth_sig(name: str, decls: list[TUDecl] | None = None) -> tuple[Optional[CallZapSig], str]:
    """Compute the truth CallZap sig for one function.

    Combines body-side inference with caller-side prefix-property
    extension (see ``CallerEvidence.confirmed_arg_count_prefix_property``).
    Returns ``(sig, source_label)`` where ``source_label`` is the
    provenance of the truth value.
    """
    try:
        body = infer_sig(name)
    except (KeyError, ValueError, FileNotFoundError):
        return None, "no-asm"
    body_n = len(body.arg_regs) + len(body.stack_args)
    declared_max_n = max((d.n_args for d in decls or []), default=0)
    try:
        ev = infer_sig_from_callers(name)
    except (KeyError, ValueError, FileNotFoundError):
        ev = None
    has_return = body.has_return
    source_has_value_return = decls is not None and any(
        d.kind == "def" and not d.returns_void and d.has_value_return
        for d in decls
    )
    if source_has_value_return:
        # A source body with `return expr;` is deliberate even if
        # the current caller set does not consume EAX or the asm
        # body-side scan misses the merged return path.
        has_return = True
    if ev and ev.n_call_sites > 0:
        strict_declared_n = ev.confirmed_arg_count(threshold=1.0)
        if (
            declared_max_n > body_n
            and strict_declared_n >= declared_max_n
        ):
            # If every observed PS call site sets the currently-declared
            # register-arg prefix, trust that source-level prototype even
            # when the callee body ignores/pass-throughs those args.  This
            # is common for codegen-shaping unused params.
            return CallZapSig.from_counts(declared_max_n, not has_return), \
                   "declared-supported-by-callers"

        if body.leaks_call_eax and not source_has_value_return:
            has_return = False
        elif (
            not has_return
            and ev.eax_used_after_call > 0
            and decls is not None
            and any(not d.returns_void for d in decls)
        ):
            # Body-side return detection can miss values that flow
            # through tail-merged epilogues or helper calls.  If the
            # reconstructed source already has a non-void signature and
            # at least one caller consumes EAX, keep that as the truth.
            # This avoids rewriting known-good local declarations to
            # void just because the body heuristic is conservative.
            has_return = True

        cn, conf = ev.confirmed_arg_count_prefix_property()
        if declared_max_n == body_n:
            cn = None
        if cn is not None and cn > len(body.arg_regs):
            # Caller-side extends.  Total args = caller-confirmed reg
            # args + body-side stack args.
            total = cn + len(body.stack_args)
            return CallZapSig.from_counts(total, not has_return), \
                   f"caller-extends-{conf}"
    return CallZapSig.from_counts(body_n, not has_return), "body"


# ── Drift detection ───────────────────────────────────────────────────


def _clib_symbol_names() -> set[str]:
    """Watcom CRT names we should not police as PS-source sig drift.

    The CRT bodies linked into PS.EXE often include tiny wrapper
    functions (e.g. ``open`` → ``sopen``) whose return value is the
    trailing call's EAX.  Body-side inference deliberately treats
    ``call X; ret`` as ambiguous/void for game functions, so applying
    it to CRT imports creates false hygiene drift.  Keep sig-drift
    focused on game/hand-written-asm declarations.
    """
    path = Path("decomp/lib/clib3r-symbols.txt")
    try:
        raw = path.read_text().splitlines()
    except OSError:
        return set()
    out: set[str] = set()
    for line in raw:
        name = line.strip()
        if not name:
            continue
        out.add(name)
        if name.endswith("_"):
            out.add(name[:-1])
    return out


def find_drift(
    src_dirs: list[Path] | None = None,
    *,
    include_headers: bool = False,
    callzap_only: bool = False,
) -> list[Drift]:
    """Scan every TU and surface functions with drift.

    A function exhibits drift when EITHER of these is true:

      * Inter-TU drift: at least two TUs declare it with different
        CallZap-relevant signatures.
      * Truth drift: at least one TU's declaration disagrees with
        the caller-evidence + body truth sig.

    The result is sorted by severity:

      1. Most affected TUs (= largest declarations list).
      2. Functions with truth drift before pure inter-TU drift.
      3. Alphabetical name within ties.
    """
    all_decls = scan_all_tu_declarations(src_dirs, include_headers=include_headers)
    clib_names = _clib_symbol_names()
    out: list[Drift] = []
    for name, decls in sorted(all_decls.items()):
        if name in clib_names and not any(d.kind == "def" for d in decls):
            continue
        truth_sig, truth_source = _truth_sig(name, decls)
        d = Drift(name=name, decls=decls, truth_sig=truth_sig,
                  truth_source=truth_source)
        if not d.has_any_drift():
            continue
        if callzap_only and not d.has_truth_drift() and not d.has_inter_tu_drift():
            continue
        out.append(d)
    out.sort(
        key=lambda d: (
            -len(d.decls),
            0 if d.has_truth_drift() else 1,
            d.name,
        )
    )
    return out


def per_tu_summary(drifts: list[Drift]) -> list[tuple[str, int, int]]:
    """Roll up drift by TU.

    Returns ``[(tu_path, n_drifted_decls, n_truth_drift), ...]``
    sorted by drift count descending.
    """
    by_tu: dict[str, list[Drift]] = defaultdict(list)
    truth_by_tu: dict[str, int] = defaultdict(int)
    for d in drifts:
        truth = d.truth_sig
        for decl in d.decls:
            by_tu[decl.file].append(d)
            if truth is not None and decl.callzap_sig() != truth:
                truth_by_tu[decl.file] += 1
    out = [
        (tu, len(ds), truth_by_tu.get(tu, 0))
        for tu, ds in by_tu.items()
    ]
    out.sort(key=lambda r: (-r[1], -r[2], r[0]))
    return out


def _load_diffing_fns() -> set[str]:
    """Load the diffing-function set from the sibling-status cache."""
    cache = Path(".c2-cache/sibling-status.json")
    if not cache.exists():
        return set()
    try:
        data = _json.loads(cache.read_text())
        d = data.get("diffing", {})
        # Schema: {fn_name: byte_diff_count}.  Filter to count > 0.
        if isinstance(d, dict):
            return {n for n, c in d.items() if isinstance(c, (int, float)) and c > 0}
        if isinstance(d, list):
            return set(d)
        return set()
    except (OSError, ValueError, KeyError):
        return set()


@dataclass
class ActionableDrift:
    """A drift case that has at least one diffing caller in a TU whose
    declaration of the callee disagrees with truth.  Fixing the callee's
    sig in those TUs is the highest-leverage cleanup action."""
    callee: str
    truth_sig: CallZapSig
    actionable_callers: list[tuple[str, str]]
    """(caller_name, caller_tu) pairs."""
    n_total_callers: int
    n_diffing_callers: int

    @property
    def n_actionable(self) -> int:
        return len(self.actionable_callers)


def actionable_drift(
    src_dirs: list[Path] | None = None,
    *,
    diffing_fns: set[str] | None = None,
) -> list[ActionableDrift]:
    """Drift cases ranked by impact on currently-diffing functions.

    For each drifting callee X with a known truth sig:

      1. Find every direct caller C of X.
      2. Filter to C that is currently diffing.
      3. Filter further to C whose own TU declares X with a CallZap
         that disagrees with truth.

    Step 3 ensures the caller's miscompilation is causally attributable
    to the wrong declared sig.  If the TU declares X with the RIGHT
    sig (or doesn't declare X at all — implicit-int Rule 37 case),
    the caller's diff has a different cause and isn't actionable via
    a sig fix.

    Imports the call graph from :mod:`c2.commands.callgraph` on first
    use.  Imports the diffing-function set from the sibling-status
    cache by default; pass ``diffing_fns`` to override.
    """
    from c2.commands.callgraph import build_callgraph

    drifts = find_drift(src_dirs)
    if diffing_fns is None:
        diffing_fns = _load_diffing_fns()
    _callers_to_calls, callees_to_callers = build_callgraph()
    all_decls = scan_all_tu_declarations(src_dirs or [Path("decomp/src")])

    # Function-name → file_where_defined (canonical owning TU).
    fn_def_file: dict[str, str] = {}
    for nm, decls in all_decls.items():
        for d in decls:
            if d.kind == "def":
                fn_def_file[nm] = d.file
                break

    # Function-name → definition line.  Within a TU, a later function
    # definition is NOT a visible prototype for earlier callers (C89
    # implicit-int / no-prototype behaviour).  Model only declarations
    # that appear before the caller's definition line as visible.
    fn_def_line: dict[str, int] = {}
    for nm, decls in all_decls.items():
        for d in decls:
            if d.kind == "def":
                fn_def_line[nm] = d.line
                break

    # TU → callee → visible declarations in source order.
    tu_decls: dict[str, dict[str, list[TUDecl]]] = defaultdict(lambda: defaultdict(list))
    for nm, decls in all_decls.items():
        for d in decls:
            tu_decls[d.file][nm].append(d)
    for by_name in tu_decls.values():
        for decl_list in by_name.values():
            decl_list.sort(key=lambda d: d.line)

    out: list[ActionableDrift] = []
    for d in drifts:
        if d.truth_sig is None:
            continue
        callers = callees_to_callers.get(d.name, set())
        actionable = []
        n_diffing = 0
        for c in callers:
            if c not in diffing_fns:
                continue
            n_diffing += 1
            tu = fn_def_file.get(c)
            if tu is None:
                continue
            caller_line = fn_def_line.get(c)
            if caller_line is None:
                continue
            visible = [
                decl for decl in tu_decls.get(tu, {}).get(d.name, [])
                if decl.line < caller_line
            ]
            if not visible:
                # No visible prototype at this call site; it compiles
                # as implicit-int/no-prototype and cannot be fixed by
                # editing a later definition's signature.
                continue
            visible_decl = visible[-1]
            if visible_decl.kind == "def":
                # A prototype-style definition that appears before the
                # caller can technically influence later calls, but
                # these cases are not Phase-1 declaration hygiene: fixing
                # them requires reshaping the function definition and all
                # calls (and single-caller body-side inference often
                # under-counts intentionally ignored parms).  Keep
                # --actionable focused on explicit extern/forward decls
                # that can be corrected locally without rewriting bodies.
                continue
            tu_sig = visible_decl.callzap_sig()
            if tu_sig == d.truth_sig:
                continue
            actionable.append((c, tu))
        if not actionable:
            continue
        out.append(ActionableDrift(
            callee=d.name,
            truth_sig=d.truth_sig,
            actionable_callers=actionable,
            n_total_callers=len(callers),
            n_diffing_callers=n_diffing,
        ))
    out.sort(key=lambda a: (-a.n_actionable, -a.n_diffing_callers, a.callee))
    return out


# ── CLI ───────────────────────────────────────────────────────────────


def sig_drift(
    name: Annotated[
        Optional[str],
        typer.Argument(
            help="One function name (show every TU's view).  "
                 "Omit to scan everything.",
        ),
    ] = None,
    by_tu: Annotated[
        bool,
        typer.Option(
            "--by-tu",
            help="Roll up drift by TU (which TU has the most drift).",
        ),
    ] = False,
    impact: Annotated[
        bool,
        typer.Option(
            "--actionable",
            help="Rank drift cases by impact on currently-diffing functions.  "
                 "Only shows drift cases with ≥1 diffing caller in a TU that "
                 "declares the callee with a non-truth sig (i.e. fixable).",
        ),
    ] = False,
    callzap_only: Annotated[
        bool,
        typer.Option(
            "--callzap/--all-drift",
            help="Restrict to drift that affects CallZap (the codegen-"
                 "byte-equality leverage).  Default: report everything.",
        ),
    ] = False,
    include_headers: Annotated[
        bool,
        typer.Option(
            "--include-headers",
            help="Also scan decomp/include/*.h (default: only .c files).",
        ),
    ] = False,
    limit: Annotated[
        int,
        typer.Option("--limit", "-n", help="Cap rows in tabular output."),
    ] = 40,
    json_out: Annotated[
        bool,
        typer.Option("--json", help="Emit JSON instead of a table."),
    ] = False,
) -> None:
    """Detect per-TU signature drift across decomp/src/."""
    console = Console(color_system=None)
    src_dirs = [Path("decomp/src")]

    # Single-function mode.
    if name is not None:
        all_decls = scan_all_tu_declarations(src_dirs, include_headers=include_headers)
        decls = all_decls.get(name, [])
        truth_sig, truth_source = _truth_sig(name)
        if json_out:
            print(_json.dumps({
                "name": name,
                "truth": {
                    "sig": truth_sig.render() if truth_sig else None,
                    "n_total_args": truth_sig.n_total_args if truth_sig else None,
                    "returns_void": truth_sig.returns_void if truth_sig else None,
                    "source": truth_source,
                },
                "decls": [
                    {
                        "file": d.file, "line": d.line, "kind": d.kind,
                        "return_type": d.return_type,
                        "arg_types": d.arg_types,
                        "raw": d.raw,
                    } for d in decls
                ],
            }, indent=2))
            return
        console.print(f"[bold]{name}[/bold] — truth sig: "
                      f"[green]{truth_sig.render() if truth_sig else '(unknown)'}[/green] "
                      f"(source: {truth_source})")
        if not decls:
            console.print("  [yellow]no declarations or definitions in decomp/src/[/yellow]")
            return
        t = Table()
        t.add_column("kind")
        t.add_column("file:line", style="cyan")
        t.add_column("n_args", justify="right")
        t.add_column("ret")
        t.add_column("callzap")
        t.add_column("declared sig")
        for d in decls:
            cz = d.callzap_sig()
            match = "✓" if truth_sig and cz == truth_sig else "✗"
            t.add_row(
                d.kind,
                f"{d.file}:{d.line}",
                str(d.n_args),
                d.return_type,
                f"{match}",
                d.raw[:80] + ("…" if len(d.raw) > 80 else ""),
            )
        console.print(t)
        return

    # Actionable mode: rank by diffing-caller impact.
    if impact:
        rows = actionable_drift(src_dirs)
        if json_out:
            print(_json.dumps([
                {
                    "callee": r.callee,
                    "truth_sig": r.truth_sig.render(),
                    "truth_n_reg_args": r.truth_sig.n_reg_args,
                    "truth_returns_void": r.truth_sig.returns_void,
                    "n_actionable": r.n_actionable,
                    "n_diffing_callers": r.n_diffing_callers,
                    "n_total_callers": r.n_total_callers,
                    "actionable_callers": [
                        {"caller": c, "tu": tu}
                        for c, tu in r.actionable_callers
                    ],
                }
                for r in rows
            ], indent=2))
            return
        if not rows:
            console.print(
                "[green]no actionable drift cases[/green] "
                "(no drift currently affects a diffing function via wrong TU sig)"
            )
            return
        t = Table(
            title=f"Actionable drift ({len(rows)} callees, "
                  f"{sum(r.n_actionable for r in rows)} caller-fixups)"
        )
        t.add_column("act", justify="right", style="red")
        t.add_column("diff/tot", justify="right")
        t.add_column("callee", style="cyan")
        t.add_column("truth", style="green")
        t.add_column("diffing callers (TUs)")
        for r in rows[:limit]:
            # Compact caller list: "name (tu_basename), ..." up to 3
            sample = ", ".join(
                f"{c} ({Path(tu).name})"
                for c, tu in r.actionable_callers[:3]
            )
            if r.n_actionable > 3:
                sample += f" + {r.n_actionable - 3} more"
            t.add_row(
                str(r.n_actionable),
                f"{r.n_diffing_callers}/{r.n_total_callers}",
                r.callee,
                r.truth_sig.render(),
                sample,
            )
        console.print(t)
        if len(rows) > limit:
            console.print(f"  ... {len(rows) - limit} more (use -n / --json)")
        return

    # Scan everything.
    drifts = find_drift(src_dirs, include_headers=include_headers,
                        callzap_only=callzap_only)

    if by_tu:
        rows = per_tu_summary(drifts)
        if json_out:
            print(_json.dumps([
                {"file": tu, "drifted_decls": n, "truth_drift": td}
                for tu, n, td in rows
            ], indent=2))
            return
        t = Table(title=f"Per-TU drift summary ({len(rows)} TUs)")
        t.add_column("TU", style="cyan")
        t.add_column("drift decls", justify="right")
        t.add_column("truth drift", justify="right", style="red")
        for tu, n, td in rows[:limit]:
            t.add_row(tu, str(n), str(td))
        console.print(t)
        if len(rows) > limit:
            console.print(f"  ... {len(rows) - limit} more (use -n / --json)")
        return

    if json_out:
        print(_json.dumps([
            {
                "name": d.name,
                "truth_sig": d.truth_sig.render() if d.truth_sig else None,
                "truth_source": d.truth_source,
                "n_decls": len(d.decls),
                "n_buckets": len(d.buckets()),
                "has_truth_drift": d.has_truth_drift(),
                "has_inter_tu_drift": d.has_inter_tu_drift(),
                "buckets": [
                    {
                        "sig": k.render(),
                        "n_total_args": k.n_total_args,
                        "returns_void": k.returns_void,
                        "files": [
                            {"file": x.file, "line": x.line, "kind": x.kind}
                            for x in v
                        ],
                    }
                    for k, v in d.buckets().items()
                ],
            }
            for d in drifts
        ], indent=2))
        return

    if not drifts:
        console.print("[green]no signature drift found[/green]")
        return

    t = Table(title=f"Signature drift ({len(drifts)} functions)")
    t.add_column("decls", justify="right")
    t.add_column("buckets", justify="right")
    t.add_column("function", style="cyan")
    t.add_column("truth", style="green")
    t.add_column("drift kind")
    t.add_column("file buckets")
    for d in drifts[:limit]:
        kinds = []
        if d.has_truth_drift():
            kinds.append("[red]truth[/red]")
        if d.has_inter_tu_drift():
            kinds.append("[yellow]inter-TU[/yellow]")
        truth_str = d.truth_sig.render() if d.truth_sig else "?"
        buckets_str = "; ".join(
            f"{k.render().split()[0]}/{k.n_total_args}arg × {len(v)}"
            for k, v in d.buckets().items()
        )
        t.add_row(
            str(len(d.decls)),
            str(len(d.buckets())),
            d.name,
            truth_str,
            " ".join(kinds),
            buckets_str[:80] + ("…" if len(buckets_str) > 80 else ""),
        )
    console.print(t)
    if len(drifts) > limit:
        console.print(f"  ... {len(drifts) - limit} more (use -n / --json)")

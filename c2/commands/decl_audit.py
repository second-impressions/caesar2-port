"""decl-audit: find call sites whose callee declaration is wrong or missing.

Because PS's TUs do **not** ``#include c2_funcs.h``, almost every
cross-TU call in the corpus is *implicit-int* (K&R ``int f()``).  That
is usually PS-faithful (wcc386 tolerates it; the PS bytes were built
that way), but three situations are genuine hazards worth auditing,
especially inside still-diffing functions:

  MISMATCH     A **local** ``extern``/forward decl in the TU disagrees
               with the callee's real definition in a way that changes
               the caller's codegen -- a **non-int** return type/width or
               signedness that forces AL/``movsx`` reads away from PS's
               byte-exact EAX default, or a **prototyped** arg count that
               disagrees.  A plain ``int`` extern is NOT a mismatch: it
               is exactly the implicit-int contract wcc386 synthesises
               for an undeclared callee (byte-neutral by construction --
               proven on the ``affected_by_cover`` class, where an ``int``
               extern is byte-exact but a ``char`` extern breaks it), so
               the ``extern int f();`` visibility decls are inert here.
               An **unprototyped** ``f()`` (empty parens) has UNKNOWN
               args, so its arg count is never compared (only ``f(void)``
               or a real param list counts).

  USED-NONINT  An **implicit-int** call whose return value is USED, but
               the callee's real return type is not ``int`` (char /
               short / pointer / enum).  The caller assumes ``int``
               (reads EAX); the callee may only set AL.  Candidate for
               a missing decl OR a call-site cast -- but VERIFY against
               a byte-exact sibling first: if one calls it the same way
               and is byte-exact, implicit-int is PS-faithful (proven
               for get_heading; a typed decl there breaks the callers).

  PARAM-CAST   An argument position cast to the **same** type at *every*
               call site.  Usually the cast matches the real param type
               (redundant, PS-faithful); a ``cast != real param`` flag
               marks the interesting signedness/width divergences.

  CAST-CONST   A callee's RETURN cast to the **same** type at *every*
               used call site in the TU.  Looks like a missing
               ``extern T f()``, but in practice these are usually
               already in byte-exact code (the casts are real PS source).

  CALLZAP      (``--callzap``) A ``void`` callee called implicit-int with
               the return discarded -- the caller still models EAX as a
               live int def.  ~800 sites corpus-wide, all PS-faithful;
               shown so a diffing function's CallZap surface is visible
               (pair with a selector or ``--diffing-only``).

The report cross-references each caller against ``.c2-cache/verify.json``
(a diffing function is marked ``exact != True`` with ``diff_byte_count>0``)
so you can see whether the hazard sits in a diffing or byte-exact
function -- a hazard in a *diffing* function is the actionable one, and
a byte-exact sibling with the same pattern is the proof it is inert.
Call-before-definition is handled positionally: a local callee is only
in scope once its definition or a forward decl precedes the call, so
implicit-int classification matches wcc386's W131.
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import typer
from typing_extensions import Annotated

from c2.forge import cspan


# ── tree-sitter helpers ────────────────────────────────────────────────────────

def _parse(path: Path):
    src = path.read_bytes()
    return cspan._parser().parse(src).root_node, src


def _txt(node, src: bytes) -> str:
    return src[node.start_byte:node.end_byte].decode("utf8", "replace")


def _norm_type(t: str | None) -> str | None:
    if t is None:
        return None
    return t.replace("unsigned ", "u").replace("signed ", "s").replace(" ", "")


def _func_name_and_params(declr):
    """From a declarator, drill to the (identifier, parameter_list) of a
    function declarator, unwrapping pointer/parenthesized wrappers."""
    n = declr
    while n is not None and n.type in ("pointer_declarator", "parenthesized_declarator"):
        n = n.child_by_field_name("declarator")
    if n is None or n.type != "function_declarator":
        return None, None
    inner = n.child_by_field_name("declarator")
    params = n.child_by_field_name("parameters")
    while inner is not None and inner.type in ("pointer_declarator", "parenthesized_declarator"):
        inner = inner.child_by_field_name("declarator")
    return inner, params


def _param_types(params, src: bytes):
    if params is None:
        return None
    out = []
    for c in params.named_children:
        if c.type == "parameter_declaration":
            out.append(re.sub(r"\s+", " ", _txt(c, src)).strip())
        elif c.type == "variadic_parameter":
            out.append("...")
    if out == ["void"]:
        return []
    if not out:
        # Empty parens `f()` is a K&R *unprototyped* declaration -- the
        # argument list is UNKNOWN, not zero.  Only `f(void)` means zero
        # args (handled above).  Returning None keeps the argc MISMATCH
        # check from firing a bogus "argc 0 vs def N" on unprototyped
        # forward decls (e.g. the implicit-int-made-visible `extern int
        # f();` blocks).
        return None
    return out


def _ret_type(decl_node, src: bytes) -> str:
    t = decl_node.child_by_field_name("type")
    base = _txt(t, src).strip() if t is not None else "?"
    ptr = any(cc.type == "pointer_declarator" for cc in decl_node.named_children)
    return base + " *" if ptr else base


def _walk(node):
    stack = [node]
    while stack:
        n = stack.pop()
        yield n
        stack.extend(n.children)


def _calls(node, src: bytes):
    for n in _walk(node):
        if n.type == "call_expression":
            fn = n.child_by_field_name("function")
            if fn is not None and fn.type == "identifier":
                yield _txt(fn, src), n


def _ret_used(call_node) -> bool:
    p = call_node.parent
    if p is None:
        return True
    if p.type == "expression_statement":
        return False
    if p.type == "comma_expression":
        return False
    return True


def _cast_type(call_node, src: bytes) -> str | None:
    p = call_node.parent
    if p is not None and p.type == "cast_expression":
        t = p.child_by_field_name("type")
        if t is not None:
            return re.sub(r"\s+", " ", _txt(t, src)).strip()
    return None


def _arg_casts(call_node, src: bytes):
    """Yield ``(position, cast_type|None)`` for each positional argument."""
    args = call_node.child_by_field_name("arguments")
    if args is None:
        return
    for pos, a in enumerate(args.named_children):
        ct = None
        if a.type == "cast_expression":
            t = a.child_by_field_name("type")
            if t is not None:
                ct = re.sub(r"\s+", " ", _txt(t, src)).strip()
        yield pos, ct


def _param_base_type(param_decl: str | None) -> str | None:
    """Strip the parameter NAME off a ``parameter_declaration`` string,
    leaving the type (e.g. ``"signed char dir"`` -> ``"signed char"``,
    ``"unsigned char *map"`` -> ``"unsigned char *"``)."""
    if param_decl is None:
        return None
    s = param_decl.strip()
    m = re.match(r"^(.*?)([A-Za-z_]\w*)\s*$", s)
    if not m or not m.group(1).strip():
        return s
    base = m.group(1).strip()
    return base


# ── corpus model ───────────────────────────────────────────────────────────────

@dataclass
class Corpus:
    defs: dict          # name -> (ret_type, param_types, file)
    header_decls: dict  # header basename -> set(names)
    header_incs: dict   # header basename -> [included header basenames]
    file_incs: dict     # cfile -> [included header basenames]
    local_externs: dict # cfile -> [(name, ret, ptypes)]
    fn_spans: dict      # cfile -> [(name, start_byte, end_byte)]


def _build_corpus(src_dir: Path, inc_dir: Path) -> Corpus:
    cfiles = sorted(src_dir.glob("*.c"))
    hfiles = sorted(inc_dir.glob("*.h"))
    defs, header_decls, header_incs, file_incs, local_externs, fn_spans = (
        {}, {}, {}, {}, {}, {})

    def _incs(root, src):
        out = []
        for n in _walk(root):
            if n.type == "preproc_include":
                p = n.child_by_field_name("path")
                if p is not None:
                    t = _txt(p, src)
                    if t.startswith('"'):
                        out.append(t.strip('"'))
        return out

    for h in hfiles:
        root, src = _parse(h)
        header_incs[h.name] = _incs(root, src)
        names = set()
        for n in _walk(root):
            if n.type == "declaration":
                for d in n.named_children:
                    if d.type in ("function_declarator", "pointer_declarator",
                                  "parenthesized_declarator"):
                        nm, _ = _func_name_and_params(d)
                        if nm is not None and nm.type == "identifier":
                            names.add(_txt(nm, src))
        header_decls[h.name] = names

    for c in cfiles:
        root, src = _parse(c)
        file_incs[c.name] = _incs(root, src)
        exts, spans = [], []
        for n in _walk(root):
            if n.type == "function_definition":
                nm, params = _func_name_and_params(n.child_by_field_name("declarator"))
                if nm is not None and nm.type == "identifier":
                    name = _txt(nm, src)
                    iv = _ret_type(n, src)
                    if n.child_by_field_name("declarator").type == "pointer_declarator":
                        iv = iv  # already includes *
                    defs[name] = (_ret_type(n, src), _param_types(params, src), c.name)
                    spans.append((name, n.start_byte, n.end_byte))
        # top-level extern/forward function decls
        for n in root.children:
            if n.type == "declaration":
                for d in n.named_children:
                    if d.type in ("function_declarator", "pointer_declarator",
                                  "parenthesized_declarator"):
                        nm, params = _func_name_and_params(d)
                        if nm is not None and nm.type == "identifier":
                            exts.append((_txt(nm, src), _ret_type(n, src),
                                         _param_types(params, src)))
        local_externs[c.name] = exts
        fn_spans[c.name] = spans
    return Corpus(defs, header_decls, header_incs, file_incs, local_externs, fn_spans)


def _transitive_headers(start, header_incs) -> set:
    seen, stack = set(), list(start)
    while stack:
        h = stack.pop()
        if h in seen:
            continue
        seen.add(h)
        stack.extend(header_incs.get(h, []))
    return seen


def _load_diffing(cache: Path) -> dict:
    """name -> (exact: bool, diff_byte_count)."""
    if not cache.is_file():
        return {}
    try:
        vj = json.loads(cache.read_text())
    except Exception:
        return {}
    out = {}
    for e in vj.get("functions", []):
        out[e["name"]] = (e.get("exact"), e.get("diff_byte_count"))
    return out


# ── audit ──────────────────────────────────────────────────────────────────────

@dataclass
class Hazard:
    category: str
    caller: str
    cfile: str
    callee: str
    detail: str
    def_file: str | None
    caller_diffing: bool | None
    count: int = 1


def _which_fn(off, spans):
    best = None
    for nm, s, e in spans:
        if s <= off <= e and (best is None or (e - s) < (best[2] - best[1])):
            best = (nm, s, e)
    return best[0] if best else None


def _declared_before(callee: str, off: int, vis: set,
                     decl_events: dict) -> bool:
    """True if ``callee`` is in scope at byte offset ``off``: declared in a
    visible header, or a local forward-decl / definition PRECEDES the
    call.  A local definition that comes AFTER the call does *not* count
    -- wcc386 sees implicit-int there (W131), which is what CallZap keys
    on."""
    if callee in vis:
        return True
    for ev_off in decl_events.get(callee, ()):  # forward-decl + def offsets
        if ev_off < off:
            return True
    return False


def audit(corpus: Corpus, status: dict,
          only_files: set[str] | None,
          only_fns: set[str] | None,
          want_callzap: bool = False) -> list[Hazard]:
    hazards: list[Hazard] = []

    def _diffing(fn):
        # verify.json marks a diffing function with exact=None (or False)
        # and diff_byte_count>0 -- NOT exact=False.  Treat any non-exact
        # entry with bytes as diffing; unknown (absent) stays None.
        if fn not in status:
            return None
        ex, dbc = status[fn]
        if ex is True:
            return False
        return bool(dbc and dbc > 0)

    for c in corpus.file_incs:
        if only_files and c not in only_files:
            continue
        root, src = _parse(Path("decomp/src") / c)
        vis = set()
        for h in _transitive_headers(corpus.file_incs.get(c, []), corpus.header_incs):
            vis |= corpus.header_decls.get(h, set())
        # header-declared functions are always in scope (headers are
        # #included at the top).  Local forward-decls / definitions are
        # only in scope AFTER their byte offset -> tracked positionally.
        spans = corpus.fn_spans.get(c, [])
        decl_events: dict = defaultdict(list)
        for nm, s, e in spans:
            decl_events[nm].append(s)
        for n in root.children:
            if n.type == "declaration":
                for d in n.named_children:
                    if d.type in ("function_declarator", "pointer_declarator",
                                  "parenthesized_declarator"):
                        nm, _ = _func_name_and_params(d)
                        if nm is not None and nm.type == "identifier":
                            decl_events[_txt(nm, src)].append(n.start_byte)

        # -- MISMATCH: local extern disagrees with real definition --
        for name, ret, ptypes in corpus.local_externs.get(c, []):
            if name in corpus.defs:
                drt, dpt, dfile = corpus.defs[name]
                probs = []
                # An `int`-returning extern IS the implicit-int contract:
                # it is exactly what wcc386 synthesises for an undeclared
                # callee, so it is byte-neutral by construction (proven on
                # the affected_by_cover class -- an int extern is
                # byte-exact, a `char` extern breaks it).  Only a NON-int
                # extern return that disagrees with the def is a real
                # codegen hazard (it forces AL/movsx reads away from PS's
                # byte-exact EAX default), so skip the plain-int case.
                if _norm_type(ret) != _norm_type(drt) and _norm_type(ret) != "int":
                    probs.append(f'ret "{ret}" vs def "{drt}"')
                if ptypes is not None and dpt is not None and len(ptypes) != len(dpt):
                    probs.append(f"argc {len(ptypes)} vs def {len(dpt)}")
                if probs:
                    hazards.append(Hazard("MISMATCH", "(file scope)", c, name,
                                          "; ".join(probs), dfile, None, 1))

        # -- per-call analysis (offset-aware implicit-int detection) --
        ret_casts = defaultdict(lambda: {"casts": Counter(), "used": 0})
        arg_stats = defaultdict(lambda: defaultdict(lambda: {"casts": Counter(), "n": 0}))
        usednonint = Counter()            # (cfn, callee, realret) -> count
        callzap = Counter()               # (cfn, callee) -> count  (void, discarded)
        for callee, cnode in _calls(root, src):
            off = cnode.start_byte
            if _declared_before(callee, off, vis, decl_events):
                continue
            cfn = _which_fn(off, spans)
            used = _ret_used(cnode)
            realrt = corpus.defs.get(callee, (None,))[0]
            # return-cast + arg-cast stats (per callee, TU-wide)
            if used:
                ret_casts[callee]["used"] += 1
                rc = _cast_type(cnode, src)
                if rc:
                    ret_casts[callee]["casts"][rc] += 1
            for pos, ac in _arg_casts(cnode, src):
                st = arg_stats[callee][pos]
                st["n"] += 1
                if ac:
                    st["casts"][ac] += 1
            # USED-NONINT
            if used and realrt is not None:
                base = realrt.replace("unsigned ", "").replace("signed ", "").strip()
                if base != "int":
                    usednonint[(cfn, callee, realrt)] += 1
            # CALLZAP: void callee called implicit-int, return discarded
            elif not used and realrt is not None and realrt.strip() == "void":
                callzap[(cfn, callee)] += 1

        for (cfn, callee, realrt), n in usednonint.items():
            hazards.append(Hazard("USED-NONINT", cfn or "?", c, callee,
                                  f'real ret "{realrt}", ret used', corpus.defs[callee][2],
                                  _diffing(cfn), n))
        if want_callzap:
            for (cfn, callee), n in callzap.items():
                hazards.append(Hazard("CALLZAP", cfn or "?", c, callee,
                                      "void callee, implicit-int, ret discarded",
                                      corpus.defs[callee][2], _diffing(cfn), n))

        # -- CAST-CONST: return cast to the same type at EVERY used site --
        for callee, d in ret_casts.items():
            if d["used"] >= 2 and len(d["casts"]) == 1 and \
                    sum(d["casts"].values()) == d["used"]:
                ct = next(iter(d["casts"]))
                realrt = corpus.defs.get(callee, (None, None, None))[0]
                mm = " (== real ret)" if _norm_type(ct) == _norm_type(realrt) else ""
                hazards.append(Hazard(
                    "CAST-CONST", "(all sites)", c, callee,
                    f'all {d["used"]} used calls cast ({ct}); real ret {realrt}{mm}',
                    corpus.defs.get(callee, (None, None, None))[2], None, d["used"]))

        # -- PARAM-CAST: an arg position cast to the same type at EVERY site --
        for callee, positions in arg_stats.items():
            realdef = corpus.defs.get(callee)
            for pos, st in positions.items():
                if st["n"] >= 2 and len(st["casts"]) == 1 and \
                        sum(st["casts"].values()) == st["n"]:
                    ct = next(iter(st["casts"]))
                    realp = None
                    if realdef and realdef[1] and pos < len(realdef[1]):
                        realp = _param_base_type(realdef[1][pos])
                    mm = "" if (realp and _norm_type(ct) == _norm_type(realp)) \
                        else "  <-- cast != real param"
                    hazards.append(Hazard(
                        "PARAM-CAST", "(all sites)", c, callee,
                        f'arg{pos} cast ({ct}) at all {st["n"]} sites; real param {realp}{mm}',
                        realdef[2] if realdef else None, None, st["n"]))

    if only_fns:
        # files that actually contain a selected function -> scope
        # file-level (MISMATCH) rows to those TUs, not the whole corpus.
        sel_files = {c for c, spans in corpus.fn_spans.items()
                     if any(nm in only_fns for nm, _, _ in spans)}
        hazards = [h for h in hazards
                   if h.caller in only_fns or h.callee in only_fns
                   or (h.category == "MISMATCH" and h.cfile in sel_files)]
    return hazards


# ── CLI ─────────────────────────────────────────────────────────────────────────

def decl_audit(
    selectors: Annotated[
        list[str] | None,
        typer.Argument(help="File (foo.c) and/or function names; default whole corpus"),
    ] = None,
    category: Annotated[
        str | None,
        typer.Option("--category", "-c",
                     help="Filter: MISMATCH | USED-NONINT | CAST-CONST"),
    ] = None,
    diffing_only: Annotated[
        bool,
        typer.Option("--diffing-only", help="Only hazards inside still-diffing functions"),
    ] = False,
    callzap: Annotated[
        bool,
        typer.Option("--callzap",
                     help="Also emit CALLZAP rows (void callee called implicit-int, "
                          "return discarded) -- 800+ corpus-wide, so pair with a "
                          "selector or --diffing-only"),
    ] = False,
    decomp_dir: Annotated[
        Path, typer.Option("--decomp", "-d", help="Decomp source directory")
    ] = Path("decomp"),
    json_out: Annotated[bool, typer.Option("--json", help="Machine-readable JSON")] = False,
) -> None:
    """Audit downstream-callee declarations for wrong / missing prototypes."""
    src_dir = decomp_dir / "src"
    inc_dir = decomp_dir / "include"
    if not src_dir.is_dir():
        typer.echo(f"Error: {src_dir} not found", err=True)
        raise typer.Exit(1)

    only_files = {s for s in (selectors or []) if s.endswith(".c")}
    only_files |= {Path(s).name for s in only_files}
    only_fns = {s for s in (selectors or []) if not s.endswith(".c")} or None

    corpus = _build_corpus(src_dir, inc_dir)
    status = _load_diffing(Path(".c2-cache/verify.json"))
    hazards = audit(corpus, status, only_files or None, only_fns,
                    want_callzap=callzap or (category or "").upper() == "CALLZAP")

    if category:
        hazards = [h for h in hazards if h.category == category.upper()]
    if diffing_only:
        hazards = [h for h in hazards if h.caller_diffing is True]

    order = {"MISMATCH": 0, "USED-NONINT": 1, "PARAM-CAST": 2,
             "CAST-CONST": 3, "CALLZAP": 4}
    hazards.sort(key=lambda h: (order.get(h.category, 9), h.cfile, h.callee))

    if json_out:
        typer.echo(json.dumps([h.__dict__ for h in hazards], indent=2))
        return

    if not hazards:
        typer.echo("no declaration hazards found")
        return

    by_cat = Counter(h.category for h in hazards)
    typer.echo(f"decl-audit — {len(hazards)} hazard(s): " +
               ", ".join(f"{k}={v}" for k, v in sorted(by_cat.items())))
    cur = None
    for h in hazards:
        if h.category != cur:
            cur = h.category
            typer.echo(f"\n== {cur} ==")
        tag = ""
        if h.caller_diffing is True:
            tag = "  [DIFFING]"
        elif h.caller_diffing is False:
            tag = "  [exact]"
        loc = f"  (def {h.def_file})" if h.def_file else ""
        cnt = f" x{h.count}" if h.count > 1 else ""
        typer.echo(f"  {h.cfile:14s} {h.caller:26s} -> {h.callee:24s}{cnt:5s} "
                   f"{h.detail}{loc}{tag}")
    typer.echo("\nNote: a hazard in a byte-exact function proves the pattern is "
               "PS-faithful (implicit-int intended); focus on [DIFFING] rows, and "
               "always confirm against a byte-exact sibling before adding a decl.")

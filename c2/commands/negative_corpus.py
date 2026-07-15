"""Negative corpus — source-shape forms that correlate with NOT byte-exact.

Idea
----
We have ~1100 byte-exact decompiled functions (the *positive* corpus) and
~350 that still diff.  The positive corpus is, by construction, "what PS
source shape compiles byte-identically under Watcom 10.0a".  This module
inverts that: it mines the AST of every function, then asks **which source
constructs are over-represented in the diffing set relative to the exact
set** — i.e. which source shapes the byte-exact corpus almost never uses.

Those are the prime suspects for an un-PS-like decompilation: the original
author very likely wrote the function in a *different shape* that the
compiler turned into the bytes we see, and our readable reconstruction
introduced a construct (a cached pointer local, a ternary, a 12-local
function body, …) that PS source did not have.

The crucial honesty control: **size**.  Big functions have more locals,
deeper nesting, more casts AND are independently harder to get byte-exact.
A naive enrichment ("ternary is 35x more common in diffing functions")
mostly re-discovers "diffing functions are bigger".  So every lift here is
**size-stratified** (Mantel–Haenszel style): observed diffs among
feature-carriers divided by the diffs *expected* from each carrier's own
size bucket.  A size-controlled lift > 1 means the construct correlates
with residue even among functions of the same size — that is the real
signal.

This is the data-driven generalization of ``style_check.py`` (which hard-codes
"0 occurrences in the corpus" facts).  Here the frequencies are measured live
and stratified, so the verdicts adapt as the corpus grows.

Output
------
* ``c2 negative-corpus`` — the corpus-wide feature table (exact% / diff% /
  raw enrichment / **size-controlled lift**) plus diffing functions ranked
  by negative score.
* ``c2 negative-corpus <fn>`` — per-function breakdown: every flagged
  construct, how rare it is in the exact corpus, and its size-controlled
  lift, with a one-line verdict.
* ``--json`` for tooling, ``--rebuild`` to force a fresh verify pass.

Built on the project's pycparser front-end (``c2.commands.c_source.parse_c``),
NOT regexes.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Optional

import pycparser.c_ast as c_ast
import typer

from c2.commands.c_source import parse_c
from c2.commands.verify_json import get_verify_json
from c2.commands.anti_rules import feature_rules, rule_label

SRC_DIR = Path("decomp/src")

# Count thresholds for the count-derived presence features.
MANY_LOCALS = 10
DEEP_NEST = 4
MANY_INIT_LOCALS = 6

# Size buckets (function byte size) for the stratified lift.  Chosen so each
# bucket has enough population on the current corpus (see module docstring).
SIZE_EDGES = [80, 200, 500]
SIZE_LABELS = ["<80", "80-200", "200-500", "500+"]


def _size_bucket(size: int) -> str:
    for edge, label in zip(SIZE_EDGES, SIZE_LABELS):
        if size < edge:
            return label
    return SIZE_LABELS[-1]


# ── AST feature extraction ───────────────────────────────────────────────────

# Human-readable note per feature: what the construct usually means for
# byte-exactness, surfaced in the per-function verdict.
FEATURE_NOTES: dict[str, str] = {
    "many-locals>=10":
        "many named locals — PS source tends to reuse/inline; extra readable "
        "temporaries spill and shift regalloc. Try collapsing caches.",
    "ternary":
        "ternary `?:` — almost absent from the exact corpus EXCEPT the Rule 82 "
        "`x = c ? N : x` idiom; any other ternary is suspect.",
    "nested-ternary":
        "nested ternary — never in the corpus; unfold into if/else.",
    "switch":
        "switch — the exact corpus overwhelmingly uses if/else-if chains "
        "(Rule 95). PS may have been a chain, not a switch.",
    "goto":
        "goto — common as an epilogue funnel (Rule 92), but heavy goto webs "
        "correlate with residue; check the control-flow shape.",
    "deep-nest>=4":
        "deep nesting — mostly a size proxy; low size-controlled lift.",
    "cast":
        "explicit cast(s) — width/sign casts are codegen-relevant; spurious "
        "(char*)/(int) casts can change loads.",
    "compound-assign":
        "compound assignment — usually fine (Rule 91), low size-controlled lift.",
    "multi-return":
        "multiple return statements — usually fine; low lift.",
    "do-while":
        "do/while — Rule 93 placement; neutral on its own.",
    "assign-in-if":
        "assignment inside `if` — not observed in the corpus; split it out.",
    "comma-for-incr":
        "comma `for` increment — house style (Rule 79); neutral.",
    "shl1":
        "`x << 1` — Rule 62; check whether PS used `lea [x+x]` (`x + x`).",
    "while1":
        "`while (1)` — codegen-neutral vs `for (;;)`.",
    "register":
        "`register` keyword — Watcom 10.0a no-op; not in the corpus. Remove it.",
    "ptr-cache":
        "cached row/entity pointer used few times — Rules 63/73/74: PS often "
        "recomputes the index and folds global+field into disp32. Inline it.",
}


def _walk(n):
    yield n
    for _, c in n.children():
        if c is not None:
            yield from _walk(c)


def _is_ptr_cache_decl(d: c_ast.Decl) -> bool:
    """A local whose initializer takes an address or does pointer arithmetic:
    ``p = &arr[i]`` / ``p = base + i*stride`` / ``p = (T*)x``.  The "readable
    cache" smell (Rules 63/73/74)."""
    if d.init is None or not isinstance(d.type, c_ast.PtrDecl):
        return False
    init = d.init
    if isinstance(init, c_ast.UnaryOp) and init.op == "&":
        return True
    if isinstance(init, c_ast.Cast):
        return True
    if isinstance(init, c_ast.BinaryOp) and init.op in ("+", "-"):
        return True
    return False


def extract_features(func: c_ast.FuncDef) -> dict[str, int]:
    """Return ``{feature_token: count}`` for one function definition.

    Presence is what the model uses; counts are surfaced in the per-function
    breakdown.
    """
    feats: dict[str, int] = {}

    def bump(tok: str, n: int = 1) -> None:
        feats[tok] = feats.get(tok, 0) + n

    n_return = 0
    n_decl = 0
    n_init = 0
    max_nest = 0

    def nest(node, depth):
        nonlocal max_nest
        for _, c in node.children():
            if c is None:
                continue
            d = depth
            if isinstance(c, (c_ast.If, c_ast.For, c_ast.While,
                              c_ast.DoWhile, c_ast.Switch)):
                d = depth + 1
                max_nest = max(max_nest, d)
            nest(c, d)
    nest(func, 0)

    for n in _walk(func):
        if isinstance(n, c_ast.Return):
            n_return += 1
        elif isinstance(n, c_ast.Goto):
            bump("goto")
        elif isinstance(n, c_ast.DoWhile):
            bump("do-while")
        elif isinstance(n, c_ast.Switch):
            bump("switch")
        elif isinstance(n, c_ast.TernaryOp):
            bump("ternary")
            inner = list(_walk(n.iftrue)) + list(_walk(n.iffalse))
            if any(isinstance(x, c_ast.TernaryOp) for x in inner):
                bump("nested-ternary")
        elif isinstance(n, c_ast.If) and isinstance(n.cond, c_ast.Assignment):
            bump("assign-in-if")
        elif isinstance(n, c_ast.While) and _const_is(n.cond, "1"):
            bump("while1")
        elif isinstance(n, c_ast.For) and isinstance(n.next, c_ast.ExprList):
            bump("comma-for-incr")
        elif isinstance(n, c_ast.Cast):
            bump("cast")
        elif isinstance(n, c_ast.Assignment) and n.op != "=":
            bump("compound-assign")
        elif (isinstance(n, c_ast.BinaryOp) and n.op == "<<"
              and _const_is(n.right, "1")):
            bump("shl1")
        elif isinstance(n, c_ast.Decl):
            if "register" in (n.storage or []):
                bump("register")
            if _is_ptr_cache_decl(n):
                bump("ptr-cache")
            if isinstance(n.type, (c_ast.TypeDecl, c_ast.PtrDecl,
                                   c_ast.ArrayDecl)):
                n_decl += 1
                if n.init is not None:
                    n_init += 1

    if n_return > 1:
        bump("multi-return")
    if max_nest >= DEEP_NEST:
        bump("deep-nest>=4")
    if n_decl >= MANY_LOCALS:
        bump("many-locals>=10")
    return feats


def _const_is(node, value: str) -> bool:
    return isinstance(node, c_ast.Constant) and node.value.strip() == value


# ── Source index ─────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _source_index() -> dict[str, tuple[str, c_ast.FuncDef]]:
    index: dict[str, tuple[str, c_ast.FuncDef]] = {}
    if not SRC_DIR.is_dir():
        return index
    for cf in sorted(SRC_DIR.glob("*.c")):
        try:
            ast = parse_c(cf.read_text(encoding="utf-8", errors="replace"), cf.name)
        except Exception:
            continue
        for node in ast.ext:
            if isinstance(node, c_ast.FuncDef) and node.decl.name:
                index[node.decl.name] = (cf.name, node)
    return index


def invalidate_cache() -> None:
    _source_index.cache_clear()
    _build_model.cache_clear()


# ── The stratified lift model ────────────────────────────────────────────────

@dataclass
class FeatureStat:
    feature: str
    exact_with: int            # exact-corpus functions exhibiting it
    diff_with: int             # diffing functions exhibiting it
    n_exact: int
    n_diff: int
    enrichment: float          # raw diff-rate / exact-rate
    lift: float                # size-controlled (Mantel-Haenszel) lift
    expected_diff: float       # diffs expected from size strata of carriers

    @property
    def exact_pct(self) -> float:
        return 100.0 * self.exact_with / self.n_exact if self.n_exact else 0.0

    @property
    def diff_pct(self) -> float:
        return 100.0 * self.diff_with / self.n_diff if self.n_diff else 0.0


@dataclass
class Model:
    # name -> (features dict, size, is_diff)
    funcs: dict[str, tuple[dict[str, int], int, bool]]
    stats: dict[str, FeatureStat]
    # base diff-rate per size bucket
    base_rate: dict[str, float]
    bucket_pop: dict[str, int] = field(default_factory=dict)


# Re-entry guard: when the hint is rendered from INSIDE decomp-verify -v we
# must never trigger another verify pass (recursion / 30 s stall).
_in_verify_hint = False


@lru_cache(maxsize=2)
def _build_model_cached(rebuild: bool, from_path: Optional[str],
                        no_build: bool) -> Model:
    doc = get_verify_json(rebuild=rebuild,
                          from_path=Path(from_path) if from_path else None,
                          no_build=no_build)
    return _build_model_from_doc(doc)


def _build_model(*, rebuild: bool = False,
                 from_path: Optional[Path] = None,
                 no_build: bool = False) -> Model:
    return _build_model_cached(rebuild, str(from_path) if from_path else None,
                              no_build)


def _build_model_from_doc(doc: dict) -> Model:
    idx = _source_index()
    status = {f["name"]: int(f.get("diff_byte_count", 0) or 0)
              for f in doc.get("functions", [])}
    size = {f["name"]: int(f.get("size", 0) or 0)
            for f in doc.get("functions", [])}

    funcs: dict[str, tuple[dict[str, int], int, bool]] = {}
    for name, (_file, func) in idx.items():
        if name not in status:
            continue
        feats = extract_features(func)
        funcs[name] = (feats, size.get(name, 0), status[name] > 0)
    return compute_model(funcs)


def compute_model(
    funcs: dict[str, tuple[dict[str, int], int, bool]],
) -> Model:
    """Pure stratified-lift model from ``{name: (features, size, is_diff)}``.

    Separated from the source/verify plumbing so the lift math is unit-
    testable with synthetic populations (no Watcom container needed).
    """
    # Per-bucket base diff rate.
    bucket_total: dict[str, int] = {b: 0 for b in SIZE_LABELS}
    bucket_diff: dict[str, int] = {b: 0 for b in SIZE_LABELS}
    for _name, (_feats, sz, is_diff) in funcs.items():
        b = _size_bucket(sz)
        bucket_total[b] += 1
        if is_diff:
            bucket_diff[b] += 1
    base_rate = {b: (bucket_diff[b] / bucket_total[b]) if bucket_total[b] else 0.0
                 for b in SIZE_LABELS}

    n_exact = sum(1 for _f, _s, d in funcs.values() if not d)
    n_diff = sum(1 for _f, _s, d in funcs.values() if d)

    # Per-feature stratified lift.
    all_feats: set[str] = set()
    for feats, _s, _d in funcs.values():
        all_feats.update(feats)

    stats: dict[str, FeatureStat] = {}
    for feat in all_feats:
        ew = dw = 0
        expected = 0.0
        for _name, (feats, sz, is_diff) in funcs.items():
            if feat not in feats:
                continue
            if is_diff:
                dw += 1
            else:
                ew += 1
            expected += base_rate[_size_bucket(sz)]
        carriers = ew + dw
        exact_rate = ew / n_exact if n_exact else 0.0
        diff_rate = dw / n_diff if n_diff else 0.0
        enrichment = (diff_rate + 1e-9) / (exact_rate + 1e-9)
        lift = (dw / expected) if expected > 0 else float("inf") if dw else 0.0
        stats[feat] = FeatureStat(
            feature=feat, exact_with=ew, diff_with=dw,
            n_exact=n_exact, n_diff=n_diff,
            enrichment=enrichment, lift=lift, expected_diff=expected,
        )
    return Model(funcs=funcs, stats=stats, base_rate=base_rate,
                 bucket_pop=bucket_total)


# ── Scoring ──────────────────────────────────────────────────────────────────

@dataclass
class Flag:
    feature: str
    count: int
    exact_pct: float
    lift: float            # size-controlled lift (may be inf)
    note: str
    rules: list[str]       # anti-rule: positive rule numbers prescribing the fix
    anti_rule: str         # the anti-rule phrasing
    contrib: float         # this flag's contribution to the negative score

    @property
    def is_novel(self) -> bool:
        """High-lift construct with no catalogue rule → discovery candidate."""
        return (not self.rules) and (
            not math.isfinite(self.lift) or self.lift >= 1.5) \
            and self.exact_pct < 25.0


@dataclass
class FuncScore:
    name: str
    size: int
    is_diff: bool
    score: float
    flags: list[Flag]      # sorted by contribution desc


def _score_function(name: str, model: Model) -> Optional[FuncScore]:
    entry = model.funcs.get(name)
    if entry is None:
        return None
    feats, sz, is_diff = entry
    flags: list[Flag] = []
    score = 0.0
    for feat, cnt in feats.items():
        st = model.stats.get(feat)
        if st is None:
            continue
        # Contribution: log2 of the size-controlled lift, only when the
        # construct is genuinely enriched (lift > 1) AND rare in the exact
        # corpus (so common-but-neutral forms don't accumulate).
        lift = st.lift if math.isfinite(st.lift) else 8.0
        contrib = max(0.0, math.log2(lift)) if lift > 1.0 else 0.0
        # Down-weight features carried by most of the corpus (non-distinctive).
        rarity = 1.0 - (st.exact_with / st.n_exact if st.n_exact else 0.0)
        contrib *= rarity
        if contrib > 0:
            score += contrib
        rules, anti = feature_rules(feat)
        flags.append(Flag(
            feature=feat, count=cnt, exact_pct=st.exact_pct, lift=st.lift,
            note=FEATURE_NOTES.get(feat, ""), rules=rules, anti_rule=anti,
            contrib=round(contrib, 3),
        ))
    flags.sort(key=lambda f: -f.contrib)
    return FuncScore(name=name, size=sz, is_diff=is_diff,
                     score=round(score, 3), flags=flags)


# ── Public API ───────────────────────────────────────────────────────────────

def feature_table(model: Model) -> list[FeatureStat]:
    """All feature stats, ranked by size-controlled lift descending."""
    return sorted(
        model.stats.values(),
        key=lambda s: (-(s.lift if math.isfinite(s.lift) else 1e9), -s.diff_with),
    )


def rank_functions(model: Model, *, include_exact: bool = False) -> list[FuncScore]:
    out = []
    for name, (_f, _s, is_diff) in model.funcs.items():
        if not include_exact and not is_diff:
            continue
        fs = _score_function(name, model)
        if fs is not None:
            out.append(fs)
    out.sort(key=lambda f: (-f.score, -f.size, f.name))
    return out


def render_negative_hint(name: str, *, max_flags: int = 2,
                         min_score: float = 0.3) -> list[str]:
    """Compact lines for decomp-verify -v: the top score-driving rare
    constructs (the ones that make this function look un-PS-like), each with
    its anti-rule pointer (or NOVEL when the catalogue has none)."""
    if _in_verify_hint:
        return []
    try:
        model = _build_model(no_build=True)
    except Exception:
        return []
    fs = _score_function(name, model)
    if fs is None or fs.score < min_score:
        return []
    # Flags that actually drive the score AND are rare in the exact corpus
    # (so we point at genuinely un-PS-like constructs, not common-but-neutral).
    picks = [f for f in fs.flags
             if f.contrib > 0 and f.exact_pct < 25.0][:max_flags]
    if not picks:
        return []
    parts = []
    for f in picks:
        lifts = "∞" if not math.isfinite(f.lift) else f"{f.lift:.1f}x"
        ar = ("Rule " + "/".join(f.rules)) if f.rules else "NOVEL"
        parts.append(f"{f.feature} (exact {f.exact_pct:.0f}%, lift {lifts} → {ar})")
    return [f"  [magenta]Neg-corpus[/]: score {fs.score:.1f} — " + "; ".join(parts)]


def negative_to_json(name: str) -> Optional[dict]:
    try:
        model = _build_model(no_build=True)
    except Exception:
        return None
    fs = _score_function(name, model)
    if fs is None:
        return None
    return {
        "name": fs.name, "size": fs.size, "diff": fs.is_diff,
        "score": fs.score,
        "flags": [
            {"feature": f.feature, "count": f.count,
             "exact_pct": round(f.exact_pct, 1),
             "lift": (None if not math.isfinite(f.lift) else round(f.lift, 2)),
             "contrib": f.contrib,
             "rules": f.rules, "anti_rule": f.anti_rule,
             "novel": f.is_novel, "note": f.note}
            for f in fs.flags
        ],
    }


# ── CLI ──────────────────────────────────────────────────────────────────────

def negative_corpus(
    name: Optional[str] = typer.Argument(
        None, help="Function name for a per-function breakdown. "
                   "Omit for the corpus-wide table + ranked list."),
    rebuild: bool = typer.Option(
        False, "--rebuild", help="Force a fresh decomp-verify --json pass."),
    from_json: Optional[Path] = typer.Option(
        None, "--from-json", help="Use a cached decomp-verify --json blob."),
    include_exact: bool = typer.Option(
        False, "--all", help="Include byte-exact functions in the ranked list."),
    limit: int = typer.Option(
        30, "--limit", "-n", help="Rows in the ranked list (0 = all)."),
    min_lift: float = typer.Option(
        1.0, "--min-lift",
        help="Hide features whose size-controlled lift is below this in the "
             "feature table."),
    json_out: bool = typer.Option(False, "--json", help="JSON output."),
) -> None:
    """Source-shape forms that correlate with NOT being byte-exact."""
    model = _build_model(rebuild=rebuild, from_path=from_json)

    if name is not None:
        fs = _score_function(name, model)
        if fs is None:
            typer.echo(f"no source for {name!r} (or not in the verify set)", err=True)
            raise typer.Exit(1)
        if json_out:
            typer.echo(json.dumps(negative_to_json(name), indent=2))
            return
        b = _size_bucket(fs.size)
        verdict = "diffing" if fs.is_diff else "byte-exact"
        typer.echo(f"\n{fs.name}  ({fs.size} b, bucket {b}, {verdict})")
        typer.echo(f"  negative score: {fs.score}")
        if not fs.flags:
            typer.echo("  no notable source-shape constructs")
            return
        typer.echo(f"  {'construct':18s} {'cnt':>3s} {'exact%':>7s} "
                   f"{'lift':>6s}  anti-rule")
        for f in fs.flags:
            lifts = "∞" if not math.isfinite(f.lift) else f"{f.lift:.1f}x"
            ar = (", ".join("Rule " + r for r in f.rules) if f.rules
                  else ("⚠ NOVEL (no catalogue rule)" if f.is_novel else "—"))
            typer.echo(f"  {f.feature:18s} {f.count:3d} {f.exact_pct:6.1f}% "
                       f"{lifts:>6s}  {ar}")
        # The anti-rule prose for the top flags.
        typer.echo("")
        for f in fs.flags[:3]:
            if f.contrib <= 0 and not f.is_novel:
                continue
            tag = "⚠ NOVEL" if f.is_novel else (
                ", ".join(rule_label(r) for r in f.rules) if f.rules else "")
            typer.echo(f"  • {f.feature}: {f.anti_rule}")
            if tag and f.rules:
                for r in f.rules[:3]:
                    typer.echo(f"      → {rule_label(r)}")
        return

    if json_out:
        typer.echo(json.dumps({
            "base_rate": {b: round(r, 4) for b, r in model.base_rate.items()},
            "bucket_pop": model.bucket_pop,
            "features": [
                {"feature": s.feature, "exact_with": s.exact_with,
                 "diff_with": s.diff_with, "exact_pct": round(s.exact_pct, 1),
                 "diff_pct": round(s.diff_pct, 1),
                 "enrichment": round(s.enrichment, 2),
                 "lift": (None if not math.isfinite(s.lift) else round(s.lift, 2)),
                 "rules": feature_rules(s.feature)[0],
                 "novel": (not feature_rules(s.feature)[0])
                 and (not math.isfinite(s.lift) or s.lift >= 1.5)
                 and s.exact_pct < 25}
                for s in feature_table(model)
            ],
            "functions": [
                {"name": f.name, "size": f.size, "diff": f.is_diff,
                 "score": f.score,
                 "flags": [ff.feature for ff in f.flags],
                 "novel_flags": [ff.feature for ff in f.flags if ff.is_novel]}
                for f in rank_functions(model, include_exact=include_exact)
            ],
        }, indent=2))
        return

    # Corpus feature table.
    typer.echo("Size buckets (base diff-rate):  " + "  ".join(
        f"{b} {100*model.base_rate[b]:.0f}% (n={model.bucket_pop[b]})"
        for b in SIZE_LABELS))
    typer.echo("\n=== source-shape features: exact% vs diff% (raw), "
               "size-controlled lift, and the anti-rule oracle ===")
    typer.echo(f"  {'feature':18s} {'exact%':>7s} {'diff%':>7s} "
               f"{'enrich':>7s} {'lift*':>6s}  anti-rule  (*=size-controlled)")
    novel_feats: list[FeatureStat] = []
    for s in feature_table(model):
        if math.isfinite(s.lift) and s.lift < min_lift:
            continue
        lifts = "∞" if not math.isfinite(s.lift) else f"{s.lift:.2f}"
        rules, _ = feature_rules(s.feature)
        suspect = (not math.isfinite(s.lift) or s.lift >= 1.5) and s.exact_pct < 25
        if rules:
            ar = "Rule " + "/".join(rules)
        elif suspect:
            ar = "⚠ NOVEL"
            novel_feats.append(s)
        else:
            ar = "—"
        typer.echo(f"  {s.feature:18s} {s.exact_pct:6.1f}% {s.diff_pct:6.1f}% "
                   f"{s.enrichment:6.1f}x {lifts:>6s}  {ar}")

    if novel_feats:
        typer.echo("\n=== novel anti-rule candidates (high size-controlled "
                   "lift, NO catalogue rule) ===")
        for s in novel_feats:
            _, anti = feature_rules(s.feature)
            lifts = "∞" if not math.isfinite(s.lift) else f"{s.lift:.1f}x"
            typer.echo(f"  {s.feature}  (exact {s.exact_pct:.1f}%, lift {lifts}) "
                       f"— {anti or 'no oracle note; investigate'}")

    ranked = rank_functions(model, include_exact=include_exact)
    if limit:
        ranked = ranked[:limit]
    typer.echo(f"\n=== {'all functions' if include_exact else 'diffing functions'} "
               f"ranked by negative score ===")
    typer.echo(f"  {'score':>5s} {'size':>5s}  name  ⟵ top suspects (→ anti-rule)")
    for f in ranked:
        susp_parts = []
        for ff in f.flags:
            if ff.contrib <= 0 and not ff.is_novel:
                continue
            ar = ("R" + "/".join(ff.rules)) if ff.rules else (
                "NOVEL" if ff.is_novel else "")
            susp_parts.append(f"{ff.feature}" + (f"→{ar}" if ar else ""))
        susp = ", ".join(susp_parts)[:64]
        typer.echo(f"  {f.score:5.1f} {f.size:5d}  {f.name}"
                   + (f"  ⟵ {susp}" if susp else ""))

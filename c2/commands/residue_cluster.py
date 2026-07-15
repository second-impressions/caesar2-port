"""Residue clustering — group diffing functions by machine-level diff shape.

Instead of treating each of the ~350 remaining diffing functions as an
isolated mystery, this clusters them by the *character* of their residue.
The premise (validated on the current corpus): there are not 350 distinct
problems, there are ~20-70 **residue families**, and a single source lever
usually fixes a whole family at once.

Signature
---------
Each diffing function is reduced to a feature multiset built from the
``decomp-verify --json`` record — deliberately from the **trustworthy,
context-aware** signals, not raw byte deltas:

  * ``hint:Rule N`` / ``hint:Reg swap`` … — the ``rule_hints`` histogram.
    These are the curated classifiers; they already abstract instruction
    selection / regalloc far better than raw mnemonic pairs (which are
    polluted by diff-misalignment once a size change shifts the stream).
  * ``tailmerge`` — is this a tail-merge dependent (blocked on a donor).
  * ``pragma:<category>`` — prologue-divergence class (extra callee-save,
    callee-save swap, structural, stack spill).
  * ``size_differs`` — whole-function size mismatch (layout/encoding cascade).
  * ``shape:{aligned,mixed,cascade}`` — fraction of diff rows that are
    insert/delete (a size-changing divergence cascades into alignment
    noise) vs clean 1:1 replaces (true regalloc residue).
  * ``mag:{tiny,small,med,large}`` — diff-byte magnitude bucket.

Features are IDF-weighted (so the near-universal ``Reg swap`` does not
dominate) and functions are grouped by **leader clustering**: a deterministic
threshold-based single-pass agglomeration (no ``k``, no sklearn) that yields
explainable families labelled by their shared high-IDF features.

Anti-rule oracle
----------------
Each family is then run through ``anti_rules.classify_family_coverage``:

  * **known**  — a numbered rule covers the family ⇒ a prescribed source fix
    exists; the family is a *known anti-rule family*, fix the representative
    and batch the lever across members.
  * **novel**  — the family carries only the generic register-swap
    classifiers (or no hints) ⇒ the catalogue has no explanation ⇒ this is a
    **novel anti-rule discovery candidate**: the highest-value place to mine
    a new rule, because solving the small representative generalizes to the
    whole cluster.
"""

from __future__ import annotations

import json
import math
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import typer

from c2.commands.verify_json import get_verify_json
from c2.commands.anti_rules import classify_family_coverage, rule_label

DEFAULT_THRESHOLD = 0.62


# ── signature ────────────────────────────────────────────────────────────────

def _shape(rows: list[dict]) -> str:
    ins = de = re_ = 0
    for r in rows:
        k = r.get("kind")
        if k == "insert":
            ins += 1
        elif k == "delete":
            de += 1
        elif k == "replace":
            re_ += 1
    tot = ins + de + re_
    if tot == 0:
        return "none"
    cascade = (ins + de) / tot
    if cascade < 0.15:
        return "aligned"
    if cascade > 0.60:
        return "cascade"
    return "mixed"


def _mag(n: int) -> str:
    if n <= 4:
        return "tiny"
    if n <= 16:
        return "small"
    if n <= 64:
        return "med"
    return "large"


def signature(fn: dict) -> Counter:
    """Feature multiset for one diffing-function verify record."""
    feats: Counter = Counter()
    for rule, cnt in (fn.get("rule_hints") or {}).items():
        feats["hint:" + rule] += 1
    if fn.get("tail_merge"):
        feats["tailmerge"] += 1
    ph = fn.get("pragma_hint")
    if ph:
        feats["pragma:" + ph.get("category", "?")] += 1
    if fn.get("size_differs"):
        feats["size_differs"] += 1
    feats["shape:" + _shape(fn.get("rows") or [])] += 1
    feats["mag:" + _mag(int(fn.get("diff_byte_count", 0) or 0))] += 1
    return feats


# ── model ────────────────────────────────────────────────────────────────────

@dataclass
class Cluster:
    cid: int
    members: list[str]
    label: list[tuple[str, int]]    # (feature, member-count) shared by >=50%
    rep: str                        # representative (smallest diff) member
    coverage: str                   # 'known' | 'partial' | 'novel'
    known_rules: list[str]
    hint_names: set[str] = field(default_factory=set)

    @property
    def size(self) -> int:
        return len(self.members)


@dataclass
class ClusterModel:
    clusters: list[Cluster]
    sig: dict[str, Counter]
    diff_bytes: dict[str, int]
    func_size: dict[str, int]
    file_of: dict[str, str]
    idf: dict[str, float]
    threshold: float
    shape_distance: dict[str, dict] = None   # name -> shape_distance dict

    def cluster_of(self, name: str) -> Optional[Cluster]:
        for c in self.clusters:
            if name in c.members:
                return c
        return None


def _cos(a: dict[str, float], b: dict[str, float]) -> float:
    common = set(a) & set(b)
    if not common:
        return 0.0
    num = sum(a[k] * b[k] for k in common)
    da = math.sqrt(sum(v * v for v in a.values()))
    db = math.sqrt(sum(v * v for v in b.values()))
    return num / (da * db) if da and db else 0.0


def build_model(doc: dict, *, threshold: float = DEFAULT_THRESHOLD) -> ClusterModel:
    diff = [f for f in doc.get("functions", [])
            if int(f.get("diff_byte_count", 0) or 0) > 0]
    sig = {f["name"]: signature(f) for f in diff}
    diff_bytes = {f["name"]: int(f.get("diff_byte_count", 0) or 0) for f in diff}
    func_size = {f["name"]: int(f.get("size", 0) or 0) for f in diff}
    file_of = {f["name"]: f.get("file", "") for f in diff}
    hint_names = {f["name"]: set((f.get("rule_hints") or {}).keys()) for f in diff}
    shape_dist = {f["name"]: (f.get("shape_distance") or {}) for f in diff}

    n = len(sig)
    df: Counter = Counter()
    for c in sig.values():
        for k in c:
            df[k] += 1
    idf = {k: math.log(n / v) for k, v in df.items()} if n else {}

    def vec(name: str) -> dict[str, float]:
        return {k: idf.get(k, 0.0) for k in sig[name]}

    vecs = {name: vec(name) for name in sig}

    # Leader clustering: deterministic order by descending vector weight.
    def weight(name: str) -> float:
        return sum(vecs[name].values())

    order = sorted(sig, key=lambda nm: (-weight(nm), nm))
    assigned: set[str] = set()
    raw_clusters: list[list[str]] = []
    for leader in order:
        if leader in assigned:
            continue
        members = [leader]
        assigned.add(leader)
        for other in order:
            if other in assigned:
                continue
            if _cos(vecs[leader], vecs[other]) >= threshold:
                members.append(other)
                assigned.add(other)
        raw_clusters.append(members)

    raw_clusters.sort(key=lambda m: (-len(m),
                                     min(diff_bytes[x] for x in m)))

    clusters: list[Cluster] = []
    for cid, members in enumerate(raw_clusters):
        fc: Counter = Counter()
        for m in members:
            for k in sig[m]:
                fc[k] += 1
        half = len(members) / 2
        label = sorted(
            ((k, fc[k]) for k in fc if fc[k] >= half),
            key=lambda kv: (-idf.get(kv[0], 0.0), -kv[1]),
        )[:8]
        rep = min(members, key=lambda x: (diff_bytes[x], func_size.get(x, 0), x))
        # Union of rule-hint names that the cluster's >=50% label carries —
        # but coverage is judged on the union of member hints (any rule that
        # explains the family).
        fam_hints: set[str] = set()
        for m in members:
            fam_hints |= hint_names[m]
        # Keep only hints carried by a meaningful share (>=33%) so a single
        # outlier member doesn't make a Reg-swap family look "known".
        share: Counter = Counter()
        for m in members:
            for h in hint_names[m]:
                share[h] += 1
        dominant = {h for h, c in share.items() if c >= max(1, len(members) // 3)}
        coverage, known_rules = classify_family_coverage(dominant)
        clusters.append(Cluster(
            cid=cid, members=members, label=label, rep=rep,
            coverage=coverage, known_rules=known_rules, hint_names=dominant,
        ))

    return ClusterModel(
        clusters=clusters, sig=sig, diff_bytes=diff_bytes,
        func_size=func_size, file_of=file_of, idf=idf, threshold=threshold,
        shape_distance=shape_dist,
    )


def _shape_cell(model: ClusterModel, name: str) -> str:
    """Compact per-fn shape-distance cell (`ir{N}/{T}[+k]→fix_next`) for a
    residue-cluster member/representative -- the per-function judge metric,
    in place of the bar a byte count used to fill."""
    sd = (model.shape_distance or {}).get(name) or {}
    if not sd:
        return "-"
    ir = sd.get("ir", 0); irt = sd.get("ir_total", 0)
    extra = sum(1 for L in ("width", "spill", "seat") if sd.get(L, 0))
    base = (f"ir{ir}/{irt}" if irt else f"ir{ir}") + (f"+{extra}" if extra else "")
    return f"{base}→{sd.get('fix_next', '?')}"


def _label_str(label: list[tuple[str, int]]) -> str:
    return " ".join(f"{k}({c})" for k, c in label)


# ── CLI ──────────────────────────────────────────────────────────────────────

def residue_cluster(
    name: Optional[str] = typer.Argument(
        None, help="Function name: show which family it belongs to. "
                   "Omit for the family list."),
    cluster: Optional[int] = typer.Option(
        None, "--cluster", "-c", help="Show all members of one cluster id."),
    rebuild: bool = typer.Option(
        False, "--rebuild", help="Force a fresh decomp-verify --json pass."),
    from_json: Optional[Path] = typer.Option(
        None, "--from-json", help="Use a cached decomp-verify --json blob."),
    threshold: float = typer.Option(
        DEFAULT_THRESHOLD, "--threshold", "-t",
        help="Cosine similarity threshold for leader clustering (0-1)."),
    min_size: int = typer.Option(
        1, "--min-size", help="Hide clusters smaller than this."),
    novel_only: bool = typer.Option(
        False, "--novel", help="Show only novel anti-rule candidate families."),
    limit: int = typer.Option(
        40, "--limit", "-n", help="Max clusters/members to print (0 = all)."),
    json_out: bool = typer.Option(False, "--json", help="JSON output."),
) -> None:
    """Cluster diffing functions by machine-level residue signature."""
    doc = get_verify_json(rebuild=rebuild, from_path=from_json)
    model = build_model(doc, threshold=threshold)

    # ── one function: which family? ──
    if name is not None:
        c = model.cluster_of(name)
        if c is None:
            typer.echo(f"{name!r} is not in the diffing set (byte-exact or "
                       f"not found)", err=True)
            raise typer.Exit(1)
        if json_out:
            typer.echo(json.dumps(_cluster_json(c, model), indent=2))
            return
        typer.echo(f"\n{name}  →  cluster #{c.cid}  (n={c.size}, "
                   f"coverage={c.coverage})")
        typer.echo(f"  signature: {_label_str(c.label)}")
        typer.echo(f"  this fn:   {dict(model.sig[name])}")
        _print_coverage(c)
        typer.echo(f"  representative: {c.rep}  [{_shape_cell(model, c.rep)}]")
        return

    # ── one cluster's members ──
    if cluster is not None:
        c = next((x for x in model.clusters if x.cid == cluster), None)
        if c is None:
            typer.echo(f"no cluster #{cluster}", err=True)
            raise typer.Exit(1)
        if json_out:
            typer.echo(json.dumps(_cluster_json(c, model), indent=2))
            return
        typer.echo(f"\ncluster #{c.cid}  (n={c.size}, coverage={c.coverage})")
        typer.echo(f"  signature: {_label_str(c.label)}")
        _print_coverage(c)
        typer.echo(f"\n  {'shape':>16s}  {'name':32s} file")
        for m in sorted(c.members, key=lambda x: -int((model.shape_distance or {}).get(x, {}).get('total', 0))):
            mark = "★" if m == c.rep else " "
            typer.echo(f" {mark}{_shape_cell(model, m):>16s}  {m:32s} "
                      f"{model.file_of.get(m,'')}")
        return

    # ── family list ──
    clusters = [c for c in model.clusters if c.size >= min_size]
    if novel_only:
        clusters = [c for c in clusters if c.coverage == "novel"]

    if json_out:
        typer.echo(json.dumps({
            "threshold": model.threshold,
            "n_diffing": len(model.sig),
            "n_clusters": len(model.clusters),
            "clusters": [_cluster_json(c, model) for c in clusters],
        }, indent=2))
        return

    n_novel = sum(1 for c in model.clusters if c.coverage == "novel")
    typer.echo(f"{len(model.clusters)} residue families from {len(model.sig)} "
               f"diffing functions (threshold={model.threshold}); "
               f"{n_novel} novel anti-rule candidate families")
    typer.echo(f"\n  {'#':>3s} {'n':>3s} {'cover':7s} {'rep':28s} "
               f"{'rep_shape':>16s}  signature / anti-rule")
    shown = clusters[:limit] if limit else clusters
    for c in shown:
        cover = {"known": "KNOWN", "partial": "part.", "novel": "NOVEL"}[c.coverage]
        if c.coverage in ("known", "partial") and c.known_rules:
            anti = "→ Rule " + "/".join(c.known_rules[:4])
        elif c.coverage == "novel":
            anti = "⚠ novel candidate"
        else:
            anti = ""
        typer.echo(f"  {c.cid:3d} {c.size:3d} {cover:7s} {c.rep:28.28s} "
                   f"{_shape_cell(model, c.rep):>16s}  {_label_str(c.label)[:48]}  {anti}")

    typer.echo("\nUse `c2 residue-cluster -c <#>` for members, "
               "`--novel` for discovery candidates, "
               "`c2 negative-corpus <rep>` for the source-shape view.")


def _print_coverage(c: Cluster) -> None:
    if c.coverage == "novel":
        typer.echo("  coverage: ⚠ NOVEL anti-rule candidate — only generic "
                   "register-swap classifiers / no numbered rule explains this "
                   "family. Solve the representative to mine a new rule.")
    elif c.known_rules:
        verb = "covered by" if c.coverage == "known" else "partially covered by"
        typer.echo(f"  coverage: {verb} the catalogue:")
        for r in c.known_rules[:6]:
            typer.echo(f"      → {rule_label(r)}")


def _cluster_json(c: Cluster, model: ClusterModel) -> dict:
    return {
        "cid": c.cid,
        "size": c.size,
        "coverage": c.coverage,
        "known_rules": c.known_rules,
        "dominant_hints": sorted(c.hint_names),
        "label": [{"feature": k, "count": v} for k, v in c.label],
        "representative": c.rep,
        "members": [
            {"name": m, "diff_bytes": model.diff_bytes[m],
             "size": model.func_size.get(m, 0), "file": model.file_of.get(m, "")}
            for m in sorted(c.members, key=lambda x: model.diff_bytes[x])
        ],
    }

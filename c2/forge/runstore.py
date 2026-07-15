"""RunStore -- persistent, reconstructable forge-run artifacts.

Every ``forge run`` / ``forge climb`` / ``forge sweep`` search burns
real compute; before 2026-07-05 the only surviving output was the
top-N winner patches -- every other tried permutation (and the whole
search TREE a climb walked) evaporated with the process.  The
RunStore keeps them, WITHOUT storing per-variant source copies:

  * ``baseline.c``     -- the exact source the run started from.
  * ``results.jsonl``  -- one line per SCORED plan: candidate names,
    the TextEdits (start/end/replacement vs the baseline), and both
    judges (bytes + layer vector).  A variant's full source -- and
    hence its unified diff -- is RECONSTRUCTED offline from
    baseline.c + edits; nothing is recompiled.
  * ``tree.json`` -- the climb search tree: every ACCEPTED state and
    every logged CHILD (evaluated but not necessarily taken), each as
    edits vs its parent.  Any node's full text is reconstructed by
    walking the edit chain from baseline.c -- no per-node source
    copies are kept.  The "different wins and trees we went down".
  * ``winners/NN.*.patch`` -- ready-to-apply unified diffs of the top
    improving plans.
  * ``run.json``       -- metadata: function, file, kind, config, git
    head, baseline scores, final summary, timing.

Layout::

    .c2-cache/forge-runs/
        index.jsonl                    # one line per finished run
        <function>/<ts>-<kind>/        # one run
            run.json  baseline.c  results.jsonl  tree.json
            winners/*.patch

Reader API: :func:`list_runs`, :func:`resolve`, :func:`load_meta`,
:func:`iter_results`, :func:`reconstruct_text`, :func:`diff_for`.
"""

from __future__ import annotations

import difflib
import json
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator


DEFAULT_ROOT = Path(".c2-cache/forge-runs")


def _git_head() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5,
        ).stdout.strip()
    except Exception:                       # noqa: BLE001
        return ""


def _edits_of(plan) -> list[list]:
    """Flatten an EditPlan's TextEdits to JSON-able [start, end, repl]."""
    out = []
    for c in plan.candidates:
        for e in c.edits:
            out.append([e.start, e.end, e.replacement])
    return out


def apply_edits(text: str, edits: list[list]) -> str:
    """Re-apply stored [start, end, repl] edits (same reverse-offset +
    deterministic tie-break order as ``EditPlan.apply``)."""
    for s, e, r in sorted(edits, key=lambda x: (-x[0], -x[1], x[2])):
        text = text[:s] + r + text[e:]
    return text


@dataclass
class RunStore:
    """Append-only artifact writer for ONE run."""

    dir: Path
    meta: dict[str, Any] = field(default_factory=dict)
    _results_fh: Any = None
    _tree: list[dict] = field(default_factory=list)
    _n_results: int = 0


    @classmethod
    def create(cls, function: str, file: str, kind: str,
               baseline_text: str, config: dict | None = None,
               root: Path | str | None = None) -> "RunStore":
        root = Path(root) if root else DEFAULT_ROOT
        ts = time.strftime("%Y%m%d-%H%M%S")
        d = root / function / f"{ts}-{kind}"
        n = 1
        while d.exists():                   # same-second re-run
            n += 1
            d = root / function / f"{ts}-{kind}-{n}"
        d.mkdir(parents=True)
        (d / "baseline.c").write_text(baseline_text)
        store = cls(dir=d, meta={
            "function": function,
            "file": file,
            "kind": kind,
            "config": config or {},
            "git_head": _git_head(),
            "started": time.strftime("%Y-%m-%d %H:%M:%S"),
        })
        store._write_meta()
        return store

    def _write_meta(self) -> None:
        (self.dir / "run.json").write_text(json.dumps(self.meta, indent=2))


    def set_baseline(self, score) -> None:
        self.meta["baseline"] = _score_dict(score)
        self._write_meta()

    def log_result(self, plan, score, *, node: str | None = None) -> None:
        """One scored plan (run mode) or child expansion (climb mode,
        with ``node`` = the parent tree-node id the edits apply to)."""
        if self._results_fh is None:
            self._results_fh = open(self.dir / "results.jsonl", "a")
        rec = {
            "id": plan.fingerprint,
            "plan": plan.name,
            "cands": [c.name for c in plan.candidates],
            "edits": _edits_of(plan),
            **_score_dict(score),
        }
        if node:
            rec["node"] = node
        self._results_fh.write(json.dumps(rec,
                                          separators=(",", ":")) + "\n")
        self._n_results += 1
        if self._n_results % 64 == 0:
            self._results_fh.flush()


    def log_node(self, node_id: str, *, parent: str | None, round_: int,
                 plan=None, score=None, accepted: bool,
                 reason: str = "") -> None:
        """One tree node: edits vs its parent + judges.  Full text is
        never stored -- reconstruct by walking the edit chain from
        baseline.c (:func:`reconstruct_text`)."""
        rec: dict[str, Any] = {
            "id": node_id, "parent": parent, "round": round_,
            "accepted": accepted, "reason": reason,
        }
        if plan is not None:
            rec["plan"] = plan.name
            rec["cands"] = [c.name for c in plan.candidates]
            rec["edits"] = _edits_of(plan)
        if score is not None:
            rec.update(_score_dict(score))
        self._tree.append(rec)
        (self.dir / "tree.json").write_text(
            json.dumps(self._tree, indent=1))


    def write_winner(self, rank: int, plan, score,
                     base_text: str, file_label: str) -> Path:
        wd = self.dir / "winners"
        wd.mkdir(exist_ok=True)
        short = "".join(ch if ch.isalnum() or ch in "+_-." else "_"
                        for ch in plan.name)[:64]
        stem = f"{rank:02d}.{short}.bytes{score.bytes}"
        new_text = plan.apply(base_text)
        diff = "".join(difflib.unified_diff(
            base_text.splitlines(keepends=True),
            new_text.splitlines(keepends=True),
            fromfile=f"decomp/src/{file_label}",
            tofile=f"decomp/src/{file_label}  (forge: {plan.name})",
            n=3,
        ))
        p = wd / f"{stem}.patch"
        p.write_text(diff)
        return p


    def finalize(self, **summary: Any) -> Path:
        self.meta["finished"] = time.strftime("%Y-%m-%d %H:%M:%S")
        self.meta["summary"] = summary
        self._write_meta()
        if self._results_fh is not None:
            self._results_fh.close()
            self._results_fh = None
        # index line for `c2 forge runs`
        root = self.dir.parent.parent
        try:
            with open(root / "index.jsonl", "a") as fh:
                fh.write(json.dumps({
                    "dir": str(self.dir.relative_to(root)),
                    "function": self.meta.get("function"),
                    "file": self.meta.get("file"),
                    "kind": self.meta.get("kind"),
                    "started": self.meta.get("started"),
                    "baseline": self.meta.get("baseline", {}),
                    "summary": summary,
                }, separators=(",", ":")) + "\n")
        except Exception:                   # noqa: BLE001
            pass
        return self.dir


def _score_dict(score) -> dict[str, Any]:
    return {
        "ok": score.ok,
        "bytes": score.bytes,
        "layers": list(score.layers),
        "fix_next": score.fix_next,
        **({"error": score.error} if score.error else {}),
    }


def list_runs(function: str | None = None,
              root: Path | str | None = None) -> list[dict]:
    """Every stored run (newest first), optionally filtered."""
    root = Path(root) if root else DEFAULT_ROOT
    out: list[dict] = []
    if not root.exists():
        return out
    for meta_path in root.glob("*/*/run.json"):
        try:
            meta = json.loads(meta_path.read_text())
        except Exception:                   # noqa: BLE001
            continue
        if function and meta.get("function") != function:
            continue
        meta["dir"] = str(meta_path.parent)
        out.append(meta)
    out.sort(key=lambda m: m.get("started", ""), reverse=True)
    return out


def resolve(selector: str, root: Path | str | None = None) -> Path:
    """Resolve a run selector: a run dir path, a ``fn/ts-kind`` id, a
    bare function name (its LATEST run), or a unique prefix."""
    root = Path(root) if root else DEFAULT_ROOT
    p = Path(selector)
    if p.is_dir() and (p / "run.json").exists():
        return p
    cand = root / selector
    if cand.is_dir() and (cand / "run.json").exists():
        return cand
    runs = list_runs(root=root)
    by_fn = [r for r in runs if r.get("function") == selector]
    if by_fn:
        return Path(by_fn[0]["dir"])
    pref = [r for r in runs
            if Path(r["dir"]).name.startswith(selector)
            or r["dir"].endswith(selector)]
    if len(pref) == 1:
        return Path(pref[0]["dir"])
    raise FileNotFoundError(
        f"no unique forge run matches {selector!r} "
        f"({len(pref)} prefix matches, {len(runs)} runs total)")


def load_meta(run_dir: Path) -> dict:
    return json.loads((Path(run_dir) / "run.json").read_text())


def iter_results(run_dir: Path) -> Iterator[dict]:
    p = Path(run_dir) / "results.jsonl"
    if not p.exists():
        return
    with open(p) as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


def load_tree(run_dir: Path) -> list[dict]:
    p = Path(run_dir) / "tree.json"
    return json.loads(p.read_text()) if p.exists() else []


def _node_text(run_dir: Path, node_id: str | None) -> str:
    """Full source text of any tree node, reconstructed by walking the
    edit chain from baseline.c (legacy runs' ``nodes/<id>.c`` copies
    are honoured when present)."""
    run_dir = Path(run_dir)
    if node_id in (None, "", "baseline"):
        return (run_dir / "baseline.c").read_text()
    p = run_dir / "nodes" / f"{node_id}.c"
    if p.exists():                          # legacy (pre 2026-07-05) runs
        return p.read_text()
    for rec in load_tree(run_dir):
        if rec["id"] == node_id:
            parent = _node_text(run_dir, rec.get("parent"))
            if rec.get("edits"):
                return apply_edits(parent, rec["edits"])
            return parent                   # edit-less node (baseline root)
    raise KeyError(f"node {node_id!r} not in run tree")


def reconstruct_text(run_dir: Path, item_id: str) -> tuple[str, str, dict]:
    """(base_text, variant_text, record) for a result plan-id or a
    tree node-id.  Pure offline reconstruction -- no recompile."""
    run_dir = Path(run_dir)
    # 1. tree node?
    for rec in load_tree(run_dir):
        if rec["id"] == item_id:
            parent_text = _node_text(run_dir, rec.get("parent"))
            if rec.get("edits"):
                return parent_text, apply_edits(parent_text,
                                                rec["edits"]), rec
            return parent_text, parent_text, rec
    # 2. scored plan (results.jsonl; edits vs the plan's node or baseline)
    for rec in iter_results(run_dir):
        if rec["id"] == item_id or rec["id"].startswith(item_id):
            base = _node_text(run_dir, rec.get("node"))
            return base, apply_edits(base, rec["edits"]), rec
    raise KeyError(f"{item_id!r} not found in {run_dir}")


def diff_for(run_dir: Path, item_id: str, *, context: int = 3,
             against_baseline: bool = True) -> str:
    """Unified diff for any tried permutation or tree node.

    ``against_baseline=True`` diffs vs the RUN's baseline source (the
    cumulative view); ``False`` diffs vs the item's immediate parent
    (the incremental step).
    """
    run_dir = Path(run_dir)
    base, variant, rec = reconstruct_text(run_dir, item_id)
    if against_baseline:
        base = (run_dir / "baseline.c").read_text()
    label = rec.get("plan") or rec.get("id")
    meta = load_meta(run_dir)
    file = meta.get("file", "?")
    hdr = (f"# {meta.get('function')}  [{rec.get('id')}]  "
           f"bytes={rec.get('bytes')}  layers={rec.get('layers')}\n")
    return hdr + "".join(difflib.unified_diff(
        base.splitlines(keepends=True),
        variant.splitlines(keepends=True),
        fromfile=f"decomp/src/{file}",
        tofile=f"decomp/src/{file}  ({label})",
        n=context,
    ))

"""Per-agent sandbox lifecycle.

Each agent runs against a workspace with this layout::

    <runs_root>/<fn-slug>-<short-ts>/        ← orchestrator-owned, the "run dir"
    ├── meta.json                            ← function/target/cflags/etc.
    ├── history.jsonl                        ← every tool call + verify
    ├── transcript.jsonl                     ← model messages (pydantic-ai)
    ├── best/                                ← orchestrator-owned best-snapshot
    │   ├── scratch.c
    │   └── verify.json
    └── work/                                ← THE SANDBOX (the agent's universe)
        ├── scratch.c                        ← editable
        ├── info.md                          ← composed once
        └── open-watcom -> <repo>/vendor/…   ← read-only symlink

The agent's ``read`` / ``write`` / ``edit`` tools resolve paths against
``work/`` and reject anything that resolves outside, so the run-dir
metadata is invisible to the model.  The orchestrator never touches
``work/scratch.c`` — only the agent does — so there is no race on the
hot file.
"""

from __future__ import annotations

import json
import re
import shutil
import time
import unicodedata
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from c2.decompile.models import (
    BestSnapshot,
    ShapeDistance,
    Target,
    VerifyResult,
)


DEFAULT_RUNS_ROOT = Path(".c2-runs")


# ── slugify ──────────────────────────────────────────────────────────────


_SLUG_RE = re.compile(r"[^a-zA-Z0-9._-]+")


def slugify(name: str, *, maxlen: int = 64) -> str:
    """Filesystem-safe slug for a function name."""
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    s = _SLUG_RE.sub("-", s).strip("-_.") or "fn"
    return s[:maxlen]


def short_ts() -> str:
    """6-char timestamp suffix; collision-resistant enough for a run dir."""
    # base36 of seconds since epoch, last 6 chars
    n = int(time.time())
    out = []
    while n:
        n, r = divmod(n, 36)
        out.append("0123456789abcdefghijklmnopqrstuvwxyz"[r])
    return "".join(reversed(out))[-6:]


# ── meta ─────────────────────────────────────────────────────────────────


@dataclass
class RunMeta:
    """Persistent metadata for one agent's run.

    Owned by the orchestrator; written once at compose, read by every
    tool, never mutated again.
    """

    function: str
    address_hex: str
    target: Target
    target_size: int
    cflags: list[str]
    source_file: Optional[str]
    signature: Optional[str]
    tail_merge_donor: Optional[str]
    body_origin: str            # 'existing' | 'blank'
    project_root: str
    started_at: float

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["target"] = self.target.value
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "RunMeta":
        return cls(
            function=d["function"],
            address_hex=d["address_hex"],
            target=Target(d["target"]),
            target_size=int(d["target_size"]),
            cflags=list(d["cflags"]),
            source_file=d.get("source_file"),
            signature=d.get("signature"),
            tail_merge_donor=d.get("tail_merge_donor"),
            body_origin=d["body_origin"],
            project_root=d["project_root"],
            started_at=float(d["started_at"]),
        )


# ── workspace ────────────────────────────────────────────────────────────


class Workspace:
    """Owns one agent's run-dir tree + the bookkeeping helpers.

    The orchestrator instantiates one Workspace per agent and passes it
    through pydantic-ai's deps to the tools.  Tools call
    ``ws.resolve_in_work(path)`` for any file op, which both joins
    against ``work/`` and rejects path-traversal escapes.
    """

    META_FILE = "meta.json"
    HISTORY_FILE = "history.jsonl"
    TRANSCRIPT_FILE = "transcript.jsonl"
    BEST_DIR = "best"
    WORK_DIR = "work"
    SCRATCH = "scratch.c"

    def __init__(self, run_dir: Path):
        self.run_dir = run_dir.resolve()
        self.work_dir = (self.run_dir / self.WORK_DIR).resolve()
        self.best_dir = (self.run_dir / self.BEST_DIR).resolve()

    # ----- creation -------------------------------------------------

    @classmethod
    def create(
        cls,
        *,
        runs_root: Path,
        function: str,
        resume: bool = False,
    ) -> "Workspace":
        """Allocate a fresh run dir under ``runs_root``.

        If ``resume=True`` and a directory matching ``<slug>-*`` already
        exists, the most recent one is reused (its work/ is untouched).
        """
        runs_root = runs_root.resolve()
        runs_root.mkdir(parents=True, exist_ok=True)

        slug = slugify(function)
        if resume:
            existing = sorted(runs_root.glob(f"{slug}-*"))
            if existing:
                return cls(existing[-1])

        ts = short_ts()
        run_dir = runs_root / f"{slug}-{ts}"
        # Guard against ts collisions on a fast-spinning loop.
        n = 0
        while run_dir.exists():
            n += 1
            run_dir = runs_root / f"{slug}-{ts}-{n}"
        run_dir.mkdir(parents=True)
        (run_dir / cls.WORK_DIR).mkdir()
        (run_dir / cls.BEST_DIR).mkdir()
        return cls(run_dir)

    # ----- path resolution / sandboxing -----------------------------

    def resolve_in_work(self, rel: str) -> Path:
        """Resolve a path RELATIVE to work/.  Reject escapes.

        Accepts strings like ``scratch.c``, ``info.md``,
        ``open-watcom/bld/cg/intel/c/...``.  Absolute paths and any
        path that resolves outside ``work/`` raise ``ValueError``.
        """
        if not rel:
            raise ValueError("empty path")
        p = Path(rel)
        if p.is_absolute():
            raise ValueError(f"absolute paths are not allowed: {rel}")
        candidate = (self.work_dir / p).resolve()
        # ``resolve`` follows symlinks; ``open-watcom`` is a deliberate
        # symlink to the vendor tree, so we whitelist that one prefix.
        try:
            candidate.relative_to(self.work_dir)
            return candidate
        except ValueError:
            ow = (self.work_dir / "open-watcom").resolve()
            try:
                candidate.relative_to(ow)
                return candidate
            except ValueError:
                raise ValueError(
                    f"path escapes the sandbox: {rel} → {candidate}"
                ) from None

    # ----- meta -----------------------------------------------------

    def write_meta(self, meta: RunMeta) -> None:
        (self.run_dir / self.META_FILE).write_text(
            json.dumps(meta.to_dict(), indent=2)
        )

    def read_meta(self) -> RunMeta:
        return RunMeta.from_dict(
            json.loads((self.run_dir / self.META_FILE).read_text())
        )

    @property
    def scratch_path(self) -> Path:
        return self.work_dir / self.SCRATCH

    # ----- best snapshot --------------------------------------------

    def _best_verify_path(self) -> Path:
        return self.best_dir / "verify.json"

    def _best_scratch_path(self) -> Path:
        return self.best_dir / "scratch.c"

    def read_best(self) -> Optional[BestSnapshot]:
        p = self._best_verify_path()
        if not p.is_file():
            return None
        try:
            d = json.loads(p.read_text())
        except Exception:
            return None
        return BestSnapshot.model_validate(d)

    def maybe_save_best(self, result: VerifyResult) -> bool:
        """If ``result`` beats the recorded best, snapshot it.

        Returns ``True`` when the snapshot was updated.  Ordering rule
        (mirrors the existing save-the-best semantics in
        ``c2-ext``)::

          1. higher build_ok wins
          2. lower SHAPE sum wins (ir+width+spill+seat) — the JUDGE
          3. lower byte_diff wins on shape tie
        """
        if not result.build_ok:
            return False
        prev = self.read_best()

        def rank(byte_diff: int, shape: Optional[ShapeDistance]) -> tuple:
            if shape is None:
                return (byte_diff, 10**9)
            ssum = sum(d for d, _ in (shape.ir, shape.width, shape.spill, shape.seat))
            return (ssum, byte_diff)

        new_rank = rank(result.byte_diff, result.shape)
        if prev is not None:
            prev_rank = rank(prev.byte_diff, prev.shape)
            if new_rank >= prev_rank:
                return False

        snap = BestSnapshot(
            byte_diff=result.byte_diff,
            shape=result.shape,
            target=result.target,
            taken_at=datetime.now(timezone.utc),
        )
        # Persist scratch.c snapshot atomically.
        scratch = self.scratch_path
        if scratch.is_file():
            tmp = self._best_scratch_path().with_suffix(".c.tmp")
            tmp.write_bytes(scratch.read_bytes())
            tmp.replace(self._best_scratch_path())
        self._best_verify_path().write_text(snap.model_dump_json(indent=2))
        return True

    def revert_to_best(self) -> bool:
        """Restore best/scratch.c into work/scratch.c.

        Returns ``True`` if a best snapshot existed and was restored.
        """
        best = self._best_scratch_path()
        if not best.is_file():
            return False
        tmp = self.scratch_path.with_suffix(".c.tmp")
        tmp.write_bytes(best.read_bytes())
        tmp.replace(self.scratch_path)
        return True

    # ----- history / transcript -------------------------------------

    def append_history(self, event: dict[str, Any]) -> None:
        """Append one JSON event to history.jsonl.

        Each event carries ``t`` (unix ts) and ``type`` at minimum.
        """
        event = {"t": time.time(), **event}
        with (self.run_dir / self.HISTORY_FILE).open("a") as f:
            f.write(json.dumps(event, default=str) + "\n")

    def append_transcript(self, event: dict[str, Any]) -> None:
        event = {"t": time.time(), **event}
        with (self.run_dir / self.TRANSCRIPT_FILE).open("a") as f:
            f.write(json.dumps(event, default=str) + "\n")

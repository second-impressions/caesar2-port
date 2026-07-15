"""Flat numpy-backed embedding store with content-hash incremental updates."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np


@dataclass(frozen=True)
class StoredIndex:
    names: tuple[str, ...]
    matrix: np.ndarray            # float16 [N, dim], L2-normalized
    hashes: dict[str, str]
    model: str
    dim: int

    @property
    def name_to_row(self) -> dict[str, int]:
        return {n: i for i, n in enumerate(self.names)}

    def search(self, query: np.ndarray, top: int) -> list[tuple[str, float]]:
        """Cosine similarity by dot product (vectors pre-normalized)."""
        if self.matrix.size == 0:
            return []
        q = query.astype(np.float32)
        q /= max(float(np.linalg.norm(q)), 1e-9)
        sims = (self.matrix.astype(np.float32) @ q).astype(np.float32)
        top = min(top, len(sims))
        idx = np.argpartition(-sims, top - 1)[:top]
        # Stable sort by sim desc within the partition.
        idx = idx[np.argsort(-sims[idx])]
        return [(self.names[int(i)], float(sims[int(i)])) for i in idx]


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def index_path(cache_dir: Path, corpus: str = "ps") -> Path:
    return cache_dir / "embeddings" / f"{corpus}.npy"


def names_path(cache_dir: Path, corpus: str = "ps") -> Path:
    return cache_dir / "embeddings" / f"{corpus}.names.json"


def hashes_path(cache_dir: Path, corpus: str = "ps") -> Path:
    return cache_dir / "embeddings" / f"{corpus}.hashes.json"


def load(cache_dir: Path, corpus: str = "ps") -> StoredIndex | None:
    ip = index_path(cache_dir, corpus)
    np_path = names_path(cache_dir, corpus)
    hp = hashes_path(cache_dir, corpus)
    if not (ip.is_file() and np_path.is_file() and hp.is_file()):
        return None
    matrix = np.load(ip)
    meta = json.loads(np_path.read_text())
    hashes = json.loads(hp.read_text())
    return StoredIndex(
        names=tuple(meta["names"]),
        matrix=matrix,
        hashes=hashes,
        model=meta["model"],
        dim=int(meta["dim"]),
    )


def save(cache_dir: Path, idx: StoredIndex, corpus: str = "ps") -> None:
    out = cache_dir / "embeddings"
    out.mkdir(parents=True, exist_ok=True)
    np.save(index_path(cache_dir, corpus), idx.matrix.astype(np.float16))
    names_path(cache_dir, corpus).write_text(json.dumps({
        "names": list(idx.names),
        "model": idx.model,
        "dim": idx.dim,
    }, indent=2))
    hashes_path(cache_dir, corpus).write_text(json.dumps(idx.hashes, indent=2))


def merge(existing: StoredIndex | None,
          updates: list[tuple[str, np.ndarray]],
          new_hashes: dict[str, str],
          *, model: str, dim: int) -> StoredIndex:
    """Merge new (name, vector) pairs into the index.

    Order: existing names keep their row; new names appended; updated
    names overwrite in-place.  Returns a fresh :class:`StoredIndex`.
    """
    if existing is None:
        names: list[str] = []
        mat = np.zeros((0, dim), dtype=np.float32)
        hashes: dict[str, str] = {}
    else:
        names = list(existing.names)
        mat = existing.matrix.astype(np.float32)
        hashes = dict(existing.hashes)

    name_to_row = {n: i for i, n in enumerate(names)}
    new_rows: list[np.ndarray] = []
    new_names: list[str] = []
    for name, vec in updates:
        v = vec.astype(np.float32)
        n = float(np.linalg.norm(v))
        if n > 0:
            v = v / n
        row = name_to_row.get(name)
        if row is None:
            new_names.append(name)
            new_rows.append(v)
        else:
            mat[row] = v
        hashes[name] = new_hashes[name]

    if new_rows:
        names.extend(new_names)
        mat = np.vstack([mat, np.stack(new_rows)])

    return StoredIndex(
        names=tuple(names),
        matrix=mat.astype(np.float16),
        hashes=hashes,
        model=model,
        dim=dim,
    )


def stale(existing: StoredIndex | None,
          current_hashes: dict[str, str]) -> list[str]:
    """Names whose hash has changed or which are new vs the existing index."""
    if existing is None:
        return sorted(current_hashes)
    old = existing.hashes
    return sorted(
        name for name, h in current_hashes.items()
        if old.get(name) != h
    )

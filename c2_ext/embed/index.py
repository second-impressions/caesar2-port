"""Build / refresh the project's per-function embedding index."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from c2_ext.embed import server, store
from c2_ext.project import ProjectConfig


def _index_key(project: ProjectConfig) -> str:
    """Per-target embedding-index slug.

    Watcom (the historical default) keeps the ``ps`` key for backward
    compatibility with existing on-disk indexes; other targets use
    ``<active_target>``.
    """
    if project.active_target in ("default", "watcom"):
        return "ps"
    return project.active_target


def index_corpus(project: ProjectConfig, *, force: bool = False) -> dict:
    """Build / refresh the byte-exact pool's asm embeddings.

    Iterates over every function in the byte-exact pool, extracts its
    normalized asm text via the toolchain, content-hashes it, and only
    re-embeds the ones whose hash has changed since the last index.

    Returns a summary dict ``{total, added, updated, unchanged}``.
    """
    tc = project.toolchain()
    cache_dir = project.cache_dir
    key = _index_key(project)
    existing = None if force else store.load(cache_dir, key)

    pool = tc.byte_exact_functions()

    # Compute current asm + hashes
    asm_texts: dict[str, str] = {}
    hashes: dict[str, str] = {}
    for name in sorted(pool):
        try:
            info = tc.function_info(name)
            fb = tc.function_bytes(name)
            fix = tc.function_fixups(name)
            insns = tc.disassemble(fb, info.address, fix)
        except Exception:
            continue
        # Render to text and normalize for embedding
        lines = []
        for ins in insns:
            lines.append(f"{ins.mnemonic} {ins.op_str}".strip())
        raw_text = "\n".join(lines)
        asm_texts[name] = tc.normalize_asm_for_embedding(raw_text)
        hashes[name] = store.content_hash(asm_texts[name])

    if force:
        stale_names = sorted(asm_texts)
    else:
        stale_names = store.stale(existing, hashes)

    if not stale_names:
        idx = existing
        if idx is None:
            idx = store.merge(None, [], hashes, model=project.embed_model,
                              dim=server.model_dim(project.embed_model))
            store.save(cache_dir, idx, key)
        return {
            "total": len(pool),
            "added": 0, "updated": 0, "unchanged": len(asm_texts),
            "model": project.embed_model, "dim": idx.dim,
            "fallback": server.is_using_fallback(project.embed_model),
        }

    # Embed only the stale set
    vectors = server.embed(
        [asm_texts[n] for n in stale_names],
        model_name=project.embed_model,
    )
    updates = list(zip(stale_names, vectors))

    new_idx = store.merge(
        existing, updates, hashes,
        model=project.embed_model,
        dim=server.model_dim(project.embed_model),
    )
    store.save(cache_dir, new_idx, key)

    added = sum(1 for n in stale_names
                if existing is None or n not in existing.name_to_row)
    return {
        "total": len(pool),
        "added": added,
        "updated": len(stale_names) - added,
        "unchanged": len(asm_texts) - len(stale_names),
        "model": project.embed_model,
        "dim": new_idx.dim,
        "fallback": server.is_using_fallback(project.embed_model),
    }


def query_by_function(project: ProjectConfig, name: str, top: int = 10) -> list[dict]:
    """Find top-N neighbors of ``name`` from the byte-exact pool."""
    tc = project.toolchain()
    idx = store.load(project.cache_dir, _index_key(project))
    if idx is None:
        raise RuntimeError("embedding index not built; run `c2-ext index`")

    if name in idx.name_to_row:
        q = idx.matrix[idx.name_to_row[name]].astype(np.float32)
    else:
        # Compute on the fly
        info = tc.function_info(name)
        fb = tc.function_bytes(name)
        fix = tc.function_fixups(name)
        insns = tc.disassemble(fb, info.address, fix)
        text = tc.normalize_asm_for_embedding(
            "\n".join(f"{i.mnemonic} {i.op_str}".strip() for i in insns)
        )
        q = server.embed([text], model_name=project.embed_model)[0]

    raw = idx.search(q, top + 1)  # +1 to include self if present
    out = []
    for n, score in raw:
        if n == name:
            continue
        out.append({"name": n, "score": score})
        if len(out) >= top:
            break
    return out


def query_by_snippet(project: ProjectConfig, snippet: str, top: int = 10) -> list[dict]:
    """Embed an arbitrary asm snippet and find top-N neighbors."""
    tc = project.toolchain()
    idx = store.load(project.cache_dir, _index_key(project))
    if idx is None:
        raise RuntimeError("embedding index not built; run `c2-ext index`")
    text = tc.normalize_asm_for_embedding(snippet)
    q = server.embed([text], model_name=project.embed_model)[0]
    raw = idx.search(q, top)
    return [{"name": n, "score": s} for n, s in raw]

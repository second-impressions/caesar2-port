"""Embedding subsystem: index + nearest-neighbor search.

* :mod:`c2_ext.embed.server` \u2014 a persistent worker (current process or
  subprocess) wrapping ``sentence-transformers`` / ``transformers`` to
  produce one mean-pooled, L2-normalized vector per function body.
* :mod:`c2_ext.embed.store` \u2014 flat ``float16`` numpy matrix + parallel
  name list + per-function SHA-256 content hashes, persisted under
  ``<cache_dir>/embeddings/``.  Brute-force cosine via numpy matmul.

Storage layout::

    <cache_dir>/embeddings/
    \u251c ps.npy            \u2190 float16 [N, dim], L2-normalized
    \u251c names.json        \u2190 {names: [...], built_at: ts, model: ..., dim: int}
    \u2514 hashes.json       \u2190 {name: sha256_hex(normalized_asm)}
"""

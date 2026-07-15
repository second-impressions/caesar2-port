"""Embedding server \u2014 in-process by default, subprocess on demand.

For ~1500-function corpora the model load is the bulk of the time
(~3 s for ``jina-embeddings-v2-base-code`` CPU; batched encode is
~50 ms / batch of 8).  We use a lazy singleton so the model loads
once per Python process; the orchestrator that drives many
``compose`` or ``index`` calls amortises that cost.

For agent runs the embedding store is built ONCE per project; the
``nearest`` tool only does the query-time encode + numpy matmul,
which is ~120 ms total cold (model load) and <30 ms warm.

Falls back to a deterministic hash-based pseudo-vector if PyTorch /
transformers is not installed.  The pseudo-vector is poor for
semantic search but lets the rest of the pipeline work end-to-end on
machines without the ML stack.
"""

from __future__ import annotations

import hashlib
from typing import Iterable

import numpy as np


_MODEL = None
_TOKENIZER = None
_DEVICE = None
_MODEL_NAME: str | None = None
_MODEL_DIM: int = 0


def _maybe_load(model_name: str) -> bool:
    """Try to load the requested model.  Returns True on success."""
    global _MODEL, _TOKENIZER, _DEVICE, _MODEL_NAME, _MODEL_DIM
    if _MODEL is not None and _MODEL_NAME == model_name:
        return True
    try:
        import torch
        from transformers import AutoModel, AutoTokenizer
    except ImportError:
        return False

    device = (
        torch.device("cuda") if torch.cuda.is_available()
        else (torch.device("mps") if torch.backends.mps.is_available()
              else torch.device("cpu"))
    )
    tok = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    model = AutoModel.from_pretrained(model_name, trust_remote_code=True)
    model = model.to(device)
    model.eval()
    _MODEL = model
    _TOKENIZER = tok
    _DEVICE = device
    _MODEL_NAME = model_name
    _MODEL_DIM = int(model.config.hidden_size)
    return True


def model_dim(model_name: str) -> int:
    """Return the embedding dimension; fallback dim is 256."""
    if _maybe_load(model_name):
        return _MODEL_DIM
    return 256


def is_using_fallback(model_name: str) -> bool:
    return not _maybe_load(model_name)


def embed(texts: Iterable[str], model_name: str, *, batch_size: int = 8) -> np.ndarray:
    """Embed an iterable of texts \u2192 ``np.ndarray`` of shape ``[N, dim]``.

    Vectors are mean-pooled across tokens and L2-normalized.
    """
    texts = list(texts)
    if not texts:
        return np.zeros((0, model_dim(model_name)), dtype=np.float32)

    if not _maybe_load(model_name):
        return _fallback_embed(texts, dim=model_dim(model_name))

    import torch

    out_chunks: list[np.ndarray] = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        enc = _TOKENIZER(
            batch, padding=True, truncation=True,
            max_length=2048, return_tensors="pt",
        )
        enc = {k: v.to(_DEVICE) for k, v in enc.items()}
        with torch.no_grad():
            out = _MODEL(**enc)
        token_emb = out[0]
        mask = enc["attention_mask"].unsqueeze(-1).expand(token_emb.size()).float()
        summed = (token_emb * mask).sum(1)
        counts = mask.sum(1).clamp(min=1e-9)
        pooled = summed / counts
        pooled = torch.nn.functional.normalize(pooled, p=2, dim=1)
        out_chunks.append(pooled.cpu().numpy().astype(np.float32))
    return np.vstack(out_chunks)


def _fallback_embed(texts: list[str], *, dim: int) -> np.ndarray:
    """Deterministic SHA-256 based pseudo-embedding (no semantic value)."""
    out = np.zeros((len(texts), dim), dtype=np.float32)
    for i, t in enumerate(texts):
        h = hashlib.sha256(t.encode("utf-8")).digest()
        # Tile the 32-byte hash to `dim` floats in [-1, 1]
        reps = (dim + 31) // 32
        raw = (h * reps)[:dim]
        out[i] = np.frombuffer(raw, dtype=np.uint8).astype(np.float32) / 127.5 - 1.0
        n = float(np.linalg.norm(out[i]))
        if n > 0:
            out[i] /= n
    return out

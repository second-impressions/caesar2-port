"""Variant data model + a lazy, deduplicating variant queue.

A Variant is the smallest unit of work the pool consumes: a unique id,
the lever path that produced it, the full replacement file text, and a
content fingerprint.  Many levers fold to the same text after
generation (e.g. ``a + b`` commute when ``a == b`` syntactically); the
fingerprint dedup keeps the search space honest without each lever
having to re-implement equality.

The queue is a generator pipeline -- never materialise the whole
variant set up front, even for a 5000-variant brute force.  Workers
pull one at a time; the dedup happens lazily as variants stream out.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Callable, Iterable, Iterator


@dataclass
class Variant:
    """One brute-force candidate."""

    id: str                    # short stable id, e.g. ``"v0042"``
    lever_path: tuple[str, ...]
    # ↑ ordered chain of lever invocations that produced this variant
    #   (e.g. ``("width:sx=short", "firstassign:swap(a,b)")``)
    body_text: str             # rendered body text (``{ … }``)
    file_text: str             # full replacement file text (spliced)
    fingerprint: str           # 12-char sha1 of body_text


def make_variant(*, vid: str, lever_path: tuple[str, ...],
                 body_text: str, file_text: str) -> Variant:
    fp = hashlib.sha1(body_text.encode("utf-8")).hexdigest()[:12]
    return Variant(id=vid, lever_path=lever_path,
                   body_text=body_text, file_text=file_text,
                   fingerprint=fp)


class VariantQueue:
    """Wrap a stream of variants with content-hash dedup and a hard cap.

    The underlying generator is consumed lazily so a million-variant
    Cartesian product never balloons RAM; only the seen-fingerprint set
    grows (typically a few KB even on big sweeps)."""

    def __init__(self, stream: Iterable[Variant], *,
                 max_variants: int | None = None):
        self._stream = iter(stream)
        self._seen: set[str] = set()
        self._max = max_variants
        self.emitted = 0
        self.duplicates = 0

    def __iter__(self) -> Iterator[Variant]:
        for v in self._stream:
            if v.fingerprint in self._seen:
                self.duplicates += 1
                continue
            self._seen.add(v.fingerprint)
            yield v
            self.emitted += 1
            if self._max is not None and self.emitted >= self._max:
                return

    def seen_count(self) -> int:
        return len(self._seen)

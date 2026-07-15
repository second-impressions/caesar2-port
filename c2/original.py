"""The original PS.EXE: expected location + integrity guard.

The reconstruction's ground truth is the **debug-symbol build** of
Caesar II's ``PS.EXE`` (``dbg-1996-04``).  It is copyrighted and
therefore NOT tracked; the user must place it at the git-excluded
location ``data/PS.EXE`` (see README "Getting the original PS.EXE", or
run ``c2 fetch-original`` to download + extract it from archive.org
automatically).

The authoritative SHA-256 lives in ONE tracked place —
``reccmp-project.yml`` (``targets.C2.hash.sha256``) — and is read via
:func:`c2.reccmp_project.expected_original_hash`.  Every command that
consumes the original calls :func:`ensure_original` so that

* a **missing** file fails with instructions instead of a stack trace,
* a **wrong** file (different CD build, truncated download, stray
  rebuild output) fails loudly before producing garbage comparisons.

Escape hatch: ``C2_ALLOW_ORIGINAL_MISMATCH=1`` downgrades the hash
mismatch to a warning (useful when deliberately pointing the tools at
one of the 1995 release builds).
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import typer

from c2.reccmp_project import expected_original_hash

ORIGINAL_PATH = Path("data/PS.EXE")

_MISSING_MSG = """\
Error: the original PS.EXE was not found at {path}

This repo does not track the (copyrighted) original.  Supply the
debug-symbol build (SHA-256 {expected}):

  * automatically:  uv run c2 fetch-original
        (downloads a CD image from archive.org and extracts it), or
  * manually: copy it to {path} — see README.md,
        "Getting the original PS.EXE", for the CD releases that ship it.
"""

_MISMATCH_MSG = """\
Error: {path} is not the expected debug-symbol PS.EXE.

  got      sha256 {actual}
  expected sha256 {expected}   (pinned in reccmp-project.yml)

This usually means the file came from a CD release that ships a
different (non-debug) build, or the copy is truncated/corrupted.  See
README.md, "Getting the original PS.EXE", or run `uv run c2
fetch-original`.  To proceed against a different build anyway, set
C2_ALLOW_ORIGINAL_MISMATCH=1.
"""


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_original(path: Path = ORIGINAL_PATH) -> Path:
    """Fail with instructions unless *path* is the pinned original PS.EXE.

    Returns *path* on success so call sites can chain it.
    """
    expected = expected_original_hash()
    if not path.is_file():
        typer.echo(_MISSING_MSG.format(path=path, expected=expected), err=True)
        raise typer.Exit(1)
    actual = sha256_of(path)
    if actual != expected:
        if os.environ.get("C2_ALLOW_ORIGINAL_MISMATCH", "") in ("1", "true", "yes"):
            typer.echo(
                f"warning: {path} sha256 {actual} != expected {expected} "
                "(C2_ALLOW_ORIGINAL_MISMATCH set — continuing)", err=True)
            return path
        typer.echo(
            _MISMATCH_MSG.format(path=path, actual=actual, expected=expected),
            err=True)
        raise typer.Exit(1)
    return path

"""``c2 cache`` -- inventory, staleness inspection, and selective clearing
of every persistent cache the toolkit maintains.

The caches, their keying, and their staleness discipline (the long-
standing pain this command makes manageable):

| name        | where                          | keyed by / invalidated by |
|-------------|--------------------------------|---------------------------|
| build       | .c2-cache/build/               | wmake timestamps; the historical rare staleness was ROOT-CAUSED + FIXED 2026-07-09 (dosemu presents 2-second DOS FAT buckets, wmake treats equal as up-to-date; staging now bumps changed files past the .obj's bucket -- see _write_if_changed).  If it ever recurs: clear ONE file's .obj, not the dir (cold rebuild ~7-10 min) |
| verify      | .c2-cache/verify.json          | src mtimes; worklist refreshes incrementally; cross-TU tail-merge donor caveat |
| win-verify  | .c2-cache/win-verify.json      | src mtimes + MSVC image |
| trace       | /tmp/c2-regalloc-corpus/       | content + cflags + headers + _CACHE_VERSION + TRACE IMAGE ID (auto since 2026-07-09; orphaned old-key entries need GC -- `c2 cache gc`) |
| trace-sidecar| .c2-cache/regalloc-trace.json (per build) | _CACHE_VERSION + image id stamp |
| bisect      | .c2-cache/bisect/              | (function, HEAD-SHA); last 5 SHAs kept |
| ast         | .c2-cache/ast/                 | content sha in filename (append-only -> GC candidate) |
| mac         | .c2-cache/mac/                 | Mac binary never changes (sound) |
| sibling     | .c2-cache/sibling-corpus.pkl   | PS.EXE never changes (sound) |
| forge       | .c2-cache/forge-runs/ + forge-*.json | append-only run artifacts |
| crossbuild  | .c2-cache/crossbuild/          | the 1995 builds never change (sound) |

Commands:
    c2 cache status            # sizes, entry counts, staleness indicators
    c2 cache gc [--days N]     # prune trace entries + ast blobs older than N (default 30)
    c2 cache clear NAME        # selective: trace|build|bisect|ast|verify|win-verify|mac|forge
"""
from __future__ import annotations

import shutil
import time
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console

console = Console()

C2_CACHE = Path(".c2-cache")


def _trace_dir() -> Path:
    from c2.regalloc import _CORPUS_CACHE
    return _CORPUS_CACHE


def _du(p: Path) -> tuple[int, int]:
    """(bytes, entries) for a file or directory (1 level of entries)."""
    if not p.exists():
        return 0, 0
    if p.is_file():
        return p.stat().st_size, 1
    total, n = 0, 0
    for child in p.iterdir():
        n += 1
        if child.is_file():
            total += child.stat().st_size
        else:
            total += sum(f.stat().st_size for f in child.rglob("*")
                         if f.is_file())
    return total, n


def _fmt(nbytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if nbytes < 1024:
            return f"{nbytes:.0f}{unit}"
        nbytes /= 1024
    return f"{nbytes:.1f}TB"


_CLEARABLE = {
    "trace": (None, "the /tmp regalloc trace store (auto-rekeyed by image; "
              "safe -- entries rebuild lazily, ~10 s/TU)"),
    "build": (C2_CACHE / "build", "the wmake build dir -- COLD REBUILD IS "
              "~7-10 MIN; prefer removing one file's .obj"),
    "bisect": (C2_CACHE / "bisect", "dossier baselines (rebuild ~20 s per "
               "function on next dossier)"),
    "ast": (C2_CACHE / "ast", "tree-sitter AST blobs (rebuild lazily)"),
    "verify": (C2_CACHE / "verify.json", "the corpus verify cache "
               "(worklist/decomp-verify rebuild it incrementally)"),
    "win-verify": (C2_CACHE / "win-verify.json", "the Windows byte-oracle "
                   "cache"),
    "mac": (C2_CACHE / "mac", "Mac decompile cache (JVM ~25 s per function "
            "to rebuild)"),
    "forge": (C2_CACHE / "forge-runs", "forge run artifacts (history -- "
              "clearing loses `c2 forge report` for past runs)"),
}


def cache(
    action: Annotated[str, typer.Argument(
        help="status | gc | clear")] = "status",
    name: Annotated[Optional[str], typer.Argument(
        help="cache name for `clear` "
             f"({'|'.join(_CLEARABLE)})")] = None,
    days: Annotated[int, typer.Option(
        "--days", help="gc: prune entries older than N days")] = 30,
    yes: Annotated[bool, typer.Option(
        "--yes", "-y", help="skip the confirmation prompt")] = False,
) -> None:
    """Inventory / GC / selectively clear the toolkit's persistent caches."""
    if action == "status":
        _status()
    elif action == "gc":
        _gc(days)
    elif action == "clear":
        _clear(name, yes)
    else:
        console.print(f"[red]unknown action {action!r} "
                      "(status | gc | clear)[/]")
        raise typer.Exit(1)


def _status() -> None:
    from c2.regalloc import trace_image_id, _CACHE_VERSION
    img = trace_image_id()
    console.print(f"[bold]trace image:[/] {img}   "
                  f"[bold]parser schema:[/] v{_CACHE_VERSION}")
    td = _trace_dir()
    tb, tn = _du(td)
    # how many trace entries belong to the CURRENT image/schema key space?
    # (entries are opaque hashes; age is the only cheap indicator)
    now = time.time()
    stale7 = sum(1 for c in td.iterdir()
                 if (now - c.stat().st_mtime) > 7 * 86400) if td.exists() else 0
    console.print(f"  trace       {_fmt(tb):>8}  {tn:>5} entries  "
                  f"({stale7} older than 7d; orphans from old keys "
                  f"accumulate -- `c2 cache gc`)   {td}")
    for nm, (path, note) in _CLEARABLE.items():
        if nm == "trace":
            continue
        p = path
        b, n = _du(p)
        console.print(f"  {nm:<11} {_fmt(b):>8}  {n:>5} entries   {p}")
    # staleness indicators for the known-tricky ones
    vj = C2_CACHE / "verify.json"
    if vj.exists():
        newest_src = max((f.stat().st_mtime
                          for f in Path("decomp/src").glob("*.c")),
                         default=0)
        mark = ("[yellow]STALE vs decomp/src[/]"
                if vj.stat().st_mtime < newest_src else "[green]fresh[/]")
        console.print(f"  verify.json: {mark} (worklist auto-refreshes "
                      "incrementally; tail-merge donor caveat)")
    console.print(
        "\n  [dim]keying summary: trace = content+flags+headers+schema+"
        "IMAGE-ID (auto-invalidates on image rebuild, 2026-07-09); "
        "bisect = (fn, HEAD-SHA); ast = content-sha; build = wmake "
        "timestamps (historical same-2s-DOS-bucket staleness root-caused "
        "+ fixed 2026-07-09 in _write_if_changed; if a wrong diff count "
        "ever recurs: rm .c2-cache/build/<file>.obj or --no-cache).[/]")


def _gc(days: int) -> None:
    import json
    from c2.regalloc import trace_image_id, _CACHE_VERSION
    cutoff = time.time() - days * 86400
    cur_img = trace_image_id()
    freed = n = orphans = 0
    td = _trace_dir()
    if td.exists():
        for child in td.iterdir():
            try:
                # PRECISE orphan detection via the per-entry stamp
                # (entries written since 2026-07-09 carry meta.json);
                # stamp mismatch = the key space can never be read again.
                meta = child / "meta.json"
                stale = False
                if meta.exists():
                    try:
                        m = json.loads(meta.read_text())
                        stale = (m.get("v") != _CACHE_VERSION
                                 or m.get("img") != cur_img)
                    except Exception:
                        stale = True
                    if stale:
                        orphans += 1
                if stale or child.stat().st_mtime < cutoff:
                    b, _ = _du(child)
                    shutil.rmtree(child, ignore_errors=True)
                    freed += b
                    n += 1
            except FileNotFoundError:
                continue
    astd = C2_CACHE / "ast"
    if astd.exists():
        for f in astd.iterdir():
            try:
                if f.is_file() and f.stat().st_mtime < cutoff:
                    freed += f.stat().st_size
                    f.unlink()
                    n += 1
            except FileNotFoundError:
                continue
    console.print(f"gc: pruned {n} entr{'y' if n == 1 else 'ies'} "
                  f"({orphans} stamped orphans, rest older than {days}d), "
                  f"freed {_fmt(freed)}")


def _clear(name: Optional[str], yes: bool) -> None:
    if not name or name not in _CLEARABLE:
        console.print(f"[red]need a cache name: {'|'.join(_CLEARABLE)}[/]")
        raise typer.Exit(1)
    path, note = _CLEARABLE[name]
    p = _trace_dir() if name == "trace" else path
    b, n = _du(p)
    console.print(f"clear [bold]{name}[/]: {p}  ({_fmt(b)}, {n} entries)")
    console.print(f"  note: {note}")
    if not yes and not typer.confirm("proceed?"):
        raise typer.Exit(0)
    if p.is_file():
        p.unlink(missing_ok=True)
    elif p.exists():
        shutil.rmtree(p, ignore_errors=True)
    console.print("[green]cleared[/]")
